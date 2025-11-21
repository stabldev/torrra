from typing import Any

from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import Reactive, reactive
from textual.widgets import Tree
from typing_extensions import override


class Sidebar(Tree[Any]):
    class ItemSelected(Message):
        def __init__(self, node_id: str, node_type: str | None = None) -> None:
            self.node_id: str = node_id
            self.node_type: str | None = node_type
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

        downloads = root.add("Downloads (2)", expand=True, allow_expand=False)
        downloads.data = {"id": "downloads_content", "category": "downloads"}

        download_items = [
            ("Downloading (0)", "downloading"),
            ("Seeding (0)", "seeding"),
            ("Paused (1)", "paused"),
            ("Completed (1)", "completed"),
        ]

        for label, download_type in download_items:
            downloads.add(
                label,
                data={"id": "downloads_content", "type": download_type},
                allow_expand=False,
            )

        self.select_node(search)  # default select "search" node
        return super().compose()

    def on_tree_node_selected(self, event: Tree.NodeSelected[dict[str, str]]) -> None:
        node_data = event.node.data
        if node_data and "id" in node_data:
            self.post_message(
                self.ItemSelected(
                    node_id=node_data["id"], node_type=node_data.get("type")
                )
            )
