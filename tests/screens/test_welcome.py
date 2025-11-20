import pytest
from textual.widgets import Input, Static

from torrra._types import Indexer
from torrra._version import __version__
from torrra.app import TorrraApp
from torrra.screens.home import HomeScreen
from torrra.screens.welcome import WelcomeScreen


@pytest.fixture
def app() -> TorrraApp:
    return TorrraApp(
        indexer=Indexer(
            name="jackett", url="http://mock.indexer.url", api_key="mock_api_key"
        ),
        use_cache=False,
        search_query=None,
    )


async def test_welcome_screen_search_flow(app: TorrraApp):
    query = "arch linux iso"

    async with app.run_test() as pilot:
        assert isinstance(app.screen, WelcomeScreen)

        await pilot.press(*list(query))
        await pilot.press("enter")

        # should show SearchScreen with dismissed search_query
        assert isinstance(app.screen, HomeScreen)
        assert app.screen.search_query == query


async def test_welcome_screen_focus_handling(app: TorrraApp):
    async with app.run_test() as pilot:
        assert isinstance(app.screen, WelcomeScreen)

        search_input = app.screen.query_one("#search", Input)
        assert search_input.has_focus

        # unfocus
        await pilot.press("escape")
        assert not search_input.has_focus

        search_input.focus()
        # wait for application state to update
        await pilot.pause()
        assert search_input.has_focus


async def test_welcome_screen_ui_composition(app: TorrraApp):
    async with app.run_test():
        assert isinstance(app.screen, WelcomeScreen)

        # check for all major static elements by their ID
        assert app.screen.query_one("#banner")
        assert app.screen.query_one("#subtitle")
        assert app.screen.query_one("#version")
        assert app.screen.query_one("Grid #title")


async def test_welcome_screen_version_display(app: TorrraApp):
    async with app.run_test():
        assert isinstance(app.screen, WelcomeScreen)

        version_widget = app.screen.query_one("#version", Static)
        version_text = str(version_widget.content)

        # version should be same
        assert __version__ in version_text
        assert app.indexer.name in version_text


async def test_welcome_screen_empty_search_does_not_dismiss(app: TorrraApp):
    async with app.run_test() as pilot:
        assert isinstance(app.screen, WelcomeScreen)

        # test with empty value
        await pilot.press("enter")
        # should be still on WelcomeScreen
        assert isinstance(app.screen, WelcomeScreen)

        # test with whitespace
        await pilot.press(" ", " ", " ")
        await pilot.press("enter")
        # should be still on WelcomeScreen
        assert isinstance(app.screen, WelcomeScreen)
