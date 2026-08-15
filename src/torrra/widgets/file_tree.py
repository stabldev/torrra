from typing import Any, ClassVar

from rich.markup import escape
from textual.binding import Binding, BindingType
from textual.message import Message
from textual.widgets import Tree
from textual.widgets.tree import TreeNode
from typing_extensions import override

from torrra._types import TorrentFile
from torrra.utils.helpers import human_readable_size


class FileTree(Tree[Any]):
    """A tree of torrent files with checkbox-style selection.

    File nodes carry `{"index": int}` data; directory nodes carry
    `{"indices": frozenset[int]}` (all descendant file indices) so a
    directory can be toggled in bulk. Directories show `[x]` when all
    descendants are selected, `[-]` for a partial selection, and `[ ]`
    when none are selected.
    """

    class SelectionChanged(Message):
        """Posted whenever the set of selected files changes."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
        Binding("space", "toggle_check", "Toggle selection"),
        Binding("enter", "toggle_check", "Toggle selection"),
        Binding("left", "collapse_node", show=False),
        Binding("right", "expand_node", show=False),
    ]

    def __init__(self, label: str = "Files", **kwargs: Any) -> None:
        super().__init__(label, **kwargs)
        self.show_root: bool = False
        self.guide_depth: int = 3

        self._selected: set[int] = set()
        self._file_nodes: dict[int, TreeNode[Any]] = {}
        self._file_labels: dict[int, str] = {}
        self._file_dirs: dict[int, list[TreeNode[Any]]] = {}
        self._dir_nodes: dict[tuple[str, ...], TreeNode[Any]] = {}
        self._dir_labels: dict[tuple[str, ...], str] = {}
        self._dir_key: dict[TreeNode[Any], tuple[str, ...]] = {}

    def populate(self, files: list[TorrentFile], selected: set[int]) -> None:
        """Rebuild the tree from a flat list of files."""
        self.clear()
        self._selected = set(selected)
        self._file_nodes.clear()
        self._file_labels.clear()
        self._file_dirs.clear()
        self._dir_nodes.clear()
        self._dir_labels.clear()
        self._dir_key.clear()

        for file in files:
            parts = file.path.split("/")
            node = self.root
            ancestors: list[TreeNode[Any]] = []
            for i, part in enumerate(parts[:-1]):
                key = tuple(parts[: i + 1])
                child = self._dir_nodes.get(key)
                if child is None:
                    child = node.add(part + "/", allow_expand=True)
                    child.data = {"indices": set()}
                    self._dir_nodes[key] = child
                    self._dir_labels[key] = part + "/"
                    self._dir_key[child] = key
                node = child
                ancestors.append(node)

            name = parts[-1]
            label = f"{name} ({human_readable_size(file.size)})"
            leaf = node.add(
                self._format_label(file.index, label),
                data={"index": file.index},
                allow_expand=False,
            )
            self._file_nodes[file.index] = leaf
            self._file_labels[file.index] = label
            self._file_dirs[file.index] = list(ancestors)

            for ancestor in ancestors:
                ancestor.data["indices"].add(file.index)

        for node in self._dir_nodes.values():
            node.set_label(self._format_dir_label(node))
            node.expand()

        if self.root.children:
            self.select_node(self.root.children[0])

        self.refresh()

    def toggle_cursor(self) -> None:
        """Toggle selection of the node under the cursor."""
        node = self.cursor_node
        if node is None or node.data is None:
            return

        if "index" in node.data:
            index = node.data["index"]
            if index in self._selected:
                self._selected.discard(index)
            else:
                self._selected.add(index)
            node.set_label(self._format_label(index, self._file_labels[index]))
            self._update_dir_labels(self._file_dirs.get(index, []))
        elif "indices" in node.data:
            indices = node.data["indices"]
            if indices and indices <= self._selected:
                self._selected.difference_update(indices)
            else:
                self._selected.update(indices)
            self._update_labels(indices)
            self._update_dir_labels([node] + self._dir_ancestors(node))

        self.refresh()
        self.post_message(self.SelectionChanged())

    def select_all(self) -> None:
        self._selected = set(self._file_nodes)
        self._update_labels(self._selected)
        self._update_dir_labels(list(self._dir_nodes.values()))
        self.post_message(self.SelectionChanged())

    def select_none(self) -> None:
        self._selected.clear()
        self._update_labels(self._file_nodes.keys())
        self._update_dir_labels(list(self._dir_nodes.values()))
        self.post_message(self.SelectionChanged())

    def selected_indices(self) -> list[int]:
        return sorted(self._selected)

    def _update_labels(self, indices: Any) -> None:
        for index in indices:
            node = self._file_nodes.get(index)
            if node is not None:
                node.set_label(self._format_label(index, self._file_labels[index]))

    def _update_dir_labels(self, nodes: list[TreeNode[Any]]) -> None:
        for node in nodes:
            if node is not None and node in self._dir_key:
                node.set_label(self._format_dir_label(node))

    def _dir_ancestors(self, node: TreeNode[Any]) -> list[TreeNode[Any]]:
        key = self._dir_key.get(node)
        if not key:
            return []
        return [self._dir_nodes[key[:i]] for i in range(1, len(key))]

    def _format_label(self, index: int, label: str) -> str:
        marker = "\\[x]" if index in self._selected else "\\[ ]"
        return f"{marker} {escape(label)}"

    def _format_dir_label(self, node: TreeNode[Any]) -> str:
        indices = node.data.get("indices", set())
        if not indices or not indices & self._selected:
            marker = "\\[ ]"
        elif indices <= self._selected:
            marker = "\\[x]"
        else:
            marker = "\\[-]"
        base = self._dir_labels.get(self._dir_key[node], "")
        return f"{marker} {escape(base)}"

    def action_expand_node(self) -> None:
        node = self.cursor_node
        if node is not None and not node.is_expanded:
            node.expand()

    def action_collapse_node(self) -> None:
        node = self.cursor_node
        if node is not None and node.is_expanded:
            node.collapse()

    @override
    def action_toggle_check(self) -> None:
        self.toggle_cursor()
