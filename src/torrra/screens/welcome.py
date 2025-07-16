from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Input, Static

BANNER = """
▀█▀ █▀█ █▀▄ █▀▄ █▀▄ █▀█
 █  █ █ █▀▄ █▀▄ █▀▄ █▀█
 ▀  ▀▀▀ ▀ ▀ ▀ ▀ ▀ ▀ ▀ ▀
"""


class WelcomeScreen(Screen[str]):
    CSS_PATH = "welcome.css"

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
            yield Static("v0.2.3", id="version")

    @on(Input.Submitted, "#search")
    async def handle_search(self, event: Input.Submitted) -> None:
        if query := event.value:
            self.dismiss(query)
