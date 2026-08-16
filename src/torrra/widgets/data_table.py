import time
from typing import Any, ClassVar, TypeVar

from textual.binding import Binding, BindingType
from textual.reactive import reactive
from textual.render import measure
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
        # width each column was declared with, kept as a floor by fit_columns
        self._min_col_widths: dict[ColumnKey, int] = {}

    def key_g(self) -> None:
        current_time = time.time()
        if current_time - self._last_g_press < 0.4:
            self.action_scroll_top()
            self._last_g_press = 0
        else:  # save for next event
            self._last_g_press = current_time

    def on_resize(self) -> None:
        self._resize_columns()
        self.refresh(layout=True)

    def fit_columns(self) -> None:
        """Grow fixed-width columns so their cells aren't silently truncated.

        A cell wider than its column is clipped with no ellipsis, so it reads as
        wrong data rather than as cut-off data. Both happen on any broad search:
        past row 99 the `No` column renders 1204 as "12", and a large swarm
        renders 1882:8877 as "1882:8". Declared widths act as a floor, so
        columns only ever grow, and the expanding column absorbs the difference.
        """
        if not self.columns:
            return

        console = self.app.console
        expand_col_key = ColumnKey(self.expand_col) if self.expand_col else None
        resized = False

        for key, col in self.columns.items():
            if key == expand_col_key:  # sized by _resize_columns from what's left
                continue

            minimum = self._min_col_widths.setdefault(key, col.width)
            content_width = max(
                (measure(console, str(cell), 1) for cell in self.get_column(key)),
                default=0,
            )

            width = max(minimum, content_width)
            if width != col.width:
                col.width = width
                resized = True

        if resized:
            self._resize_columns()
            self.refresh(layout=True)

    def _resize_columns(self) -> None:
        if not self.columns or not self.expand_col:
            return

        total_cell_padding = self.cell_padding * 2 * len(self.columns)
        expand_col_key = ColumnKey(self.expand_col)
        expand_col = self.columns.get(expand_col_key)
        if expand_col is None:
            return

        other_cols_width = sum(
            col.width for key, col in self.columns.items() if key != expand_col_key
        )

        available_width = self.size.width - total_cell_padding
        expand_col_width = available_width - other_cols_width

        # never let a wide neighbour squeeze the expanding column out of existence
        minimum = self._min_col_widths.setdefault(expand_col_key, expand_col.width)
        if expand_col_width > 0:
            expand_col.width = max(minimum, expand_col_width)
