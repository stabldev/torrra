from typing import Any, ClassVar

from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import Reactive, reactive
from textual.widgets import Tree
from textual.widgets.tree import TreeNode
from typing_extensions import override


class Sidebar(Tree[Any]):
    DOWNLOADS_GROUP: ClassVar[list[str]] = [
        "Downloading",
        "Seeding",
        "Paused",
        "Completed",
    ]

    class ItemSelected(Message):
        def __init__(self, group_id: str, group_type: str | None = None) -> None:
            self.group_id: str = group_id
            self.group_type: str | None = group_type
            super().__init__()

    def __init__(self, id: str) -> None:
        super().__init__("Menu", id=id)
        self.show_horizontal_scrollbar: Reactive[bool] = reactive(False)
        self.show_root: bool = False
        self.guide_depth: int = 3
        self.can_focus: bool = False  # re-enable focus later

        self._downloads_root_node: TreeNode[Any]
        self._downloads_nodes: dict[str, TreeNode[Any]] = {}

    @override
    def compose(self) -> ComposeResult:
        root = self.root
        # NODES
        search = root.add("Search", allow_expand=False)
        search.data = {"group_id": "search_content"}

        downloads_node = root.add("Downloads (0)", expand=True, allow_expand=False)
        downloads_node.data = {"group_id": "downloads_content"}

        for item in self.DOWNLOADS_GROUP:
            node = downloads_node.add(f"{item} (0)", allow_expand=False)
            node.data = {**downloads_node.data, "group_type": item}

            self._downloads_nodes[item] = node
        self._downloads_root_node = downloads_node

        self.select_node(search)  # default
        return super().compose()

    def on_tree_node_selected(self, event: Tree.NodeSelected[dict[str, str]]) -> None:
        node_data = event.node.data or {}
        if group_id := node_data.get("group_id"):
            self.post_message(
                self.ItemSelected(
                    group_id=group_id, group_type=node_data.get("group_type")
                )
            )

    def select_node_by_group_id(self, group_id: str) -> None:
        def _find_node(node: TreeNode[Any]) -> TreeNode[Any] | None:
            if node.data and node.data.get("group_id") == group_id:
                return node

            for child in node.children:
                if found := _find_node(child):
                    return found
            return None

        if target_node := _find_node(self.root):
            self.select_node(target_node)

    def update_download_counts(self, counts: dict[str, int]) -> None:
        total = sum(counts.values())
        self._downloads_root_node.set_label(f"Downloads ({total})")

        for item in self.DOWNLOADS_GROUP:
            count = counts.get(item, 0)
            self._downloads_nodes[item].set_label(f"{item} ({count})")
