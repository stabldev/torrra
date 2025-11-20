from typing import Any

from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import Reactive, reactive
from textual.widgets import Tree
from typing_extensions import override


class Sidebar(Tree[Any]):
    class ItemSelected(Message):
        def __init__(self, node_id: str) -> None:
            self.node_id: str = node_id
            super().__init__()

    def __init__(self, id: str | None = None) -> None:
        super().__init__("Menu", id=id)
        self.show_horizontal_scrollbar: Reactive[bool] = reactive(False)
        self.show_root: bool = False
        self.guide_depth: int = 3
        self.can_focus: bool = False  # re-enable focus later

    @override
    def compose(self) -> ComposeResult:
        root = self.root
        # NODES
        search = root.add("Search", allow_expand=False)
        search.data = {"id": "search_content"}

        downloads = root.add("Downloads (1)", expand=True, allow_expand=False)
        downloads.data = {"id": "downloads_content"}

        downloads.add("Active (0)", data=downloads.data, allow_expand=False)
        downloads.add("Completed (1)", data=downloads.data, allow_expand=False)

        self.select_node(search)  # default select "search" node
        return super().compose()

    def on_tree_node_selected(self, event: Tree.NodeSelected[dict[str, str]]) -> None:
        if event.node.data and "id" in event.node.data:
            self.post_message(self.ItemSelected(node_id=event.node.data["id"]))
