from typing import Any

import pytest
from textual.css.query import NoMatches
from textual.widgets import Input, Label

from torrra.app import TorrraApp
from torrra.core.config import get_config
from torrra.core.download import get_download_manager
from torrra.screens.speed_limit import SpeedLimitScreen
from torrra.widgets.status_bar import StatusBar


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


async def test_speed_limit_global_mode_hides_torrent_name(app: TorrraApp):
    async with app.run_test() as pilot:
        app.push_screen(
            SpeedLimitScreen(
                title="Movie",
                upload_limit=None,
                download_limit=None,
                global_mode=True,
            ),
            lambda _: None,
        )
        await pilot.pause()

        assert isinstance(app.screen, SpeedLimitScreen)
        title = str(app.screen.query_one("#speed-limit-title", Label).render())
        assert "Global" in title
        # the torrent name label is only shown in per-torrent mode
        with pytest.raises(NoMatches):
            app.screen.query_one("#speed-limit-name", Label)


async def test_global_speed_limit_toggle_flow(app_factory: Any, mock_config: Any):
    app = app_factory(search_query="arch linux iso")
    async with app.run_test() as pilot:
        # move focus off the search box so plain keys reach the app bindings
        app.screen.set_focus(None)
        await pilot.pause()

        # limits are unconfigured, so the first press opens the modal once
        await pilot.press("t")
        await pilot.pause()
        assert isinstance(app.screen, SpeedLimitScreen)

        up = app.screen.query_one("#speed-up-input", Input)
        down = app.screen.query_one("#speed-down-input", Input)
        up.value = "1M"
        down.value = "2M"

        await pilot.press("enter")
        await pilot.pause()

        cfg = get_config()
        assert cfg.get("speed_limit.enabled") is True
        assert cfg.get("speed_limit.upload_limit") == 1024 * 1024
        assert cfg.get("speed_limit.download_limit") == 2 * 1024**2

        # session-wide caps applied to libtorrent and badge visible
        dm = get_download_manager()
        settings = dm.session.get_settings()
        assert settings["upload_rate_limit"] == 1024 * 1024
        assert settings["download_rate_limit"] == 2 * 1024**2

        status_bar = app.screen.query_one(StatusBar)
        assert "TURTLE" in status_bar._limit_badge()

        # second press toggles back off
        await pilot.press("t")
        await pilot.pause()
        assert cfg.get("speed_limit.enabled") is False
        settings = dm.session.get_settings()
        assert settings["upload_rate_limit"] == 0
        assert settings["download_rate_limit"] == 0
        assert status_bar._limit_badge() == ""
