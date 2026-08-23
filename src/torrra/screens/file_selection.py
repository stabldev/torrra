from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import libtorrent as lt
from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.timer import Timer
from textual.widgets import Input, Static, Tree
from textual.widgets.tree import TreeNode
from typing_extensions import override

from torrra._types import DownloadSelection, Torrent
from torrra.core.config import get_config
from torrra.core.download import get_download_manager
from torrra.core.exceptions import ConfigError, DownloadError, DownloadPathError
from torrra.core.paths import normalize_download_path, prepare_download_path
from torrra.core.torrent import get_torrent_manager
from torrra.utils.helpers import human_readable_size
from torrra.widgets.spinner import Spinner


def _selection_mark(selected: int, total: int) -> str:
    """Return a colored checkbox marker for a node's selection state.

    Brackets are escaped so they survive rich markup processing, and the mark
    is tinted green (all), yellow (partial) or dim (none).
    """
    if selected == 0 or total == 0:
        return "[dim]\\[ ][/dim]"
    if selected == total:
        return "[green]\\[x][/green]"
    return "[yellow]\\[~][/yellow]"


class FileSelectionTree(Tree[int]):
    """A collapsible directory tree of a torrent's files with multi-selection.

    Folders are expandable/collapsible nodes; files are leaves. ``space``
    toggles the highlighted file (or a whole folder subtree), and the arrow
    keys navigate. Selection state is shown on each label and tracked as a set
    of file indices.
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("space", "toggle_selection", "Toggle", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("up", "cursor_up", "Up", show=False),
        Binding("left", "collapse_node", "Collapse folder", show=False),
        Binding("right", "expand_node", "Expand folder", show=False),
        Binding("h", "collapse_node", "Collapse folder", show=False),
        Binding("l", "expand_node", "Expand folder", show=False),
        Binding("enter", "confirm_selection", "Confirm", show=False),
    ]

    class SelectionChanged(Message):
        """Posted whenever the set of selected files changes."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.show_root = False

        self._selected: set[int] = set()
        self._file_sizes: dict[int, int] = {}
        self._nodes_by_index: dict[int, TreeNode[int]] = {}
        self._folder_nodes: list[TreeNode[int]] = []
        self._node_files: dict[TreeNode[int], set[int]] = {}
        self._base_labels: dict[TreeNode[int], str] = {}
        self._folder_nodes_by_path: dict[tuple[str, ...], TreeNode[int]] = {}

    @staticmethod
    def _format_file_prompt(file_path: str, size_str: str, max_width: int = 46) -> str:
        size_suffix = f" ({size_str})"
        if len(file_path) + len(size_suffix) <= max_width:
            return f"{file_path} [dim]({size_str})[/dim]"

        avail = max_width - len(size_suffix) - 3  # 3 chars for "..."
        truncated = file_path[: avail if avail > 0 else 8] + "..."
        return f"{truncated} [dim]({size_str})[/dim]"

    @property
    def selected(self) -> set[int]:
        return self._selected

    def file_labels(self) -> dict[int, str]:
        """Map each file index to its rendered label (for tests/introspection)."""
        return {i: str(node.label) for i, node in self._nodes_by_index.items()}

    def folder_labels(self) -> dict[str, str]:
        """Map each folder name to its rendered label (for tests/introspection)."""
        return {self._base_labels[n]: str(n.label) for n in self._folder_nodes}

    def folder_nodes(self) -> list[TreeNode[int]]:
        """Return the folder nodes in build order (for tests/introspection)."""
        return list(self._folder_nodes)

    def populate(
        self,
        raw_files: list[tuple[int, str, int]],
        common_root: str | None,
        existing_priorities: list[int] | None,
    ) -> None:
        """Build the folder tree from ``(index, path, size)`` tuples."""
        self.clear()
        self._selected = set()
        self._nodes_by_index = {}
        self._folder_nodes = []
        self._node_files = {}
        self._base_labels = {}
        self._folder_nodes_by_path = {}

        for index, file_path, file_size in raw_files:
            self._file_sizes[index] = file_size

            display_path = (
                file_path[len(common_root) + 1 :]
                if common_root and file_path.startswith(f"{common_root}/")
                else file_path
            )
            parts = display_path.split("/")

            parent: TreeNode[int] = self.root
            path_key: tuple[str, ...] = ()
            for part in parts[:-1]:
                path_key = path_key + (part,)
                folder = self._folder_nodes_by_path.get(path_key)
                if folder is None:
                    folder = parent.add(part, expand=True)
                    self._folder_nodes_by_path[path_key] = folder
                    self._folder_nodes.append(folder)
                    self._node_files[folder] = set()
                    self._base_labels[folder] = part
                parent = folder

            size_str = human_readable_size(file_size)
            prompt = self._format_file_prompt(parts[-1], size_str)
            leaf = parent.add_leaf(prompt, data=index)
            self._nodes_by_index[index] = leaf
            self._node_files[leaf] = {index}
            self._base_labels[leaf] = prompt

            ancestor: TreeNode[int] | None = leaf.parent
            while ancestor is not None and ancestor is not self.root:
                self._node_files[ancestor].add(index)
                ancestor = ancestor.parent

        if existing_priorities is not None:
            self._selected = {
                index
                for index in self._nodes_by_index
                if index < len(existing_priorities) and existing_priorities[index] > 0
            }
        else:
            self._selected = set(self._nodes_by_index)

        self._refresh_all_labels()
        if self._nodes_by_index:
            self.cursor_line = 0

    def _is_folder(self, node: TreeNode[int]) -> bool:
        return node.data is None

    def _selected_count(self, node: TreeNode[int]) -> int:
        return len(self._node_files[node] & self._selected)

    def _update_node_label(self, node: TreeNode[int]) -> None:
        base = self._base_labels[node]
        if self._is_folder(node):
            files = self._node_files[node]
            selected_count = self._selected_count(node)
            mark = _selection_mark(selected_count, len(files))
            node.set_label(f"{mark} {base} [dim]({selected_count}/{len(files)})[/dim]")
        else:
            mark = _selection_mark(1 if node.data in self._selected else 0, 1)
            node.set_label(f"{mark} {base}")

    def _update_ancestors(self, node: TreeNode[int]) -> None:
        parent: TreeNode[int] | None = node.parent
        while parent is not None and parent is not self.root:
            self._update_node_label(parent)
            parent = parent.parent

    def _refresh_all_labels(self) -> None:
        for node in self._folder_nodes:
            self._update_node_label(node)
        for node in self._nodes_by_index.values():
            self._update_node_label(node)

    def action_toggle_selection(self) -> None:
        node = self.cursor_node
        if node is None or node is self.root:
            return
        if self._is_folder(node):
            self._toggle_folder(node)
        else:
            assert node.data is not None
            self._toggle_file(node.data)

    def _toggle_file(self, index: int) -> None:
        if index in self._selected:
            self._selected.discard(index)
        else:
            self._selected.add(index)
        self._update_node_label(self._nodes_by_index[index])
        self._update_ancestors(self._nodes_by_index[index])
        self.post_message(self.SelectionChanged())

    def _toggle_folder(self, node: TreeNode[int]) -> None:
        files = self._node_files[node]
        if not files:
            return
        if files <= self._selected:
            self._selected -= files
        else:
            self._selected |= files
        self._refresh_all_labels()
        self.post_message(self.SelectionChanged())

    def select_all(self) -> None:
        self._selected = set(self._nodes_by_index)
        self._refresh_all_labels()
        self.post_message(self.SelectionChanged())

    def deselect_all(self) -> None:
        self._selected = set()
        self._refresh_all_labels()
        self.post_message(self.SelectionChanged())

    def toggle_all(self) -> None:
        all_indices = set(self._nodes_by_index)
        self._selected = all_indices - self._selected
        self._refresh_all_labels()
        self.post_message(self.SelectionChanged())

    def action_collapse_node(self) -> None:
        node = self.cursor_node
        if node is None or node is self.root:
            return
        if self._is_folder(node) and node.is_expanded:
            node.collapse()
        elif node.parent is not None and node.parent is not self.root:
            self.move_cursor(node.parent)

    def action_expand_node(self) -> None:
        node = self.cursor_node
        if node is None or node is self.root:
            return
        if self._is_folder(node) and node.is_collapsed:
            node.expand()


