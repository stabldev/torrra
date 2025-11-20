from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import ContentSwitcher, Tree
from typing_extensions import override

from torrra._types import Indexer
from torrra._version import __version__
from torrra.widgets.search_content import SearchContent


class SearchScreen(Screen[None]):
    def __init__(self, indexer: Indexer, search_query: str, use_cache: bool):
        super().__init__()
        self.indexer: Indexer = indexer
        self.search_query: str = search_query
        self.use_cache: bool = use_cache

        # ui refs (cached later)
        self._sidebar: Tree[Any]

    @override
    def compose(self) -> ComposeResult:
        with Horizontal(id="main_layout"):
            sidebar: Tree[Any] = Tree("Menu", id="sidebar")
            sidebar.show_horizontal_scrollbar = False
            sidebar.show_root = False
            sidebar.guide_depth = 3
            sidebar.can_focus = False  # re-enable focus later
            root = sidebar.root
            search = root.add("Search", allow_expand=False)
            downloads = root.add("Downloads (1)", expand=True, allow_expand=False)
            downloads.add("Active (0)", allow_expand=False)
            downloads.add("Completed (1)", allow_expand=False)
            sidebar.select_node(search)
            yield sidebar
            with ContentSwitcher(initial="search_content"):
                yield SearchContent(
                    indexer=self.indexer,
                    search_query=self.search_query,
                    use_cache=self.use_cache,
                )

    # --------------------------------------------------
    # APP LIFECYCLE
    # --------------------------------------------------
    def on_mount(self) -> None:
        self._sidebar = self.query_one("#sidebar", Tree)
        self._sidebar.border_subtitle = f"v{__version__}"
        self._sidebar.can_focus = True
