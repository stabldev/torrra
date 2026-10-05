from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import Checkbox, Input, Label, Static
from typing_extensions import override

from torrra._types import TorrentOptions
from torrra.screens.speed_limit import (
    _detect_unit,
    _format_prefill_value,
    _parse_speed_input,
)
from torrra.utils.helpers import (
    format_ratio_limit,
    format_seeding_time,
    parse_ratio_limit,
    parse_seeding_time,
)


class TorrentOptionsScreen(ModalScreen[TorrentOptions | None]):
    """Configure speed limits, seed limits, and sequential downloading for one torrent.

    Returns ``TorrentOptions`` or ``None`` if cancelled.
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "cancel"),
        Binding("enter", "submit", "save"),
    ]

    def __init__(
        self,
        title: str,
        options: TorrentOptions | None = None,
        upload_limit: int | None = None,
        download_limit: int | None = None,
        max_ratio: float | None = None,
        max_seeding_time: int | None = None,
        sequential_download: bool = False,
    ) -> None:
        super().__init__()
        self._torrent_title = title
        if options is not None:
            self._upload_limit = options.upload_limit
            self._download_limit = options.download_limit
            self._max_ratio = options.max_ratio
            self._max_seeding_time = options.max_seeding_time
            self._sequential_download = options.sequential_download
        else:
            self._upload_limit = upload_limit
            self._download_limit = download_limit
            self._max_ratio = max_ratio
            self._max_seeding_time = max_seeding_time
            self._sequential_download = sequential_download

        self._up_input: Input
        self._down_input: Input
        self._ratio_input: Input
        self._time_input: Input
        self._seq_checkbox: Checkbox

    @override
    def compose(self) -> ComposeResult:
        down_val = _format_prefill_value(self._download_limit)
        up_val = _format_prefill_value(self._upload_limit)
        ratio_val = format_ratio_limit(self._max_ratio)
        time_val = format_seeding_time(self._max_seeding_time)

        with Vertical(id="torrent-options-container"):
            yield Label("[b]Torrent Options[/b]", id="torrent-options-title")
            yield Label(self._torrent_title, id="torrent-options-name")
            with Vertical(id="torrent-options-fields"):
                with Horizontal(classes="torrent-option-row"):
                    yield Label("Upload:", classes="torrent-option-label")
                    yield Input(
                        placeholder="0",
                        value=up_val,
                        id="option-up-input",
                    )
                    yield Label(
                        _detect_unit(up_val),
                        id="option-up-unit",
                        classes="torrent-option-unit-label",
                    )
                with Horizontal(classes="torrent-option-row"):
                    yield Label("Download:", classes="torrent-option-label")
                    yield Input(
                        placeholder="0",
                        value=down_val,
                        id="option-down-input",
                    )
                    yield Label(
                        _detect_unit(down_val),
                        id="option-down-unit",
                        classes="torrent-option-unit-label",
                    )
                yield Label(
                    "[dim]These will not exceed global limits.[/dim]",
                    id="torrent-options-speed-hint",
                    classes="torrent-option-hint",
                )
                with Horizontal(classes="torrent-option-row"):
                    yield Label("Max Ratio:", classes="torrent-option-label")
                    yield Input(
                        placeholder="0",
                        value=ratio_val,
                        id="option-ratio-input",
                    )
                    yield Label(
                        "ratio",
                        id="option-ratio-unit",
                        classes="torrent-option-unit-label",
                    )
                with Horizontal(classes="torrent-option-row"):
                    yield Label("Seed Time:", classes="torrent-option-label")
                    yield Input(
                        placeholder="0",
                        value=time_val,
                        id="option-time-input",
                    )
                    yield Label(
                        "duration",
                        id="option-time-unit",
                        classes="torrent-option-unit-label",
                    )
                yield Label(
                    "[dim]e.g. 30m, 2h, 1d (or in minutes)[/dim]",
                    id="torrent-options-time-hint",
                    classes="torrent-option-hint",
                )
                with Horizontal(classes="torrent-option-row checkbox-row"):
                    yield Checkbox(
                        "Sequential download",
                        value=self._sequential_download,
                        id="option-seq-checkbox",
                    )
            yield Static("", id="torrent-options-error", classes="error-text hidden")
            yield Static(
                "[dim]hint: 0 or empty = unlimited / off[/dim]\n\\[enter] apply · \\[esc] cancel",
                id="torrent-options-footer",
            )

    def on_mount(self) -> None:
        self._up_input = self.query_one("#option-up-input", Input)
        self._down_input = self.query_one("#option-down-input", Input)
        self._ratio_input = self.query_one("#option-ratio-input", Input)
        self._time_input = self.query_one("#option-time-input", Input)
        self._seq_checkbox = self.query_one("#option-seq-checkbox", Checkbox)
        self._up_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "option-down-input":
            unit_id = "#option-down-unit"
        elif event.input.id == "option-up-input":
            unit_id = "#option-up-unit"
        else:
            return

        try:
            unit_label = self.query_one(unit_id, Label)
        except NoMatches:
            return
        unit_label.update(_detect_unit(event.value))

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.action_submit()

    def action_submit(self) -> None:
        error_widget = self.query_one("#torrent-options-error", Static)
        try:
            up = _parse_speed_input(self._up_input.value)
            down = _parse_speed_input(self._down_input.value)
        except ValueError:
            error_widget.update(
                "Invalid speed limit. Use e.g. 500k, 2M, 1.5G or 0 for unlimited."
            )
            error_widget.remove_class("hidden")
            return

        try:
            ratio = parse_ratio_limit(self._ratio_input.value)
        except ValueError:
            error_widget.update(
                "Invalid max ratio. Use e.g. 1.0, 1.5, 2.0 or 0 for unlimited."
            )
            error_widget.remove_class("hidden")
            return

        try:
            seeding_time = parse_seeding_time(self._time_input.value)
        except ValueError:
            error_widget.update(
                "Invalid seed time. Use e.g. 30m, 2h, 1d or 0 for unlimited."
            )
            error_widget.remove_class("hidden")
            return

        error_widget.add_class("hidden")
        self.dismiss(
            TorrentOptions(
                upload_limit=up if up >= 0 else -1,
                download_limit=down if down >= 0 else -1,
                max_ratio=ratio if ratio > 0 else None,
                max_seeding_time=seeding_time if seeding_time > 0 else None,
                sequential_download=bool(self._seq_checkbox.value),
            )
        )
