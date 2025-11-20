from textual import on
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

        # ui refs (cached later)
        self._sidebar: Sidebar
        self._content_switcher: ContentSwitcher

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
        self._sidebar.can_focus = True

        self._content_switcher = self.query_one("#content_switcher", ContentSwitcher)

    @on(Sidebar.ItemSelected)
    def _switch_content(self, event: Sidebar.ItemSelected) -> None:
        self._content_switcher.current = event.node_id
