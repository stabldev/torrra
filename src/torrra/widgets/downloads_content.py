from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static
from typing_extensions import override


class DownloadsContent(Vertical):
    def __init__(self) -> None:
        super().__init__(id="downloads_content")

    @override
    def compose(self) -> ComposeResult:
        yield Static("Downloads section")
