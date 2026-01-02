from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import ContentSwitcher
from typing_extensions import override

from torrra._types import Indexer, TorrentStatus
from torrra.core.download import get_download_manager
from torrra.core.torrent import get_torrent_manager
from torrra.widgets.downloads import DownloadsContent
from torrra.widgets.search import SearchContent
from torrra.widgets.sidebar import Sidebar


class HomeScreen(Screen[None]):
    def __init__(
        self,
        indexer: Indexer,
        search_query: str,
        use_cache: bool,
        direct_download: str | None = None,
    ):
        super().__init__()
        self.indexer: Indexer = indexer
        self.search_query: str = search_query
        self.use_cache: bool = use_cache
        self.direct_download: str | None = direct_download

        self._sidebar: Sidebar
        self._content_switcher: ContentSwitcher
        self._downloads_content: DownloadsContent

    @override
    def compose(self) -> ComposeResult:
        initial_content = (
            "downloads_content" if self.direct_download else "search_content"
        )

        with Horizontal(id="main_layout"):
            yield Sidebar(id="sidebar")
            with ContentSwitcher(initial=initial_content, id="content_switcher"):
                yield DownloadsContent()
                yield SearchContent(
                    indexer=self.indexer,
                    search_query=self.search_query,
                    use_cache=self.use_cache,
                )

    def on_mount(self) -> None:
        self._sidebar = self.query_one(Sidebar)
        self._sidebar.can_focus = True  # re-enable focus

        self._content_switcher = self.query_one(ContentSwitcher)
        self._downloads_content = self.query_one(DownloadsContent)

        # start torrents in background
        tm, dm = get_torrent_manager(), get_download_manager()
        torrents = tm.get_all_torrents()
        for torrent in torrents:
            dm.add_torrent(
                torrent["magnet_uri"],
                is_paused=torrent["is_paused"],
            )

        # Handle direct download if provided
        if self.direct_download:
            import asyncio
            from torrra.utils.magnet import resolve_magnet_uri
            from torrra._types import Torrent

            # It's a magnet URI or URL, resolve it
            async def handle_direct_download():
                magnet_uri = await resolve_magnet_uri(str(self.direct_download))
                if magnet_uri:
                    # Add to download manager
                    dm.add_torrent(magnet_uri, is_paused=False)

                    # Create a basic torrent record to add to the database
                    # For direct downloads, we'll use the magnet URI as the title initially
                    # The actual title will be updated when the torrent metadata is available
                    tm.add_torrent(
                        Torrent(
                            magnet_uri=magnet_uri,
                            title=magnet_uri.split("&")[0]
                            if magnet_uri.startswith("magnet:")
                            else str(self.direct_download),
                            size=0,  # Size will be updated when metadata is available
                            source="Direct Download",
                            seeders=0,
                            leechers=0,
                        )
                    )

                    # Switch to downloads content and select the new torrent
                    self._content_switcher.current = "downloads_content"
                    self._sidebar.select_node_by_group_id("downloads_content")
                else:
                    self.app.notify("Failed to resolve magnet URI", severity="error")

            # Run the async function
            asyncio.create_task(handle_direct_download())

        # start timer to update data on both sidebar
        # and downloads content table
        self.set_interval(1, self._update_downloads_data)

    def on_sidebar_item_selected(self, event: Sidebar.ItemSelected) -> None:
        self.query_one(ContentSwitcher).current = event.group_id

    def on_search_content_download_requested(self) -> None:
        self.query_one(ContentSwitcher).current = "downloads_content"
        self.query_one(Sidebar).select_node_by_group_id("downloads_content")

        self._downloads_content.focus_table()

    def _update_downloads_data(self) -> None:
        dm = get_download_manager()

        # Check for metadata updates
        dm.check_metadata_updates()

        magnet_uris = list(dm.torrents.keys())

        counts = {"Downloading": 0, "Seeding": 0, "Paused": 0, "Completed": 0}
        statuses: dict[str, TorrentStatus | None] = {}

        for uri in magnet_uris:
            status = dm.get_torrent_status(uri)
            statuses[uri] = status
            if not status:
                continue

            state_text = dm.get_torrent_state_text(status)
            if state_text in ("Downloading", "Fetching"):
                counts["Downloading"] += 1
            elif state_text in counts:
                counts[state_text] += 1

        self._sidebar.update_download_counts(counts)
        # only update downloads table if it is visible
        if self._content_switcher.current == "downloads_content":
            self._downloads_content.update_table_data(statuses)
