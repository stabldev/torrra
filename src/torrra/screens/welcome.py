from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Grid
from textual.screen import Screen
from textual.widgets import Input, Static
from typing_extensions import override

from torrra._types import Indexer
from torrra._version import __version__

BANNER = """
▀█▀ █▀█ █▀▄ █▀▄ █▀▄ █▀█
 █  █ █ █▀▄ █▀▄ █▀▄ █▀█
 ▀  ▀▀▀ ▀ ▀ ▀ ▀ ▀ ▀ ▀ ▀
"""


class WelcomeScreen(Screen[str]):
    def __init__(self, indexer: Indexer) -> None:
        super().__init__()
        self.indexer: Indexer = indexer

    @override
    def compose(self) -> ComposeResult:
        with Container(id="welcome_container"):
            yield Static(BANNER, id="banner")
            yield Static(
                "\n".join(
                    [
                        "Find and download torrents right from here.",
                        "Powered by libtorrent and Python ❤️",
                    ]
                ),
                id="subtitle",
            )
            yield Input(placeholder="Search...", id="search")
            yield Static(
                f"v{__version__}{f' - {self.indexer.name}' if self.indexer else ''}",
                id="version",
            )
            with Container(id="commands_container"):
                with Grid():
                    yield Static("[key binds]", id="title", markup=False)
                    yield Static("[q]uit", markup=False)
                    yield Static("ctrl+q", classes="key")
                    yield Static("[t]heme switcher", markup=False)
                    yield Static("ctrl+t", classes="key")

    @on(Input.Submitted, "#search")
    async def handle_search(self, event: Input.Submitted) -> None:
        query = event.value

        if query and query.strip():
            self.dismiss(query)
