from typing import Any, cast

import pytest
from textual.widgets import ListView

from torrra.app import TorrraApp
from torrra.core.config import Config
from torrra.screens.theme_switcher import ThemeSwitcherScreen


@pytest.fixture
def app(app_factory: Any) -> TorrraApp:
    app = app_factory()
    app.theme = "textual-dark"  # default theme
    return app


async def test_theme_switcher_opens_and_closes_with_escape(app: TorrraApp):
    async with app.run_test() as pilot:
        await pilot.press("ctrl+t")
        assert isinstance(app.screen, ThemeSwitcherScreen)
        assert len(app.screen_stack) == 3  # default + welcome + theme switcher

        await pilot.press("escape")
        assert len(app.screen_stack) == 2  # default + welcome screen


async def test_theme_switcher_navigation_with_j_and_k(app: TorrraApp):
    async with app.run_test() as pilot:
        await pilot.press("ctrl+t")
        assert isinstance(app.screen, ThemeSwitcherScreen)

        list_view = app.screen.query_one("ListView", ListView)
        initial_index = cast(int, list_view.index)

        await pilot.press("j")
        assert list_view.index == initial_index + 1

        await pilot.press("k")
        assert list_view.index == initial_index


async def test_theme_switcher_select_theme_with_enter(app: TorrraApp):
    async with app.run_test() as pilot:
        await pilot.press("ctrl+t")
        assert isinstance(app.screen, ThemeSwitcherScreen)

        list_view = app.screen.query_one("ListView", ListView)
        target_theme = list_view.children[1].name

        # navigate and wait for preview
        list_view.index = 1
        await pilot.pause(0.6)
        assert app.theme == target_theme

        await pilot.press("enter")
        await pilot.pause()

        assert len(app.screen_stack) == 2  # default + welcome screen
        assert app.theme == target_theme


async def test_theme_switcher_cancel_selection_with_escape(
    app: TorrraApp, mock_config: Config
):
    original_theme = app.theme
    mock_config.set("general.theme", original_theme)

    async with app.run_test() as pilot:
        await pilot.press("ctrl+t")
        assert isinstance(app.screen, ThemeSwitcherScreen)

        list_view = app.screen.query_one("ListView", ListView)
        target_theme = list_view.children[1].name

        # navigate and wait for preview
        list_view.index = 1
        await pilot.pause(0.6)

        assert app.theme == target_theme

        await pilot.press("escape")
        await pilot.pause()

        assert len(app.screen_stack) == 2  # default + welcome screen
        assert app.theme == original_theme
        assert mock_config.get("general.theme") == original_theme
