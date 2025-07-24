from typing import ClassVar, override

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Grid
from textual.screen import Screen
from textual.types import CSSPathType
from textual.widgets import Input, Static

from torrra._types import Provider
from torrra._version import __version__
from torrra.utils.fs import get_resource_path

BANNER = """
▀█▀ █▀█ █▀▄ █▀▄ █▀▄ █▀█
 █  █ █ █▀▄ █▀▄ █▀▄ █▀█
 ▀  ▀▀▀ ▀ ▀ ▀ ▀ ▀ ▀ ▀ ▀
"""


class WelcomeScreen(Screen[str]):
    CSS_PATH: ClassVar[CSSPathType | None] = get_resource_path("screens/welcome.css")

    def __init__(self, provider: Provider | None) -> None:
        super().__init__()
        self.provider: Provider | None = provider

    @override
    def compose(self) -> ComposeResult:
        with Container():
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
            provider_name = f" - {self.provider.name}" if self.provider else ""
            yield Static(f"v{__version__}{provider_name}", id="version")
            with Container(id="commands_container"):
                with Grid(id="commands"):
                    yield Static("[commands]", id="title", markup=False)
                    yield Static("[esc]ape focus", markup=False)
                    yield Static("esc", classes="key")
                    yield Static("toggle [d]ark mode", markup=False)
                    yield Static("d", classes="key")
                    yield Static("[q]uit", markup=False)
                    yield Static("q", classes="key")

    @on(Input.Submitted, "#search")
    async def handle_search(self, event: Input.Submitted) -> None:
        if query := event.value:
            self.dismiss(query)
