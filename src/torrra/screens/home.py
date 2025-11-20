from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import ContentSwitcher, Tree
from typing_extensions import override

from torrra._types import Indexer
from torrra.widgets.downloads_content import DownloadsContent
from torrra.widgets.search_content import SearchContent


class HomeScreen(Screen[None]):
    def __init__(self, indexer: Indexer, search_query: str, use_cache: bool):
        super().__init__()
        self.indexer: Indexer = indexer
        self.search_query: str = search_query
        self.use_cache: bool = use_cache

        # ui refs (cached later)
        self._sidebar: Tree[Any]
        self._content_switcher: ContentSwitcher

    @override
    def compose(self) -> ComposeResult:
        with Horizontal(id="main_layout"):
            sidebar: Tree[Any] = Tree("Menu", id="sidebar")
            sidebar.show_horizontal_scrollbar = False
            sidebar.show_root = False
            sidebar.guide_depth = 3
            sidebar.can_focus = False  # re-enable focus later
            root = sidebar.root
            search_data = {"id": "search_content"}
            downloads_data = {"id": "downloads_content"}
            search = root.add("Search", data=search_data, allow_expand=False)
            downloads = root.add(
                "Downloads (1)",
                data=downloads_data,
                expand=True,
                allow_expand=False,
            )
            downloads.add("Active (0)", data=downloads_data, allow_expand=False)
            downloads.add("Completed (1)", data=downloads_data, allow_expand=False)
            sidebar.select_node(search)
            yield sidebar
            with ContentSwitcher(initial="search_content"):
                yield DownloadsContent()
                yield SearchContent(
                    indexer=self.indexer,
                    search_query=self.search_query,
                    use_cache=self.use_cache,
                )

    def on_mount(self) -> None:
        self._sidebar = self.query_one("#sidebar", Tree)
        self._sidebar.can_focus = True

        self._content_switcher = self.query_one("ContentSwitcher", ContentSwitcher)

    @on(Tree.NodeSelected)
    def on_node_selected(self, event: Tree.NodeSelected[Any]) -> None:
        if event.node.data:
            self._content_switcher.current = event.node.data.get("id")