class FileSelectionScreen(ModalScreen[DownloadSelection | None]):
    """Compact modal screen to select specific files from a torrent before downloading or editing."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm_selection", "Download"),
        Binding("a", "select_all", "Select All"),
        Binding("n", "select_none", "Select None"),
        Binding("i", "invert_selection", "Invert"),
        Binding("d", "skip_metadata", "Download All", show=False),
    ]

    def __init__(
        self,
        torrent: Torrent,
        existing_priorities: list[int] | None = None,
        torrent_info: lt.torrent_info | None = None,
        is_edit_mode: bool = False,
        initial_save_path: str | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.torrent: Torrent = torrent
        self.existing_priorities: list[int] | None = existing_priorities
        self._torrent_info: lt.torrent_info | None = torrent_info
        self.is_edit_mode: bool = is_edit_mode
        self.initial_save_path = (
            initial_save_path if initial_save_path is not None else torrent.save_path
        )

        self._file_sizes: dict[int, int] = {}
        self._pad_file_indices: set[int] = set()
        self._poll_timer: Timer | None = None

        self._selection_list: FileSelectionTree
        self._stats_label: Static
        self._torrent_name_label: Static
        self._loading_status_label: Static
        self._loading_container: Vertical
        self._body_container: Vertical
        self._footer_container: Vertical
        self._save_path_input: Input | None = None
        self._default_save_path: Path | None = None

    @override
    def compose(self) -> ComposeResult:
        action_verb = "save" if self.is_edit_mode else "download"
        with Vertical(id="file-selection-container"):
            with Vertical(id="file-selection-header"):
                yield Static(self.torrent.title, id="torrent-name")
                yield Static("Loading file list...", id="selection-stats")
                if not self.is_edit_mode:
                    yield Static("Save to", id="save-path-label")
                    yield Input(
                        value=self.initial_save_path or "",
                        placeholder="Absolute path",
                        id="save-path",
                    )

            with Vertical(id="file-selection-loading"):
                with Vertical(id="loading-spinner-area"):
                    yield Static(
                        "Fetching torrent metadata...", id="loading-status-text"
                    )
                    yield Spinner(name="material")
                yield Static(
                    "[dim]hint: download all files without waiting\n\\[enter] download · \\[esc] cancel[/dim]",
                    id="loading-cancel-hint",
                )

            with Vertical(id="file-selection-body", classes="hidden"):
                yield FileSelectionTree("Files")

            with Vertical(id="file-selection-footer", classes="hidden"):
                yield Static(
                    f"[dim]\\[space] toggle · \\[a] all · \\[n] none · \\[i] invert\n\\[h/l/←/→] folders · \\[enter] {action_verb} · \\[esc] cancel[/dim]",
                    id="shortcuts-hint",
                )

    def on_mount(self) -> None:
        self._selection_list = self.query_one(FileSelectionTree)
        self._stats_label = self.query_one("#selection-stats", Static)
        self._torrent_name_label = self.query_one("#torrent-name", Static)
        self._loading_status_label = self.query_one("#loading-status-text", Static)
        self._loading_container = self.query_one("#file-selection-loading", Vertical)
        self._body_container = self.query_one("#file-selection-body", Vertical)
        self._footer_container = self.query_one("#file-selection-footer", Vertical)
        if not self.is_edit_mode:
            self._save_path_input = self.query_one("#save-path", Input)
            if self.initial_save_path is None:
                try:
                    self._default_save_path = normalize_download_path(
                        get_config().get("general.download_path")
                    )
                    self._save_path_input.value = str(self._default_save_path)
                except (ConfigError, DownloadPathError) as exc:
                    self._show_path_error(exc)

        if self._torrent_info is not None:
            self._populate_files(self._torrent_info)
            return

        dm = get_download_manager()
        handle = dm.torrents.get(self.torrent.magnet_uri)
        if handle and handle.is_valid() and handle.status().has_metadata:
            try:
                info = handle.torrent_file()
                if info:
                    self._populate_files(info)
                    return
            except (AttributeError, RuntimeError):
                pass

        try:
            save_path = self._validated_save_path()
            dm.fetch_metadata(self.torrent.magnet_uri, save_path=save_path)
        except (ConfigError, DownloadPathError) as exc:
            self._show_path_error(exc)
            return
        except DownloadError as exc:
            self.notify(str(exc), title="Metadata Fetch Failed", severity="error")
            self._loading_status_label.update("Unable to fetch torrent metadata.")
            return
        self._poll_timer = self.set_interval(0.3, self._poll_metadata)
        self.call_after_refresh(self.set_focus, None)

    def _validated_save_path(self) -> str | None:
        if self.is_edit_mode:
            return self.torrent.save_path

        assert self._save_path_input is not None
        raw_path = self._save_path_input.value.strip()
        if raw_path:
            selected_path = prepare_download_path(raw_path)
            if (
                self._default_save_path is not None
                and selected_path == self._default_save_path
            ):
                return None
            return str(selected_path)

        prepare_download_path(get_config().get("general.download_path"))
        return None

    def _show_path_error(self, error: Exception) -> None:
        self.notify(str(error), title="Invalid Download Path", severity="error")
        self._loading_status_label.update(
            "Choose a valid download directory, then press [b]enter[/b]."
        )
        if self._save_path_input is not None:
            self._save_path_input.focus()

    def _poll_metadata(self) -> None:
        dm = get_download_manager()
        handle = dm.torrents.get(self.torrent.magnet_uri)
        if handle and handle.is_valid():
            status = handle.status()
            if status.has_metadata:
                try:
                    info = handle.torrent_file()
                    if info:
                        if self._poll_timer:
                            self._poll_timer.stop()
                        self._populate_files(info)
                        return
                except (AttributeError, RuntimeError):
                    pass
            self._loading_status_label.update(
                f"Fetching torrent metadata...\n[dim](peers: {status.num_peers})[/dim]"
            )

    def _populate_files(self, info: lt.torrent_info) -> None:
        self._torrent_info = info
        fs = info.files()
        num_files = fs.num_files()

        # Update title if info provides a better one
        name = info.name()
        if name:
            self.torrent.title = name
            self._torrent_name_label.update(name)

        self._file_sizes.clear()
        self._pad_file_indices.clear()

        raw_files: list[tuple[int, str, int]] = []
        for i in range(num_files):
            # Check for pad files
            if hasattr(lt.file_storage, "flag_pad_file") and (
                fs.file_flags(i) & lt.file_storage.flag_pad_file
            ):
                self._pad_file_indices.add(i)
                continue

            file_path = fs.file_path(i).replace("\\", "/")
            file_size = fs.file_size(i)
            self._file_sizes[i] = file_size
            raw_files.append((i, file_path, file_size))

        # Check if all files share a common root directory
        common_root: str | None = None
        all_paths = [path for _, path, _ in raw_files]
        if all_paths and all("/" in p for p in all_paths):
            roots = {p.split("/", 1)[0] for p in all_paths}
            if len(roots) == 1:
                common_root = roots.pop()

        self._selection_list.populate(
            raw_files,
            common_root,
            self.existing_priorities,
        )

        # Switch UI from loading to loaded
        self._loading_container.add_class("hidden")
        self._body_container.remove_class("hidden")
        self._footer_container.remove_class("hidden")

        self._update_stats()
        self._selection_list.focus()

    @on(FileSelectionTree.SelectionChanged)
    def on_selection_changed(self, _event: FileSelectionTree.SelectionChanged) -> None:
        self._update_stats()

    def _update_stats(self) -> None:
        if not self._file_sizes:
            return

        selected_indices = set(self._selection_list.selected)
        selected_count = len(selected_indices)
        total_count = len(self._file_sizes)

        selected_size = sum(
            self._file_sizes[idx] for idx in selected_indices if idx in self._file_sizes
        )
        total_size = sum(self._file_sizes.values())

        sel_size_str = human_readable_size(selected_size)
        tot_size_str = human_readable_size(total_size)

        self._stats_label.update(
            f"Selected: [b]{selected_count}/{total_count}[/b] files · [b]{sel_size_str}[/b] / {tot_size_str}"
        )

    def on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            event.stop()
            event.prevent_default()
            self.action_confirm_selection()

    def action_confirm_selection(self) -> None:
        if self._torrent_info is None:
            self.action_skip_metadata()
            return

        selected_indices = set(self._selection_list.selected)
        if not selected_indices:
            self.notify(
                "Please select at least one file to download.",
                title="No Files Selected",
                severity="warning",
            )
            return

        num_files = self._torrent_info.files().num_files()
        priorities: list[int] = []
        for i in range(num_files):
            if i in self._pad_file_indices:
                priorities.append(4)  # Default priority for internal pad files
            elif i in selected_indices:
                priorities.append(4)  # Download selected file
            else:
                priorities.append(0)  # Skip unselected file

        try:
            save_path = self._validated_save_path()
        except (ConfigError, DownloadPathError) as exc:
            self._show_path_error(exc)
            return

        self.dismiss(DownloadSelection(priorities, save_path))

    def action_cancel(self) -> None:
        if self._poll_timer:
            self._poll_timer.stop()

        # Clean up temporary handle if this was a new download cancelled by the user
        if not self.is_edit_mode:
            tm = get_torrent_manager()
            if not tm.get_torrent(self.torrent.magnet_uri):
                dm = get_download_manager()
                dm.remove_torrent(self.torrent.magnet_uri)

        self.dismiss(None)

    def action_select_all(self) -> None:
        if self._body_container.has_class("hidden"):
            return
        self._selection_list.select_all()

    def action_select_none(self) -> None:
        if self._body_container.has_class("hidden"):
            return
        self._selection_list.deselect_all()

    def action_invert_selection(self) -> None:
        if self._body_container.has_class("hidden"):
            return
        self._selection_list.toggle_all()

    def action_skip_metadata(self) -> None:
        try:
            save_path = self._validated_save_path()
        except (ConfigError, DownloadPathError) as exc:
            self._show_path_error(exc)
            return

        if self._poll_timer:
            self._poll_timer.stop()
        self.dismiss(DownloadSelection(None, save_path))
