from typing import ClassVar

from textual import work
from textual.app import App
from textual.binding import Binding, BindingType
from textual.reactive import Reactive
from textual.types import CSSPathType

from torrra._types import Indexer
from torrra.core.config import config
from torrra.screens.home import HomeScreen
from torrra.screens.theme_selector import ThemeSelectorScreen
from torrra.screens.welcome import WelcomeScreen
from torrra.utils.fs import get_resource_path


class TorrraApp(App[None]):
    theme: Reactive[str]

    TITLE: str | None = "torrra"
    CSS_PATH: ClassVar[CSSPathType | None] = get_resource_path("app.tcss")
    ENABLE_COMMAND_PALETTE: ClassVar[bool] = False
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit"),
        Binding("escape", "clear_focus"),
        Binding("ctrl+t", "switch_theme"),
    ]

    def __init__(
        self, indexer: Indexer, use_cache: bool, search_query: str | None
    ) -> None:
        super().__init__()
        self.indexer: Indexer = indexer
        self.use_cache: bool = use_cache
        self.search_query: str | None = search_query

        # load theme from config file
        theme = config.get("general.theme", "textual-dark")
        if theme not in self.available_themes:
            error_message = (
                f"invalid theme '{theme}' configured.\n"
                f"available themes: {', '.join(sorted(self.available_themes))}"
            )
            raise RuntimeError(error_message)
        self.theme = theme

    async def on_mount(self) -> None:
        if not (self.search_query and self.search_query.strip()):
            self._show_welcome_and_search()
        else:  # direct show search screen
            await self.push_screen(
                HomeScreen(
                    indexer=self.indexer,
                    search_query=self.search_query,
                    use_cache=self.use_cache,
                )
            )

    @work(exclusive=True)
    async def _show_welcome_and_search(self) -> None:
        if search_query := await self.push_screen_wait(
            WelcomeScreen(indexer=self.indexer)
        ):  # show both screens
            await self.push_screen(
                HomeScreen(
                    indexer=self.indexer,
                    search_query=search_query,
                    use_cache=self.use_cache,
                )
            )

    def action_clear_focus(self) -> None:
        self.set_focus(None)

    def action_switch_theme(self) -> None:
        self.push_screen(ThemeSelectorScreen())
