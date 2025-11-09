from typing import ClassVar

from textual import work
from textual.app import App
from textual.binding import BindingType
from textual.reactive import Reactive
from textual.types import CSSPathType

from torrra._types import Indexer
from torrra.core.config import config
from torrra.screens.welcome import WelcomeScreen
from torrra.utils.fs import get_resource_path


class TorrraApp(App[None]):
    theme: Reactive[str]

    TITLE: str | None = "torrra"
    CSS_PATH: ClassVar[CSSPathType | None] = get_resource_path("app.css")
    ENABLE_COMMAND_PALETTE: ClassVar[bool] = False
    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "clear_focus", "Clear focus"),
    ]

    def __init__(self, indexer: Indexer, use_cache: bool) -> None:
        super().__init__()
        self.indexer: Indexer = indexer
        self.use_cache: bool = use_cache

        # load theme from config file (with fallback)
        self.theme = config.get("general.theme", "textual-dark")

    @work
    async def on_mount(self) -> None:
        if query := await self.push_screen_wait(WelcomeScreen(indexer=self.indexer)):
            from torrra.screens.search import SearchScreen

            search_screen = SearchScreen(indexer=self.indexer, query=query)
            await self.push_screen(search_screen)

    def action_clear_focus(self) -> None:
        self.set_focus(None)
