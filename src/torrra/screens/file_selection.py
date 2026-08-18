from typing import Any, ClassVar

import libtorrent as lt
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.timer import Timer
from textual.widgets import SelectionList, Static
from textual.widgets.selection_list import Selection
from typing_extensions import override

from torrra._types import Torrent
from torrra.core.download import get_download_manager
from torrra.core.torrent import get_torrent_manager
from torrra.utils.helpers import human_readable_size
from torrra.widgets.spinner import Spinner


class FileSelectionList(SelectionList[int]):
    """Custom SelectionList with vim and arrow key navigation."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("space", "toggle_selection", "Toggle", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("up", "cursor_up", "Up", show=False),
    ]

    def action_toggle_selection(self) -> None:
        if self.highlighted is None and self.option_count > 0:
            self.highlighted = 0
        self._toggle_highlighted_selection()


class FileSelectionScreen(ModalScreen[list[int] | None]):
    """Compact modal screen to select specific files from a torrent before downloading or editing."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel"),
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
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.torrent: Torrent = torrent
        self.existing_priorities: list[int] | None = existing_priorities
        self._torrent_info: lt.torrent_info | None = torrent_info
        self.is_edit_mode: bool = is_edit_mode

        self._file_sizes: dict[int, int] = {}
        self._pad_file_indices: set[int] = set()
        self._poll_timer: Timer | None = None

        self._selection_list: FileSelectionList
        self._stats_label: Static
        self._torrent_name_label: Static
        self._loading_status_label: Static
        self._loading_container: Vertical
        self._body_container: Vertical
        self._footer_container: Vertical

    @override
    def compose(self) -> ComposeResult:
        action_verb = "save" if self.is_edit_mode else "download"
        with Vertical(id="file-selection-container"):
            with Vertical(id="file-selection-header"):
                yield Static(self.torrent.title, id="torrent-name")
                yield Static("Loading file list...", id="selection-stats")

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
                yield FileSelectionList()

            with Vertical(id="file-selection-footer", classes="hidden"):
                yield Static(
                    f"[dim]\\[space] toggle · \\[a] all · \\[n] none · \\[i] invert\n\\[enter] {action_verb} · \\[esc] cancel[/dim]",
                    id="shortcuts-hint",
                )

    def on_mount(self) -> None:
        self._selection_list = self.query_one(FileSelectionList)
        self._stats_label = self.query_one("#selection-stats", Static)
        self._torrent_name_label = self.query_one("#torrent-name", Static)
        self._loading_status_label = self.query_one("#loading-status-text", Static)
        self._loading_container = self.query_one("#file-selection-loading", Vertical)
        self._body_container = self.query_one("#file-selection-body", Vertical)
        self._footer_container = self.query_one("#file-selection-footer", Vertical)

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

        # Metadata not available yet, start fetching in background
        dm.add_torrent(self.torrent.magnet_uri, is_paused=True)
        self._poll_timer = self.set_interval(0.3, self._poll_metadata)

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

    @staticmethod
    def _format_file_prompt(file_path: str, size_str: str, max_width: int = 46) -> str:
        size_suffix = f" ({size_str})"
        if len(file_path) + len(size_suffix) <= max_width:
            return f"{file_path} [dim]({size_str})[/dim]"

        avail = max_width - len(size_suffix) - 3  # 3 chars for "..."
        if avail > 0:
            truncated = file_path[:avail] + "..."
        else:
            truncated = file_path[:8] + "..."
        return f"{truncated} [dim]({size_str})[/dim]"

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
        self._selection_list.clear_options()

        selections: list[Selection[int]] = []
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

            # Determine initial selected state
            if self.existing_priorities is not None and i < len(
                self.existing_priorities
            ):
                initial_state = self.existing_priorities[i] > 0
            else:
                initial_state = True

            size_str = human_readable_size(file_size)
            prompt = self._format_file_prompt(file_path, size_str, max_width=46)
            selections.append(Selection(prompt, value=i, initial_state=initial_state))

        self._selection_list.add_options(selections)
        if selections:
            self._selection_list.highlighted = 0

        # Switch UI from loading to loaded
        self._loading_container.add_class("hidden")
        self._body_container.remove_class("hidden")
        self._footer_container.remove_class("hidden")

        self._update_stats()
        self._selection_list.focus()

    @on(SelectionList.SelectedChanged)
    def on_selection_changed(self, _event: SelectionList.SelectedChanged) -> None:
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

    def key_enter(self) -> None:
        if self._torrent_info is None:
            self.action_skip_metadata()
        else:
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

        self.dismiss(priorities)

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
        if self._poll_timer:
            self._poll_timer.stop()
        self.dismiss([])
