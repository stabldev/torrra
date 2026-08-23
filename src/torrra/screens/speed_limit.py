from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Static
from typing_extensions import override

from torrra.utils.helpers import human_readable_size, parse_speed_limit


def _format_prefill(value: int | None) -> str:
    if value is None or value < 0:
        return ""
    if value % (1024**3) == 0:
        return f"{value // (1024**3)} GB/s"
    if value % (1024**2) == 0:
        return f"{value // (1024**2)} MB/s"
    if value % 1024 == 0:
        return f"{value // 1024} KB/s"
    return f"{value} B/s"


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
        with Vertical(id="speed-limit-container"):
            yield Label("[b]Speed Limit[/b]", id="speed-limit-title")
            yield Label(self._torrent_title, id="speed-limit-name")
            yield Label("Enter a value with its unit — e.g. 500 KB, 2 MB, 1.5 GB.")
            yield Label("Use 0 for unlimited.")
            with Vertical(id="speed-limit-fields"):
                yield Label("Upload limit (per sec):")
                yield Input(
                    placeholder="0 = unlimited",
                    value=_format_prefill(self._upload_limit),
                    id="speed-up-input",
                )
                yield Label("Download limit (per sec):")
                yield Input(
                    placeholder="0 = unlimited",
                    value=_format_prefill(self._download_limit),
                    id="speed-down-input",
                )
            yield Static("", id="speed-limit-error", classes="error-text hidden")
            yield Static("enter apply · esc cancel", id="speed-limit-footer")

    def on_mount(self) -> None:
        self._up_input = self.query_one("#speed-up-input", Input)
        self._down_input = self.query_one("#speed-down-input", Input)
        self._up_input.focus()

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
            up = parse_speed_limit(self._up_input.value)
            down = parse_speed_limit(self._down_input.value)
        except ValueError:
            error_widget.update(
                "Invalid speed. Use e.g. 500 KB, 2 MB or 0 for unlimited."
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
