import asyncio
from typing import Any, ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.types import CSSPathType
from textual.widgets import Label, ListItem, ListView, Static
from textual.worker import Worker
from typing_extensions import override

from torrra.core.config import config
from torrra.utils.fs import get_resource_path


class ThemeSwitcherScreen(ModalScreen[None]):
    CSS_PATH: ClassVar[CSSPathType | None] = get_resource_path("app.tcss")
    BINDINGS: list[BindingType] = [
        Binding("escape", "close_screen"),
    ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.original_theme: str = self.app.theme
        self._update_worker: Worker[None] | None = None

    @override
    def compose(self) -> ComposeResult:
        with Vertical(id="theme-switcher-container"):
            yield Label("[b]Select a Theme[/b]")
            yield Label("j/k: navigate - enter: save", markup=False)
            yield ListView(
                *[
                    ListItem(Static(theme), name=theme)
                    for theme in sorted(self.app.available_themes)
                ]
            )

    def on_mount(self) -> None:
        theme_list = self.query_one(ListView)
        for i, item in enumerate(theme_list.children):
            if item.name == self.app.theme:
                theme_list.index = i
                break

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        self._cancel_update_worker()
        if event.item is not None and event.item.name is not None:
            self._update_worker = self._set_theme(event.item.name)

    def on_list_view_selected(self) -> None:
        self._cancel_update_worker()
        config.set("general.theme", self.app.theme)
        self.app.pop_screen()

    def action_close_screen(self) -> None:
        self._cancel_update_worker()
        self.app.theme = self.original_theme
        self.app.pop_screen()

    @work(exclusive=True)
    async def _set_theme(self, theme: str) -> None:
        await asyncio.sleep(0.5)
        self.app.theme = theme

    def _cancel_update_worker(self) -> None:
        if self._update_worker is not None:
            self._update_worker.cancel()
