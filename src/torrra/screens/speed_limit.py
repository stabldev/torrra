from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Static
from typing_extensions import override

from torrra.utils.helpers import human_readable_size, parse_speed_limit


def _detect_unit(text: str) -> str:
    cleaned = (text or "").strip().lower()
    if cleaned.endswith("/s"):
        cleaned = cleaned[:-2].strip()
    if cleaned.endswith(("gib", "gb", "g")):
        return "GiB/s"
    if cleaned.endswith(("mib", "mb", "m")):
        return "MiB/s"
    if cleaned.endswith(("kib", "kb", "k")):
        return "KiB/s"
    if cleaned.endswith("b") and not cleaned.endswith(
        ("gib", "gb", "mib", "mb", "kib", "kb")
    ):
        return "B/s"
    return "KiB/s"


def _format_prefill_value(value: int | None) -> str:
    if value is None or value < 0:
        return ""
    if value % (1024**3) == 0:
        return f"{value // (1024**3)}G"
    if value % (1024**2) == 0:
        return f"{value // (1024**2)}M"
    if value % 1024 == 0:
        return str(value // 1024)
    return f"{value}B"


def _parse_speed_input(text: str) -> int:
    cleaned = (text or "").strip().lower()
    if cleaned.endswith("/s"):
        cleaned = cleaned[:-2].strip()
    if cleaned in ("", "0", "unlimited", "off", "none"):
        return -1
    try:
        val = float(cleaned)
        if val < 0:
            raise ValueError("speed limit must not be negative")
        return int(val * 1024)
    except ValueError:
        return parse_speed_limit(cleaned)


class SpeedLimitScreen(ModalScreen[tuple[int, int] | None]):
    """Set upload and download speed limits (bytes/sec) for one torrent.

    Returns ``(upload_limit, download_limit)`` or ``None`` if cancelled.
    ``-1`` in either value means unlimited.
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "cancel"),
        Binding("enter", "submit", "save"),
    ]

    def __init__(
        self,
        title: str,
        upload_limit: int | None,
        download_limit: int | None,
    ) -> None:
        super().__init__()
        self._torrent_title = title
        self._upload_limit = upload_limit
        self._download_limit = download_limit

        self._up_input: Input
        self._down_input: Input

    @override
    def compose(self) -> ComposeResult:
        down_val = _format_prefill_value(self._download_limit)
        up_val = _format_prefill_value(self._upload_limit)

        with Vertical(id="speed-limit-container"):
            yield Label("[b]Speed Limits[/b]", id="speed-limit-title")
            yield Label(self._torrent_title, id="speed-limit-name")
            with Vertical(id="speed-limit-fields"):
                with Horizontal(classes="speed-field-row"):
                    yield Label("Upload:", classes="speed-field-label")
                    yield Input(
                        placeholder="0",
                        value=up_val,
                        id="speed-up-input",
                    )
                    yield Label(
                        _detect_unit(up_val),
                        id="speed-up-unit",
                        classes="speed-unit-label",
                    )
                with Horizontal(classes="speed-field-row"):
                    yield Label("Download:", classes="speed-field-label")
                    yield Input(
                        placeholder="0",
                        value=down_val,
                        id="speed-down-input",
                    )
                    yield Label(
                        _detect_unit(down_val),
                        id="speed-down-unit",
                        classes="speed-unit-label",
                    )
            yield Static("", id="speed-limit-error", classes="error-text hidden")
            yield Static(
                "[dim](these won't exceed the global limits)[/dim]\n\\[enter] apply · \\[esc] cancel",
                id="speed-limit-footer",
            )

    def on_mount(self) -> None:
        self._up_input = self.query_one("#speed-up-input", Input)
        self._down_input = self.query_one("#speed-down-input", Input)
        self._up_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        unit_id = (
            "#speed-down-unit"
            if event.input.id == "speed-down-input"
            else "#speed-up-unit"
        )
        try:
            unit_label = self.query_one(unit_id, Label)
        except NoMatches:
            return
        unit_label.update(_detect_unit(event.value))

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        # Enter inside either input should submit the form. Consume the event
        # so it does not also bubble to any other handler.
        event.stop()
        self.action_submit()

    def action_submit(self) -> None:
        error_widget = self.query_one("#speed-limit-error", Static)
        try:
            up = _parse_speed_input(self._up_input.value)
            down = _parse_speed_input(self._down_input.value)
        except ValueError:
            error_widget.update(
                "Invalid speed. Use e.g. 500, 2M, 1.5G or 0 for unlimited."
            )
            error_widget.remove_class("hidden")
            return

        up_text = "unlimited" if up < 0 else f"{human_readable_size(up, short=True)}/s"
        down_text = (
            "unlimited" if down < 0 else f"{human_readable_size(down, short=True)}/s"
        )
        self.dismiss((up, down))
        self.notify(
            f"Limits set — Up: [b]{up_text}[/b] · Down: [b]{down_text}[/b]",
            title="Speed Limit",
        )
