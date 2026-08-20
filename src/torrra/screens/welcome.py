from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Grid
from textual.screen import Screen
from textual.widgets import Input, Static
from typing_extensions import override

from torrra._types import Indexer
from torrra._version import __version__
from torrra.widgets.search_input import SearchInput

GO_TO_DOWNLOADS = "__go_to_downloads__"

BANNER = """
▀█▀ █▀█ █▀▄ █▀▄ █▀▄ █▀█
 █  █ █ █▀▄ █▀▄ █▀▄ █▀█
 ▀  ▀▀▀ ▀ ▀ ▀ ▀ ▀ ▀ ▀ ▀
"""


class WelcomeScreen(Screen[str]):
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+d", "go_to_downloads", priority=True),
    ]

    def __init__(self, indexer: Indexer) -> None:
        super().__init__()
        self.indexer: Indexer = indexer

    @override
    def compose(self) -> ComposeResult:
        with Container(id="welcome_container"):
            yield Static(BANNER, id="banner")
            yield Static(
                "Find and download torrents right from here.\nPowered by libtorrent and Python ❤️",
                id="subtitle",
            )
            yield SearchInput(placeholder="Search...", id="search")
            yield Static(
                f"v{__version__}{f' - {self.indexer.name}' if self.indexer else ''}",
                id="version",
            )
            with Container(id="commands_container"), Grid():
                yield Static("[key binds]", id="title", markup=False)
                yield Static("[q]uit", markup=False)
                yield Static("ctrl+q", classes="key")
                yield Static("[t]heme switcher", markup=False)
                yield Static("ctrl+t", classes="key")
                yield Static("[d]ownloads", markup=False)
                yield Static("ctrl+d", classes="key")
                yield Static("shortcuts", markup=False)
                yield Static("?", classes="key")

    def action_go_to_downloads(self) -> None:
        self.dismiss(GO_TO_DOWNLOADS)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if query := event.value.strip():
            self.dismiss(query)
