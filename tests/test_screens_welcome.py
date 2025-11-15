from textual.widgets import Input

from torrra._types import Indexer
from torrra.app import TorrraApp
from torrra.screens.search import SearchScreen
from torrra.screens.welcome import WelcomeScreen


async def test_welcome_screen():
    query = "arch linux iso"
    app = TorrraApp(
        indexer=Indexer(
            name="jackett", url="http://mock.indexer.url", api_key="mock_api_key"
        ),
        use_cache=False,
        search_query=None,
    )

    async with app.run_test() as pilot:
        # if no search_query is passed, WelcomeScreen should show
        assert isinstance(pilot.app.screen, WelcomeScreen)

        # check focus on search input
        search_input = pilot.app.screen.query_one("#search", Input)
        assert search_input.has_focus

        # unfocus with "escape" and check
        await pilot.press("escape")
        assert not search_input.has_focus

        # focus again
        search_input.focus()
        # wait for application state to update
        await pilot.pause()
        assert search_input.has_focus

        # simulate type query and press enter to submit
        await pilot.press(*list(query))
        await pilot.press("enter")

        # now SearchScreen should be shown with entered search_query
        assert isinstance(pilot.app.screen, SearchScreen)
        assert pilot.app.screen.search_query == query
