from typing import Any, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static
from typing_extensions import override

from torrra.core.results import SortKey, sort_option_label


class SortSelectorScreen(ModalScreen[SortKey | None]):
    """Pick the field the results table is ordered by.

    Dismisses with the chosen key, or None when cancelled, so the caller
    decides what to do rather than this screen reaching back into the table.
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "close_screen"),
        Binding("k", "cursor_up"),
        Binding("j", "cursor_down"),
    ]

    def __init__(self, current: SortKey, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.current: SortKey = current

        self._list_view: ListView | None = None

    @override
    def compose(self) -> ComposeResult:
        with Vertical(id="sort-selector-container"):
            yield Label("[b]Sort Results By[/b]")
            yield Label("j/k: navigate - enter: apply", markup=False)
            yield ListView(
                *[
                    ListItem(Static(sort_option_label(key)), name=key.value)
                    for key in SortKey
                ]
            )

    def on_mount(self) -> None:
        self._list_view = self.query_one(ListView)
        # start on the active sort so enter is a no-op rather than a surprise
        for i, item in enumerate(self._list_view.children):
            if item.name == self.current.value:
                self._list_view.index = i
                break

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        name = event.item.name
        self.dismiss(SortKey(name) if name else None)

    def action_close_screen(self) -> None:
        self.dismiss(None)

    def action_cursor_up(self) -> None:
        if self._list_view is not None:
            self._list_view.action_cursor_up()

    def action_cursor_down(self) -> None:
        if self._list_view is not None:
            self._list_view.action_cursor_down()
