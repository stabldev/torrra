import pytest
from textual.widgets import ContentSwitcher

from torrra.app import TorrraApp
from torrra.screens.file_selection import FileSelectionScreen
from torrra.screens.home import HomeScreen
from torrra.widgets.downloads import DownloadsContent
from torrra.widgets.search import SearchContent
from torrra.widgets.sidebar import Sidebar


def _sidebar_group_ids(sidebar: Sidebar) -> list[str | None]:
    return [
        child.data.get("group_id") if child.data else None
        for child in sidebar.root.children
    ]


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


async def test_downloads_view_never_reaches_welcome_without_indexer():
    # a bare downloads launch (no flags) must still skip the welcome/search
    # screen entirely rather than crash on the missing indexer
    app = TorrraApp(indexer=None, use_cache=False, search_query=None)

    async with app.run_test() as pilot:
        await pilot.pause()

        assert isinstance(app.screen, HomeScreen)
        assert len(app.screen.query(SearchContent)) == 0


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


def test_app_rejects_invalid_download_path_at_startup(mock_config):
    # a download_path that cannot resolve must be reported once at startup,
    # not surface as an uncaught error when a torrent is later added
    mock_config.set("general.download_path", "$UNDEFINED_VAR_STARTUP/downloads")

    with pytest.raises(RuntimeError, match="invalid download_path configured"):
        TorrraApp(
            indexer=None,
            use_cache=False,
            search_query=None,
            show_downloads=True,
        )


def test_app_accepts_literal_dollar_in_download_path(mock_config):
    # regression: '$' is a legal filename character in an absolute path
    mock_config.set("general.download_path", "/Volumes/My$Drive/Downloads")

    # constructing the app is enough - validation happens in __init__, and
    # running the TUI here would touch the real torrent database
    app = TorrraApp(
        indexer=None,
        use_cache=False,
        search_query=None,
        show_downloads=True,
    )

    assert app.show_downloads is True
