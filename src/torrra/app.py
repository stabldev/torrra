from typing import ClassVar

from textual import work
from textual.app import App
from textual.binding import BindingType
from textual.types import CSSPathType

from torrra._types import Indexer
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

    def __init__(self, provider: Indexer | None, use_cache: bool) -> None:
        super().__init__()
        self.provider: Indexer | None = provider
        self.use_cache: bool = use_cache

    @work
    async def on_mount(self) -> None:
        self.theme = (  # pyright: ignore[reportUnannotatedClassAttribute]
            "catppuccin-mocha"
        )

        if query := await self.push_screen_wait(WelcomeScreen(provider=self.provider)):
            from torrra.screens.search import SearchScreen

            search_screen = SearchScreen(
                indexer=self.provider, initial_query=query, use_cache=self.use_cache
            )
            await self.push_screen(search_screen)

    def action_toggle_dark_mode(self) -> None:
        self.theme = (
            "catppuccin-mocha"
            if self.theme == "catppuccin-latte"
            else "catppuccin-latte"
        )

    def action_clear_focus(self) -> None:
        self.set_focus(None)
