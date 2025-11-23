from typing import Any

from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import Reactive, reactive
from textual.widgets import Tree
from textual.widgets.tree import TreeNode
from typing_extensions import override


class Sidebar(Tree[Any]):
    class ItemSelected(Message):
        def __init__(self, node_id: str, node_type: str | None = None) -> None:
            self.node_id: str = node_id
            self.node_type: str | None = node_type
            super().__init__()

    def __init__(self, id: str) -> None:
        super().__init__("Menu", id=id)
        self.show_horizontal_scrollbar: Reactive[bool] = reactive(False)
        self.show_root: bool = False
        self.guide_depth: int = 3
        self.can_focus: bool = False  # re-enable focus later

        self._downloads_node: TreeNode[Any]
        self._downloading_node: TreeNode[Any]
        self._seeding_node: TreeNode[Any]
        self._paused_node: TreeNode[Any]
        self._completed_node: TreeNode[Any]

    @override
    def compose(self) -> ComposeResult:
        root = self.root
        # NODES
        search = root.add("Search", allow_expand=False)
        search.data = {"id": "search_content"}

        self._downloads_node = root.add(
            "Downloads (0)",
            data={"id": "downloads_content", "category": "downloads"},
            expand=True,
            allow_expand=False,
        )

        download_items = [
            ("Downloading (0)", "downloading"),
            ("Seeding (0)", "seeding"),
            ("Paused (0)", "paused"),
            ("Completed (0)", "completed"),
        ]

        for label, download_type in download_items:
            node = self._downloads_node.add(
                label,
                data={"id": "downloads_content", "type": download_type},
                allow_expand=False,
            )

            if download_type == "downloading":
                self._downloading_node = node
            elif download_type == "seeding":
                self._seeding_node = node
            elif download_type == "paused":
                self._paused_node = node
            elif download_type == "completed":
                self._completed_node = node

        self.select_node(search)  # default select "search" node
        return super().compose()

    def update_download_counts(self, counts: dict[str, int]) -> None:
        total_downloads = sum(counts.values())

        self._downloads_node.set_label(f"Downloads ({total_downloads})")
        self._downloading_node.set_label(
            f"Downloading ({counts.get('Downloading', 0)})"
        )
        self._seeding_node.set_label(f"Seeding ({counts.get('Seeding', 0)})")
        self._paused_node.set_label(f"Paused ({counts.get('Paused', 0)})")
        self._completed_node.set_label(f"Completed ({counts.get('Completed', 0)})")

    def on_tree_node_selected(self, event: Tree.NodeSelected[dict[str, str]]) -> None:
        node_data = event.node.data
        if node_data and "id" in node_data:
            self.post_message(
                self.ItemSelected(
                    node_id=node_data["id"], node_type=node_data.get("type")
                )
            )

    def select_node_by_id(self, node_id: str) -> None:
        def _find_node(node: TreeNode[Any]) -> TreeNode[Any] | None:
            if node.data and node.data.get("id") == node_id:
                return node

            for child in node.children:
                if found := _find_node(child):
                    return found
            return None

        if target_node := _find_node(self.root):
            self.select_node(target_node)
