from typing import Any, TypeVar

from textual.widgets import DataTable
from textual.widgets.data_table import ColumnKey

T = TypeVar("T")


class AutoResizingDataTable(DataTable[T]):
    def __init__(self, *args: Any, expand_col: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.expand_col: str = expand_col

    def on_resize(self) -> None:
        self._resize_columns()
        self.refresh()

    def _resize_columns(self) -> None:
        if not self.columns:
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
