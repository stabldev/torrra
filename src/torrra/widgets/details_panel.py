from textual.app import ComposeResult
from textual.containers import Vertical
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

    @override
    def compose(self) -> ComposeResult:
        yield Static()
        if self.show_progress_bar:
            yield ProgressBar()

    def on_mount(self) -> None:
        self._content_widget = self.query_one(Static)
        if self.show_progress_bar:
            self._progress_bar = self.query_one(ProgressBar)
        # enable focus for this widget
        self.can_focus: bool = True

    def key_escape(self) -> None:
        self.add_class("hidden")
        self.post_message(self.Closed())

    def update(self, content: str, progress: float | None = None) -> None:
        self._content_widget.update(content)
        if self._progress_bar and progress is not None:
            self._progress_bar.progress = progress
