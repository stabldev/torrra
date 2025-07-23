from typing import ClassVar

from textual import work
from textual.app import App
from textual.binding import BindingType
from textual.types import CSSPathType

from torrra._types import Provider
from torrra.screens.search import SearchScreen
from torrra.screens.welcome import WelcomeScreen
from torrra.utils.fs import get_resource_path


class TorrraApp(App[None]):
    TITLE: str | None = "torrra"
    CSS_PATH: ClassVar[CSSPathType | None] = get_resource_path("app.css")
    BINDINGS: ClassVar[list[BindingType]] = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark_mode", "Toggle dark mode"),
        ("escape", "clear_focus", "Clear focus"),
    ]
    ENABLE_COMMAND_PALETTE: ClassVar[bool] = False

    def __init__(self, provider: Provider | None) -> None:
        super().__init__()
        self.provider: Provider | None = provider

    @work
    async def on_mount(self) -> None:
        self.theme = (
            "catppuccin-mocha"  # pyright: ignore[reportUnannotatedClassAttribute]
        )

        if query := await self.push_screen_wait(WelcomeScreen(provider=self.provider)):
            search_screen = SearchScreen(provider=self.provider, initial_query=query)
            await self.push_screen(search_screen)

    def action_toggle_dark_mode(self) -> None:
        self.theme = (
            "catppuccin-mocha"
            if self.theme == "catppuccin-latte"
            else "catppuccin-latte"
        )

    def action_clear_focus(self) -> None:
        self.set_focus(None)
