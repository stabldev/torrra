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
    def __init__(self, indexer: Indexer, search_query: str, use_cache: bool):
        super().__init__()
        self.indexer: Indexer = indexer
        self.search_query: str = search_query
        self.use_cache: bool = use_cache

        self._sidebar: Sidebar
        self._content_switcher: ContentSwitcher
        self._downloads_content: DownloadsContent

    @override
    def compose(self) -> ComposeResult:
        with Horizontal(id="main_layout"):
            yield Sidebar(id="sidebar")
            with ContentSwitcher(initial="search_content", id="content_switcher"):
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

        # start timer to update data on both sidebar
        # and downloads content table
        self.set_interval(1, self._update_downloads_data)

    def on_sidebar_item_selected(self, event: Sidebar.ItemSelected) -> None:
        self.query_one(ContentSwitcher).current = event.group_id

    def on_search_content_download_requested(self) -> None:
        self.query_one(ContentSwitcher).current = "downloads_content"
        self.query_one(Sidebar).select_node_by_group_id(
            "downloads_content"
        )  # change currently selected sidebar item

    def _update_downloads_data(self) -> None:
        dm = get_download_manager()
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
