from typing import ClassVar

from textual import work
from textual.app import App
from textual.binding import Binding, BindingType
from textual.reactive import Reactive
from textual.types import CSSPathType
from textual.widgets import Input
from typing_extensions import override

from torrra._types import Indexer
from torrra.core.config import get_config
from torrra.screens.help import HelpScreen
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
        Binding("ctrl+t", "switch_theme"),
        Binding("question_mark", "show_help", priority=True),
    ]

    def __init__(
        self,
        indexer: Indexer | None,
        use_cache: bool,
        search_query: str | None,
        direct_download: str | None = None,
        show_downloads: bool = False,
    ) -> None:
        super().__init__()
        self.indexer: Indexer | None = indexer
        self.use_cache: bool = use_cache
        self.search_query: str | None = search_query
        self.direct_download: str | None = direct_download
        self.show_downloads: bool = show_downloads

        # load theme from config file
        theme = get_config().get("general.theme", "textual-dark")
        if theme not in self.available_themes:
            raise RuntimeError(
                f"invalid theme '{theme}' configured.\n"
                + f"available themes: {', '.join(sorted(self.available_themes))}"
            )
        self.theme = theme

    async def on_mount(self) -> None:
        # the welcome screen only exists to collect a search query, so it is
        # reachable solely with a configured indexer and no other entry point
        # (direct download / downloads view / an already-supplied query)
        wants_downloads_view = bool(self.direct_download or self.show_downloads)
        has_query = bool(self.search_query and self.search_query.strip())

        if self.indexer is not None and not wants_downloads_view and not has_query:
            self._show_welcome_and_search()
        else:
            await self.push_screen(
                HomeScreen(
                    indexer=self.indexer,
                    search_query=self.search_query or "",
                    use_cache=self.use_cache,
                    direct_download=self.direct_download,
                    show_downloads=self.show_downloads,
                )
            )

    def action_switch_theme(self) -> None:
        self.push_screen(ThemeSelectorScreen())

    @override
    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        # "?" is bound with priority so it works from any list, but it is also a
        # perfectly ordinary character to type into a search query, so step
        # aside whenever a text box is focused and contains text
        typing_a_query = (
            action == "show_help"
            and isinstance(self.focused, Input)
            and bool(self.focused.value.strip())
        )
        return not typing_a_query

    def action_show_help(self) -> None:
        # the binding has priority, so it stays live while help is open;
        # make the same key close it rather than stack a second copy
        if isinstance(self.screen, HelpScreen):
            self.pop_screen()
        else:
            self.push_screen(HelpScreen())

    @work(exclusive=True)
    async def _show_welcome_and_search(self) -> None:
        # only ever called with an indexer configured (see on_mount)
        assert self.indexer is not None
        if search_query := await self.push_screen_wait(
            WelcomeScreen(indexer=self.indexer)
        ):  # show both screens
            await self.push_screen(
                HomeScreen(
                    indexer=self.indexer,
                    search_query=search_query,
                    use_cache=self.use_cache,
                    direct_download=None,
                    show_downloads=self.show_downloads,
                )
            )
