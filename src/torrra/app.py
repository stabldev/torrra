from textual.app import App

from torrra.screens.search import SearchScreen


class TorrraApp(App):
    TITLE = "torrra"
    BINDINGS = [("q", "quit", "Quit")]

    def on_mount(self) -> None:
        self.theme = "catppuccin-mocha"
        self.push_screen(SearchScreen())


if __name__ == "__main__":
    app = TorrraApp()
    app.run()
