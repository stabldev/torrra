import inspect
import time
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar

from rich.markup import escape
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static
from textual.worker import Worker
from typing_extensions import override

from torrra._types import TorrentFileStatus
from torrra.core.download import METADATA_TIMEOUT
from torrra.utils.helpers import human_readable_size
from torrra.widgets.data_table import AutoResizingDataTable
from torrra.widgets.spinner import Spinner

FileManagerResult = list[int] | None


class FileManagerScreen(ModalScreen[FileManagerResult]):
    """Modal showing per-file status that lets the user re/deselect files."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "close", "Close"),
        Binding("space", "toggle_file", "Toggle selection"),
    ]

    def __init__(
        self,
        title: str,
        load_status: Callable[[], Awaitable[list[TorrentFileStatus] | None]],
        *args: Any,
        metadata_timeout: float = METADATA_TIMEOUT,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._torrent_title: str = title
        self._load_status = load_status
        self._metadata_timeout: float = metadata_timeout

        self._statuses: list[TorrentFileStatus] = []
        self._selected: set[int] = set()
        self._total_size: int = 0
        self._table_ready: bool = False
        self._waiting_for_metadata: bool = False
        self._metadata_deadline: float = 0.0
        self._load_worker: Worker[None]

        # ui refs (cached later)
        self._loader: Vertical
        self._header: Static
        self._table: AutoResizingDataTable[str]
        self._footer: Horizontal

    @override
    def compose(self) -> ComposeResult:
        with Vertical(id="file_manager_container"):
            yield Static(f"[b]{self._torrent_title}[/b]", id="file_manager_title")
            with Vertical(id="file_manager_loader"):
                yield Static("Loading file status...")
                yield Spinner(name="dots")
            yield Static("", id="file_manager_header", classes="hidden")
            yield AutoResizingDataTable(id="file_manager_table", classes="hidden")
            yield Static(
                "[b]space[/b] toggle  ·  [b]j/k[/b] move  ·  [b]esc[/b] close",
                id="file_manager_hint",
            )
            with Horizontal(id="file_manager_footer", classes="hidden"):
                yield Button("Apply", variant="success", id="file_manager_apply")
                yield Button("Close", variant="error", id="file_manager_close")

    def on_mount(self) -> None:
        self._loader = self.query_one("#file_manager_loader", Vertical)
        self._header = self.query_one("#file_manager_header", Static)
        self._table = self.query_one("#file_manager_table", AutoResizingDataTable)
        self._footer = self.query_one("#file_manager_footer", Horizontal)
        self._table.expand_col = "name"
        for label, key, width in self.COLUMNS:
            self._table.add_column(label, width=width, key=key)

        self.set_interval(1.0, self._refresh)
        self._load_worker = self._load_data()

    COLUMNS: ClassVar[list[tuple[str, str, int]]] = [
        ("Sel", "sel", 3),
        ("Name", "name", 25),
        ("Size", "size", 8),
        ("Downloaded", "downloaded", 10),
        ("Done", "done", 5),
    ]

    @work(exclusive=True)
    async def _load_data(self) -> None:
        try:
            statuses = await self._fetch()
        except Exception as exc:  # noqa: BLE001 - surface any failure instead of hanging
            self._fail_load(f"Could not load file status: {exc}")
            return
        if statuses is None:
            self._waiting_for_metadata = True
            self._metadata_deadline = time.monotonic() + self._metadata_timeout
            return

        self._apply_statuses(statuses)

    async def _fetch(self) -> list[TorrentFileStatus] | None:
        result = self._load_status()
        if inspect.isawaitable(result):
            result = await result
        return result

    def _apply_statuses(self, statuses: list[TorrentFileStatus]) -> None:
        self._statuses = statuses
        try:
            self._populate()
        except Exception as exc:  # noqa: BLE001 - surface any render failure
            self.log.error("file manager: failed to render file list: %r", exc)
            self._fail_load(f"Could not load file status: {exc}")

    def _fail_load(self, message: str) -> None:
        if not self.is_mounted:
            return
        self.log.error("file manager: load failed: %s", message)
        self.notify(message, title="Load Error", severity="error")
        self.dismiss(None)

    def _populate(self) -> None:
        self._table.clear()
        self._total_size = sum(self._file_size(s) for s in self._statuses)
        self._selected = {s.index for s in self._statuses if s.priority > 0}

        for status in self._statuses:
            self._table.add_row(
                self._marker(status.index),
                escape(str(status.path or "")),
                human_readable_size(self._file_size(status), short=True),
                human_readable_size(self._file_downloaded(status), short=True),
                self._done_text(status),
                key=str(status.index),
            )

        self._table_ready = True
        self._waiting_for_metadata = False
        self._loader.add_class("hidden")
        self._header.remove_class("hidden")
        self._table.remove_class("hidden")
        self._footer.remove_class("hidden")
        self._update_header()
        self._table.focus()

    def _update_header(self) -> None:
        self._header.update(
            f"{len(self._statuses)} files - "
            f"{human_readable_size(self._total_size)}"
            f"  ·  selected {human_readable_size(self._selected_size())} "
            f"({len(self._selected)} files)"
        )

    def _selected_size(self) -> int:
        return sum(
            self._file_size(s) for s in self._statuses if s.index in self._selected
        )

    async def _refresh(self) -> None:
        if not self._table_ready:
            await self._try_first_load()
            return
        try:
            statuses = await self._fetch()
        except Exception as exc:  # noqa: BLE001 - keep the screen usable on refresh errors
            self.log.error("file manager: refresh failed: %r", exc)
            return
        if not statuses or not self._table_ready:
            return

        self._statuses = statuses
        for status in statuses:
            try:
                key = str(status.index)
                self._table.update_cell(
                    key,
                    "downloaded",
                    human_readable_size(self._file_downloaded(status), short=True),
                )
                self._table.update_cell(key, "done", self._done_text(status))
            except Exception as exc:  # noqa: BLE001 - skip cells that can't be updated
                self.log.debug("file manager: cell update failed: %r", exc)
                continue

    async def _try_first_load(self) -> None:
        if not self._waiting_for_metadata:
            return
        try:
            statuses = await self._fetch()
        except Exception as exc:  # noqa: BLE001 - surface any failure instead of hanging
            self._fail_load(f"Could not load file status: {exc}")
            return
        if statuses is not None:
            self._apply_statuses(statuses)
        elif time.monotonic() >= self._metadata_deadline:
            self._fail_load(
                "Could not load file status: timed out waiting for metadata"
            )

    def _marker(self, index: int) -> str:
        return "\\[x]" if index in self._selected else "\\[ ]"

    def _file_size(self, status: TorrentFileStatus) -> int:
        return max(0, int(status.size or 0))

    def _file_downloaded(self, status: TorrentFileStatus) -> int:
        return max(0, int(status.downloaded or 0))

    def _done_text(self, status: TorrentFileStatus) -> str:
        size = self._file_size(status)
        if size <= 0:
            return "100%"
        return f"{min(100, int(self._file_downloaded(status) / size * 100))}%"

    def action_toggle_file(self) -> None:
        row = self._table.cursor_row
        if row is None:
            return
        index = int(row)
        if index in self._selected:
            self._selected.discard(index)
        else:
            self._selected.add(index)
        self._table.update_cell(str(index), "sel", self._marker(index))
        self._update_header()

    def action_close(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "file_manager_apply":
            if not self._selected:
                self.notify(
                    "Select at least one file to download",
                    title="No Files Selected",
                    severity="warning",
                )
                return
            self.dismiss(sorted(self._selected))
        elif event.button.id == "file_manager_close":
            self.dismiss(None)
