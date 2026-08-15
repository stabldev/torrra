from typing import cast
from unittest.mock import MagicMock

import pytest
from textual.coordinate import Coordinate
from textual.geometry import Region
from textual.widgets import DataTable, Static
from textual.widgets.data_table import ColumnKey

from torrra._types import Indexer, Torrent
from torrra.app import TorrraApp
from torrra.screens.home import HomeScreen
from torrra.widgets.search import SearchContent


@pytest.fixture
def app():
    # start app on SearchScreen
    # by providing a default search_query
    return TorrraApp(
        indexer=Indexer(
            name="jackett", url="http://mock.indexer.url", api_key="mock_api_key"
        ),
        use_cache=False,
        search_query="arch linux iso",
    )


async def test_home_screen_search(app: TorrraApp, mock_indexer: MagicMock):
    mock_indexer.search.return_value = [
        Torrent(
            magnet_uri="magnet:?xt=urn:btih:mock",
            title="Arch Linux ISO (Mock)",
            size=840499200,
            seeders=523,
            leechers=17,
            source="MockIndexer",
        )
    ]

    async with app.run_test():
        assert isinstance(app.screen, HomeScreen)

        table = cast(
            DataTable[str], app.screen.query_one("SearchContent DataTable", DataTable)
        )
        # table should have results
        assert not table.has_class("hidden")

        # verify table has the correct number of rows and content
        assert table.row_count == len(mock_indexer.search.return_value)
        assert table.get_cell_at(Coordinate(0, 1)) == "Arch Linux ISO (Mock)"


async def test_home_screen_search_no_results(app: TorrraApp, mock_indexer: MagicMock):
    # ensure result is empty []
    mock_indexer.search.return_value = []

    async with app.run_test():
        assert isinstance(app.screen, HomeScreen)

        loader_status = app.screen.query_one("#loader Static", Static)
        table = app.screen.query_one("SearchContent DataTable")

        assert "Nothing Found" in str(loader_status.content)
        assert table.has_class("hidden")


# a broad search returns hundreds of rows with five-digit swarm counts, which
# is more than the "No" and "S:L" columns are declared wide enough to hold
WIDE_VALUE_FIXTURE = [
    Torrent(
        magnet_uri=f"magnet:?xt=urn:btih:wide{i}",
        title=f"Wide Release {i:03d}",
        size=1_000_000_000 + i,
        seeders=15128 - i,
        leechers=10059 - i,
        source="MockIndexer",
    )
    for i in range(150)
]


def _table_of(app: TorrraApp) -> DataTable[str]:
    return cast(
        DataTable[str], app.screen.query_one("SearchContent DataTable", DataTable)
    )


def _col_width(table: DataTable[str], key: str) -> int:
    return table.columns[ColumnKey(key)].width


def _rendered(table: DataTable[str]) -> str:
    """Exactly what the table paints, so clipped cells can't pass unnoticed."""
    lines = table.render_lines(Region(0, 0, table.size.width, table.size.height))
    return "\n".join("".join(segment.text for segment in line) for line in lines)


async def test_wide_swarm_counts_are_not_clipped_on_screen(
    app: TorrraApp, mock_indexer: MagicMock
):
    mock_indexer.search.return_value = list(WIDE_VALUE_FIXTURE)

    async with app.run_test(size=(120, 40)):
        table = _table_of(app)
        assert table.get_cell_at(Coordinate(0, 3)) == "15128:10059"
        assert "15128:10059" in _rendered(table), "widest S:L cell is being clipped"


async def test_fixed_columns_widen_to_fit_their_content(
    app: TorrraApp, mock_indexer: MagicMock
):
    mock_indexer.search.return_value = list(WIDE_VALUE_FIXTURE)

    async with app.run_test(size=(120, 40)):
        table = _table_of(app)

        for index, (_, key, _) in enumerate(SearchContent.COLS):
            if key == "title_col":  # absorbs whatever width is left over
                continue
            widest = max(
                len(str(table.get_cell_at(Coordinate(row, index))))
                for row in range(table.row_count)
            )
            assert _col_width(table, key) >= widest, f"{key} clips its own content"


async def test_columns_stay_at_their_declared_width_for_small_values(
    app: TorrraApp, mock_indexer: MagicMock
):
    mock_indexer.search.return_value = [
        Torrent(
            magnet_uri="magnet:?xt=urn:btih:small",
            title="Small Release",
            size=1_000_000_000,
            seeders=12,
            leechers=3,
            source="MockIndexer",
        )
    ]

    async with app.run_test(size=(120, 40)):
        table = _table_of(app)
        declared = {key: width for _, key, width in SearchContent.COLS}

        assert _col_width(table, "no_col") == declared["no_col"]
        assert _col_width(table, "size_col") == declared["size_col"]
        assert (
            _col_width(table, "seeders_leechers_col")
            == declared["seeders_leechers_col"]
        )


async def test_title_column_keeps_a_usable_width_in_a_narrow_terminal(
    app: TorrraApp, mock_indexer: MagicMock
):
    mock_indexer.search.return_value = list(WIDE_VALUE_FIXTURE)

    async with app.run_test(size=(40, 20)):
        table = _table_of(app)
        declared = {key: width for _, key, width in SearchContent.COLS}
        assert _col_width(table, "title_col") >= declared["title_col"]
