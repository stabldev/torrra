from typing import Any

import pytest
from textual.widgets import Input

from torrra.app import TorrraApp
from torrra.screens.speed_limit import SpeedLimitScreen


@pytest.fixture
def app(app_factory: Any) -> TorrraApp:
    return app_factory()


async def test_speed_limit_cancel_with_escape(app: TorrraApp):
    captured: list[tuple[int, int] | None] = []
    async with app.run_test() as pilot:
        app.push_screen(
            SpeedLimitScreen(title="Movie", upload_limit=None, download_limit=None),
            captured.append,
        )
        await pilot.pause()
        assert isinstance(app.screen, SpeedLimitScreen)

        await pilot.press("escape")
        await pilot.pause()

    assert captured == [None]


async def test_speed_limit_submit_with_values(app: TorrraApp):
    captured: list[tuple[int, int] | None] = []
    async with app.run_test() as pilot:
        app.push_screen(
            SpeedLimitScreen(title="Movie", upload_limit=None, download_limit=None),
            captured.append,
        )
        await pilot.pause()

        up = app.screen.query_one("#speed-up-input", Input)
        down = app.screen.query_one("#speed-down-input", Input)
        up.value = "1M"
        down.value = "2M"

        await pilot.press("enter")
        await pilot.pause()

    assert captured == [(1024 * 1024, 2 * 1024**2)]


async def test_speed_limit_submit_unlimited(app: TorrraApp):
    captured: list[tuple[int, int] | None] = []
    async with app.run_test() as pilot:
        app.push_screen(
            SpeedLimitScreen(title="Movie", upload_limit=1024, download_limit=2048),
            captured.append,
        )
        await pilot.pause()

        up = app.screen.query_one("#speed-up-input", Input)
        down = app.screen.query_one("#speed-down-input", Input)
        up.value = "0"
        down.value = "unlimited"

        await pilot.press("enter")
        await pilot.pause()

    assert captured == [(-1, -1)]


async def test_speed_limit_invalid_input_shows_error(app: TorrraApp):
    captured: list[tuple[int, int] | None] = []
    async with app.run_test() as pilot:
        app.push_screen(
            SpeedLimitScreen(title="Movie", upload_limit=None, download_limit=None),
            captured.append,
        )
        await pilot.pause()

        up = app.screen.query_one("#speed-up-input", Input)
        up.value = "garbage"

        await pilot.press("enter")
        await pilot.pause()

        # screen stays open and nothing was dismissed
        assert isinstance(app.screen, SpeedLimitScreen)
        assert not captured
        assert not app.screen.query_one("#speed-limit-error").has_class("hidden")
