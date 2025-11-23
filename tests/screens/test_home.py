from typing import cast
from unittest.mock import MagicMock

import pytest
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Static

from torrra._types import Indexer, Torrent
from torrra.app import TorrraApp
from torrra.screens.home import HomeScreen


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
