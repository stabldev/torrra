from textual import work
from textual.app import App

from torrra.screens.search import SearchScreen
from torrra.screens.welcome import WelcomeScreen


class TorrraApp(App):
    TITLE = "torrra"
    BINDINGS = [("q", "quit", "Quit")]

    @work
    async def on_mount(self) -> None:
        self.theme = "catppuccin-mocha"

        if query := await self.push_screen_wait(WelcomeScreen()):
            search_screen = SearchScreen(query)
            await self.push_screen(search_screen)


if __name__ == "__main__":
    app = TorrraApp()
    app.run()
