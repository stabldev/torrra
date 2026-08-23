from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import ProgressBar, Static
from typing_extensions import override


class DetailsPanel(Vertical):
    class Closed(Message):
        """Posted when the panel is closed."""

    def __init__(self, show_progress_bar: bool = False) -> None:
        super().__init__(classes="hidden")
        self.show_progress_bar: bool = show_progress_bar
        # UI refs
        self._content_widget: Static
        self._progress_bar: ProgressBar | None = None
        self._eta_widget: Static | None = None
        self._shortcuts_widget: Static

    @override
    def compose(self) -> ComposeResult:
        yield Static(id="details_content")
        if self.show_progress_bar:
            with Horizontal(id="details_progress_row"):
                yield ProgressBar(total=100, show_eta=False)
                yield Static(id="details_eta")
        yield Static(id="details_shortcuts")

    def on_mount(self) -> None:
        self._content_widget = self.query_one("#details_content", Static)
        if self.show_progress_bar:
            self._progress_bar = self.query_one(ProgressBar)
            self._eta_widget = self.query_one("#details_eta", Static)
        self._shortcuts_widget = self.query_one("#details_shortcuts", Static)
        # enable focus for this widget
        self.can_focus: bool = True

    def key_escape(self) -> None:
        self.add_class("hidden")
        self.post_message(self.Closed())

    def update_content(
        self,
        content: str,
        progress: float | None = None,
        eta: str | None = None,
        shortcuts: str | None = None,
    ) -> None:
        self._content_widget.update(content)
        if self._progress_bar and progress is not None:
            self._progress_bar.progress = progress
        if self._eta_widget and eta is not None:
            self._eta_widget.update(f"ETA: [b]{eta}[/b]" if eta else "")
        if shortcuts is not None:
            self._shortcuts_widget.update(shortcuts)
