from typing import ClassVar

from textual import work
from textual.app import App
from textual.binding import Binding, BindingType
from textual.css.query import NoMatches
from textual.reactive import Reactive
from textual.types import CSSPathType
from textual.widgets import Input
from typing_extensions import override

from torrra._types import Indexer
from torrra.core.config import get_config
from torrra.screens.help import HelpScreen
from torrra.screens.home import HomeScreen
from torrra.screens.theme_selector import ThemeSelectorScreen
from torrra.screens.welcome import GO_TO_DOWNLOADS, WelcomeScreen
from torrra.utils.fs import get_resource_path
from torrra.widgets.status_bar import StatusBar


class TorrraApp(App[None]):
    theme: Reactive[str]

    TITLE: str | None = "torrra"
    CSS_PATH: ClassVar[CSSPathType | None] = get_resource_path("app.tcss")
    ENABLE_COMMAND_PALETTE: ClassVar[bool] = False
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("ctrl+t", "switch_theme"),
        Binding("t", "toggle_speed_limit"),
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

    def _format_limit_text(self, limit: int) -> str:
        from torrra.utils.helpers import human_readable_size

        return (
            "unlimited" if limit <= 0 else f"{human_readable_size(limit, short=True)}/s"
        )

    def _refresh_status_bar(self) -> None:
        status_bar = self._find_status_bar()
        if status_bar is not None:
            status_bar.update_stats(*status_bar._last_stats)

    def _find_status_bar(self) -> "StatusBar | None":
        # the status bar lives on the home screen, which may be buried under
        # other screens (welcome/help) or not mounted at all yet
        for screen in self.screen_stack:
            try:
                return screen.query_one(StatusBar)
            except NoMatches:
                continue
        return None

    def action_toggle_speed_limit(self) -> None:
        from torrra.core.download import get_download_manager
        from torrra.screens.speed_limit import SpeedLimitScreen

        dm = get_download_manager()
        config = get_config()

        if dm.is_speed_limit_enabled():
            dm.set_speed_limit_enabled(False)
            self.notify("Turtle mode off — unlimited speed", title="Speed Limit")
            self._refresh_status_bar()
            return

        up = int(config.get("speed_limit.upload_limit", 0) or 0)
        down = int(config.get("speed_limit.download_limit", 0) or 0)

        def _enable_and_notify() -> None:
            up = int(config.get("speed_limit.upload_limit", 0) or 0)
            down = int(config.get("speed_limit.download_limit", 0) or 0)
            self.notify(
                f"Turtle mode on — [b]↓[/b] {self._format_limit_text(down)}"
                f" · [b]↑[/b] {self._format_limit_text(up)}",
                title="Speed Limit",
            )
            self._refresh_status_bar()

        if up <= 0 and down <= 0:
            # no global limits configured yet; collect them once via the modal
            def _on_limits_set(limits: tuple[int, int] | None) -> None:
                if limits is None:
                    return
                modal_up, modal_down = limits
                config.set("speed_limit.upload_limit", str(modal_up))
                config.set("speed_limit.download_limit", str(modal_down))
                dm.set_speed_limit_enabled(True)
                _enable_and_notify()

            self.push_screen(
                SpeedLimitScreen(
                    title="",
                    upload_limit=None,
                    download_limit=None,
                    global_mode=True,
                ),
                _on_limits_set,
            )
            return

        dm.set_speed_limit_enabled(True)
        _enable_and_notify()

    @work(exclusive=True)
    async def _show_welcome_and_search(self) -> None:
        # only ever called with an indexer configured (see on_mount)
        assert self.indexer is not None
        result = await self.push_screen_wait(WelcomeScreen(indexer=self.indexer))

        is_search = bool(result and result != GO_TO_DOWNLOADS)
        await self.push_screen(
            HomeScreen(
                indexer=self.indexer,
                search_query=result if is_search else "",
                use_cache=self.use_cache,
                direct_download=None,
                show_downloads=not is_search,
            )
        )
