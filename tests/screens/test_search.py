from typing import Any, cast
import pytest
from unittest.mock import AsyncMock, MagicMock

from textual.coordinate import Coordinate
from textual.widgets import DataTable, Static

from torrra._types import Indexer, Torrent
from torrra.app import TorrraApp
from torrra.screens.search import SearchScreen


@pytest.fixture
def mock_indexer(monkeypatch: pytest.MonkeyPatch):
    mock_indexer_instance = MagicMock()
    mock_indexer_instance.search = AsyncMock(return_value=[])

    # patch the method that creates the indexer to return mock instance
    def _mock_get_indexer_instance(self: Any):  # pyright: ignore[reportUnusedParameter]
        return mock_indexer_instance

    monkeypatch.setattr(
        "torrra.screens.search.SearchScreen._get_indexer_instance",
        _mock_get_indexer_instance,
    )
    # return patched indexer for test cases
    return mock_indexer_instance


@pytest.fixture
def app():
    # start app on SearchScreen
    return TorrraApp(
        indexer=Indexer(
            name="jackett", url="http://mock.indexer.url", api_key="mock_api_key"
        ),
        use_cache=False,
        search_query="arch linux iso",
    )


async def test_search_screen_search(app: TorrraApp, mock_indexer: MagicMock):
    mock_indexer.search.return_value = [
        Torrent(
            "Arch Linux ISO (Mock)",
            840499200,
            523,
            17,
            "MockIndexer",
            "magnet:?xt=urn:btih:mock",
        )
    ]

    async with app.run_test() as pilot:
        # should show SearchScreen first
        assert isinstance(pilot.app.screen, SearchScreen)

        # (doesnt support generic type, so used casting)
        table = cast(
            DataTable[str],
            pilot.app.screen.query_one("#results_table", DataTable),
        )

        # table should have results
        assert not table.has_class("hidden")

        # verify table has the correct number of rows and content
        assert table.row_count == len(mock_indexer.search.return_value)
        assert table.get_cell_at(Coordinate(0, 1)) == "Arch Linux ISO (Mock)"


async def test_search_screen_no_results(app: TorrraApp, mock_indexer: MagicMock):
    # ensure result is empty []
    mock_indexer.search.return_value = []

    async with app.run_test() as pilot:
        # should show SearchScreen first
        assert isinstance(pilot.app.screen, SearchScreen)

        loader_status = pilot.app.screen.query_one("#loader #status", Static)
        # (doesnt support generic type, so used casting)
        table = cast(
            DataTable[str],
            pilot.app.screen.query_one("#results_table", DataTable),
        )

        assert "Nothing Found" in str(loader_status.content)
        assert table.has_class("hidden")
