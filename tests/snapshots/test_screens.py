from typing import Any
import pytest
from textual.pilot import Pilot

from torrra._types import Indexer
from torrra.app import TorrraApp


@pytest.fixture
def app_factory():
    def _create_app(search_query: str | None = None):
        return TorrraApp(
            indexer=Indexer(
                name="jackett", url="http://mock.indexer.url", api_key="mock_api_key"
            ),
            use_cache=False,
            search_query=search_query,
        )

    return _create_app


def test_search_screen_snapshot(app_factory: Any, snap_compare: Any):
    app = app_factory("arch linux iso")
    assert snap_compare(app)


def test_welcome_screen_snapshot(app_factory: Any, snap_compare: Any):
    async def run_before(pilot: Pilot[Any]):
        await pilot.press(*list("arch linux iso"))

    app = app_factory()
    assert snap_compare(app, run_before=run_before)
