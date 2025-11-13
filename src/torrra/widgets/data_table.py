import time
from typing import Any, ClassVar, TypeVar

from textual.binding import Binding, BindingType
from textual.reactive import reactive
from textual.widgets import DataTable
from textual.widgets.data_table import ColumnKey

T = TypeVar("T")


class AutoResizingDataTable(DataTable[T]):
    expand_col: reactive[str | None] = reactive(None)

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("k", "cursor_up"),
        Binding("j", "cursor_down"),
        Binding("G", "scroll_bottom"),
        Binding("ctrl+u", "page_up"),
        Binding("ctrl+d", "page_down"),
        Binding("l", "select_cursor"),
    ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._last_g_press: float = 0

    def key_g(self) -> None:
        current_time = time.time()
        if current_time - self._last_g_press < 0.4:
            self.action_scroll_top()
            self._last_g_press = 0
        else: # save for next event
            self._last_g_press = current_time

    def on_resize(self) -> None:
        self._resize_columns()
        self.refresh()

    def _resize_columns(self) -> None:
        if not self.columns or not self.expand_col:
            return

        # TODO: This is a bit of a hack. The 4 accounts for border and padding.
        # It would be better to get this from the widget's styles.
        border_and_padding = 4

        total_cell_padding = self.cell_padding * 2 * len(self.columns)
        expand_col_key = ColumnKey(self.expand_col)

        other_cols_width = sum(
            col.width for key, col in self.columns.items() if key != expand_col_key
        )

        available_width = self.size.width - border_and_padding - total_cell_padding
        expand_col_width = available_width - other_cols_width

        if expand_col_width > 0:
            self.columns[expand_col_key].width = expand_col_width
