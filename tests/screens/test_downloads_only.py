from typing import Any

import pytest
from textual.widgets import ContentSwitcher

from torrra.app import TorrraApp
from torrra.core import db as db_module
from torrra.screens.file_selection import FileSelectionScreen
from torrra.screens.home import HomeScreen
from torrra.widgets.downloads import DownloadsContent
from torrra.widgets.search import SearchContent
from torrra.widgets.sidebar import Sidebar


@pytest.fixture
def temp_db(tmp_path: Any, monkeypatch: pytest.MonkeyPatch):
    # downloads machinery touches the db on mount, so point it at a temp file
    monkeypatch.setattr(db_module, "DB_FILE", tmp_path / "test.db")
    monkeypatch.setattr(db_module, "DB_DIR", tmp_path)
    db_module.init_db()


def _sidebar_group_ids(sidebar: Sidebar) -> list[str | None]:
    return [
        child.data.get("group_id") if child.data else None
        for child in sidebar.root.children
    ]


@pytest.mark.usefixtures("temp_db")
async def test_downloads_view_launches_without_indexer():
    # `torrra downloads` - no indexer configured
    app = TorrraApp(
        indexer=None,
        use_cache=False,
        search_query=None,
        show_downloads=True,
    )

    async with app.run_test() as pilot:
        await pilot.pause()

        assert isinstance(app.screen, HomeScreen)
        # the downloads tab is active...
        assert (
            app.screen.query_one("#content_switcher", ContentSwitcher).current
            == "downloads_content"
        )
        # ...and search is entirely absent, both content and sidebar node
        assert len(app.screen.query(SearchContent)) == 0
        assert _sidebar_group_ids(app.screen.query_one(Sidebar)) == [
            "downloads_content"
        ]


@pytest.mark.usefixtures("temp_db")
async def test_direct_download_launches_without_indexer():
    # `torrra download <magnet>` - no indexer configured
    magnet = "magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567&dn=test"
    app = TorrraApp(
        indexer=None,
        use_cache=False,
        search_query=None,
        direct_download=magnet,
    )

    async with app.run_test() as pilot:
        await pilot.pause()

        # the file-selection modal opens over a downloads-only home screen
        assert isinstance(app.screen, FileSelectionScreen)
        home = next(s for s in app.screen_stack if isinstance(s, HomeScreen))
        assert (
            home.query_one("#content_switcher", ContentSwitcher).current
            == "downloads_content"
        )
        assert len(home.query(SearchContent)) == 0
        assert _sidebar_group_ids(home.query_one(Sidebar)) == ["downloads_content"]


@pytest.mark.usefixtures("temp_db")
async def test_downloads_view_never_reaches_welcome_without_indexer():
    # a bare downloads launch (no flags) must still skip the welcome/search
    # screen entirely rather than crash on the missing indexer
    app = TorrraApp(indexer=None, use_cache=False, search_query=None)

    async with app.run_test() as pilot:
        await pilot.pause()

        assert isinstance(app.screen, HomeScreen)
        assert len(app.screen.query(SearchContent)) == 0


@pytest.mark.usefixtures("temp_db")
async def test_downloads_content_is_interactive_without_indexer():
    # the downloads table should take focus so it is immediately usable
    app = TorrraApp(
        indexer=None,
        use_cache=False,
        search_query=None,
        show_downloads=True,
    )

    async with app.run_test() as pilot:
        await pilot.pause()

        downloads = app.screen.query_one(DownloadsContent)
        assert downloads._table.has_focus
