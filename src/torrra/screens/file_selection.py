from collections.abc import Awaitable, Callable
from typing import Any, ClassVar, Literal

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static
from textual.worker import Worker
from typing_extensions import override

from torrra._types import TorrentFile
from torrra.utils.helpers import human_readable_size
from torrra.widgets.file_tree import FileTree
from torrra.widgets.spinner import Spinner

DOWNLOAD_ALL: Literal["download_all"] = "download_all"

FileSelectionResult = list[int] | Literal["download_all"] | None


class FileSelectionScreen(ModalScreen[FileSelectionResult]):
    """Modal that lets the user pick which torrent files to download."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "download_all", "Download all"),
    ]

    def __init__(
        self,
        title: str,
        load_files: Callable[[], Awaitable[list[TorrentFile] | None]],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._torrent_title: str = title
        self._load_files = load_files

        self._files: list[TorrentFile] = []
        self._file_sizes: dict[int, int] = {}
        self._total_size: int = 0
        self._load_worker: Worker[None]

        # ui refs (cached later)
        self._loader: Vertical
        self._header: Static
        self._file_tree: FileTree
        self._footer: Horizontal

    @override
    def compose(self) -> ComposeResult:
        with Vertical(id="file_selection_container"):
            yield Static(f"[b]{self._torrent_title}[/b]", id="file_selection_title")
            with Vertical(id="file_selection_loader"):
                yield Static("Fetching torrent metadata...")
                yield Spinner(name="dots")
            yield Static("", id="file_selection_header", classes="hidden")
            yield FileTree(id="file_selection_tree", classes="hidden")
            yield Static(
                "[b]esc[/b] download all files  ·  [b]space[/b] toggle  ·  "
                "[b]j/k[/b] move  ·  [b]left/right[/b] expand",
                id="file_selection_hint",
            )
            with Horizontal(id="file_selection_footer", classes="hidden"):
                yield Button("Select all", id="select_all_button")
                yield Button("Select none", id="select_none_button")
                yield Button("Cancel", variant="error", id="cancel_button")
                yield Button("Download", variant="success", id="download_button")

    def on_mount(self) -> None:
        self._loader = self.query_one("#file_selection_loader", Vertical)
        self._header = self.query_one("#file_selection_header", Static)
        self._file_tree = self.query_one("#file_selection_tree", FileTree)
        self._footer = self.query_one("#file_selection_footer", Horizontal)

        self._load_worker = self._load_metadata()

    @work(exclusive=True)
    async def _load_metadata(self) -> None:
        files = await self._load_files()
        if files is None:
            self.notify(
                "Failed to fetch torrent metadata",
                title="Metadata Error",
                severity="error",
            )
            self.dismiss(None)
            return

        self._files = files
        self._show_file_list()

    def _show_file_list(self) -> None:
        self._file_sizes = {f.index: f.size for f in self._files}
        self._total_size = sum(f.size for f in self._files)

        self._loader.add_class("hidden")
        self._header.remove_class("hidden")
        self._file_tree.remove_class("hidden")
        self._footer.remove_class("hidden")

        self._file_tree.populate(self._files, selected={f.index for f in self._files})
        self._update_selection_header()
        self._file_tree.focus()

    def _update_selection_header(self) -> None:
        selected = self._file_tree.selected_indices()
        selected_size = sum(self._file_sizes.get(i, 0) for i in selected)
        self._header.update(
            f"{len(self._files)} files - {human_readable_size(self._total_size)}"
            f"  ·  selected {human_readable_size(selected_size)} ({len(selected)} files)"
        )

    def on_file_tree_selection_changed(self, event: FileTree.SelectionChanged) -> None:
        self._update_selection_header()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "select_all_button":
            self._file_tree.select_all()
        elif button_id == "select_none_button":
            self._file_tree.select_none()
        elif button_id == "cancel_button":
            self.dismiss(None)
        elif button_id == "download_button":
            selected = self._file_tree.selected_indices()
            if not selected:
                self.notify(
                    "Select at least one file to download",
                    title="No Files Selected",
                    severity="warning",
                )
                return
            self.dismiss(selected)

    def action_download_all(self) -> None:
        if not self._load_worker.is_finished:
            self._load_worker.cancel()
        self.dismiss(DOWNLOAD_ALL)
