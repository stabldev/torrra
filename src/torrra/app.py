from typing import Optional

from textual import work
from textual.app import App

from torrra._types import Provider
from torrra.screens.search import SearchScreen
from torrra.screens.welcome import WelcomeScreen
from torrra.utils.cli import parse_cli_args
from torrra.utils.provider import load_provider


class TorrraApp(App):
    TITLE = "torrra"
    CSS_PATH = "app.css"
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, provider: Optional[Provider]) -> None:
        super().__init__()
        self.provider = provider

    @work
    async def on_mount(self) -> None:
        self.theme = "catppuccin-mocha"

        if query := await self.push_screen_wait(WelcomeScreen(provider=self.provider)):
            search_screen = SearchScreen(query)
            await self.push_screen(search_screen)


def main():
    args = parse_cli_args()
    provider = None

    if args.jackett:
        provider = load_provider("jackett")

    app = TorrraApp(provider=provider)
    app.run()


if __name__ == "__main__":
    main()
