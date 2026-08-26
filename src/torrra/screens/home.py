from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import ContentSwitcher
from typing_extensions import override

from torrra._types import Indexer, TorrentStatus
from torrra.core.download import get_download_manager
from torrra.core.exceptions import ConfigError, DownloadError
from torrra.core.torrent import get_torrent_manager
from torrra.widgets.downloads import DownloadsContent
from torrra.widgets.search import SearchContent
from torrra.widgets.sidebar import DOWNLOADS_GROUP, Sidebar
from torrra.widgets.status_bar import StatusBar


class HomeScreen(Screen[None]):
    def __init__(
        self,
        indexer: Indexer | None,
        search_query: str,
        use_cache: bool,
        direct_download: str | None = None,
        direct_save_path: str | None = None,
        show_downloads: bool = False,
    ):
        super().__init__()
        self.indexer: Indexer | None = indexer
        self.search_query: str = search_query
        self.use_cache: bool = use_cache
        self.direct_download: str | None = direct_download
        self.direct_save_path: str | None = direct_save_path
        self.show_downloads: bool = show_downloads

        self._sidebar: Sidebar
        self._content_switcher: ContentSwitcher
        self._downloads_content: DownloadsContent
        self._status_bar: StatusBar

    @override
    def compose(self) -> ComposeResult:
        # without an indexer there is no search, so the app opens on downloads
        has_search = self.indexer is not None
        initial_content = (
            "search_content"
            if has_search and not (self.direct_download or self.show_downloads)
            else "downloads_content"
        )

        with Horizontal(id="main_layout"):
            yield Sidebar(id="sidebar", show_search=has_search)
            with ContentSwitcher(initial=initial_content, id="content_switcher"):
                yield DownloadsContent()
                if self.indexer is not None:
                    yield SearchContent(
                        indexer=self.indexer,
                        search_query=self.search_query,
                        use_cache=self.use_cache,
                    )
        yield StatusBar(id="status_bar")

    def on_mount(self) -> None:
        self._sidebar = self.query_one(Sidebar)
        self._sidebar.can_focus = True  # re-enable focus

        self._content_switcher = self.query_one(ContentSwitcher)
        self._downloads_content = self.query_one(DownloadsContent)
        self._status_bar = self.query_one(StatusBar)

        # start torrents in background
        tm, dm = get_torrent_manager(), get_download_manager()
        torrents = tm.get_all_torrents()
        for torrent in torrents:
            try:
                dm.add_torrent(
                    torrent["magnet_uri"],
                    is_paused=torrent["is_paused"],
                    file_priorities=torrent.get("file_priorities"),
                    upload_limit=torrent.get("upload_limit"),
                    download_limit=torrent.get("download_limit"),
                    save_path=torrent.get("save_path"),
                    create_path=torrent.get("save_path") is None,
                    max_ratio=torrent.get("max_ratio"),
                    max_seeding_time=torrent.get("max_seeding_time"),
                    sequential_download=torrent.get("sequential_download", False),
                )
            except (ConfigError, DownloadError) as exc:
                self.notify(
                    f"Could not restore '{torrent['title']}': {exc}",
                    title="Torrent Restore Failed",
                    severity="error",
                )

        if self.show_downloads or self.direct_download or self.indexer is None:
            # When showing downloads or handling direct download, set sidebar active node to downloads
            self._sidebar.select_node_by_group_id("downloads_content")
            self._downloads_content.focus_table()

        # Handle direct download if provided
        if self.direct_download:
            import asyncio

            from torrra.utils.direct_download import handle_direct_download

            asyncio.create_task(
                handle_direct_download(
                    self,
                    str(self.direct_download),
                    save_path=self.direct_save_path,
                )
            )

        # start timer to update data on both sidebar
        # and downloads content table
        self.set_interval(1, self._update_downloads_data)

    def on_sidebar_item_selected(self, event: Sidebar.ItemSelected) -> None:
        self.query_one(ContentSwitcher).current = event.group_id
        if event.group_id == "downloads_content":
            self._downloads_content.set_group_filter(event.group_type)

    def on_search_content_download_requested(self) -> None:
        self.query_one(ContentSwitcher).current = "downloads_content"
        self.query_one(Sidebar).select_node_by_group_id("downloads_content")
        self._downloads_content.set_group_filter(None)

        self._downloads_content.focus_table()

    def _update_downloads_data(self) -> None:
        dm = get_download_manager()

        # Check for metadata updates
        dm.check_metadata_updates()

        # Update status bar stats
        stats = dm.get_session_stats()
        self._status_bar.update_stats(
            stats.get("download_rate", 0.0),
            stats.get("upload_rate", 0.0),
            stats.get("dht_nodes", 0),
        )

        magnet_uris = list(dm.torrents.keys())

        counts = {group: 0 for group in DOWNLOADS_GROUP}
        statuses: dict[str, TorrentStatus | None] = {}

        for uri in magnet_uris:
            status = dm.get_torrent_status(uri)
            statuses[uri] = status
            if not status:
                continue

            state_text = dm.get_torrent_state_text(status)
            if state_text in ("Downloading", "Fetching", "Allocating"):
                counts["Downloading"] += 1
            elif state_text == "Stalled":
                counts["Stalled"] += 1
            elif state_text == "Seeding":
                counts["Seeding"] += 1
            elif state_text in ("Paused", "Queued"):
                counts["Paused"] += 1
            elif state_text == "Completed":
                counts["Completed"] += 1
            elif state_text == "Checking":
                counts["Checking"] += 1
            elif state_text in ("Missing Files", "Error"):
                counts["Error"] += 1
            elif state_text in counts:
                counts[state_text] += 1

        self._sidebar.update_download_counts(counts)
        # only update downloads table if it is visible
        if self._content_switcher.current == "downloads_content":
            self._downloads_content.update_table_data(statuses)
