from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import ContentSwitcher
from typing_extensions import override

from torrra._types import Indexer
from torrra.widgets.downloads_content import DownloadsContent
from torrra.widgets.search_content import SearchContent
from torrra.widgets.sidebar import Sidebar


class HomeScreen(Screen[None]):
    def __init__(self, indexer: Indexer, search_query: str, use_cache: bool):
        super().__init__()
        self.indexer: Indexer = indexer
        self.search_query: str = search_query
        self.use_cache: bool = use_cache

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
        self.query_one(Sidebar).can_focus = True  # re-enable focus

    def on_sidebar_item_selected(self, event: Sidebar.ItemSelected) -> None:
        self.query_one(ContentSwitcher).current = event.node_id

    def on_search_content_download_requested(
        self, event: SearchContent.DownloadRequested
    ) -> None:
        _ = event.torrent
        self.query_one(ContentSwitcher).current = "downloads_content"
        self.query_one(DownloadsContent).children[0].focus()  # focus table
        self.query_one(Sidebar).select_node_by_id(
            "downloads_content"
        )  # change currently selected sidebar item
