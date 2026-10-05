from typing import Any

import pytest
from textual.widgets import Checkbox, Input

from torrra._types import TorrentOptions
from torrra.app import TorrraApp
from torrra.screens.torrent_options import TorrentOptionsScreen


@pytest.fixture
def app(app_factory: Any) -> TorrraApp:
    return app_factory()


async def test_torrent_options_cancel_with_escape(app: TorrraApp):
    captured: list[TorrentOptions | None] = []
    async with app.run_test() as pilot:
        app.push_screen(
            TorrentOptionsScreen(
                title="Ubuntu ISO", upload_limit=None, download_limit=None
            ),
            captured.append,
        )
        await pilot.pause()
        assert isinstance(app.screen, TorrentOptionsScreen)

        await pilot.press("escape")
        await pilot.pause()

    assert captured == [None]


async def test_torrent_options_submit_with_values(app: TorrraApp):
    captured: list[TorrentOptions | None] = []
    async with app.run_test() as pilot:
        app.push_screen(
            TorrentOptionsScreen(title="Ubuntu ISO"),
            captured.append,
        )
        await pilot.pause()

        up = app.screen.query_one("#option-up-input", Input)
        down = app.screen.query_one("#option-down-input", Input)
        ratio = app.screen.query_one("#option-ratio-input", Input)
        time_inp = app.screen.query_one("#option-time-input", Input)
        seq_cb = app.screen.query_one("#option-seq-checkbox", Checkbox)

        up.value = "1M"
        down.value = "2M"
        ratio.value = "1.5"
        time_inp.value = "2h"
        seq_cb.value = True

        await pilot.press("enter")
        await pilot.pause()

    assert len(captured) == 1
    opts = captured[0]
    assert opts is not None
    assert opts.upload_limit == 1024 * 1024
    assert opts.download_limit == 2 * 1024 * 1024
    assert opts.max_ratio == 1.5
    assert opts.max_seeding_time == 120
    assert opts.sequential_download is True


async def test_torrent_options_submit_unlimited(app: TorrraApp):
    captured: list[TorrentOptions | None] = []
    async with app.run_test() as pilot:
        app.push_screen(
            TorrentOptionsScreen(
                title="Debian ISO",
                upload_limit=1024,
                download_limit=2048,
                max_ratio=2.0,
                max_seeding_time=60,
                sequential_download=True,
            ),
            captured.append,
        )
        await pilot.pause()

        up = app.screen.query_one("#option-up-input", Input)
        down = app.screen.query_one("#option-down-input", Input)
        ratio = app.screen.query_one("#option-ratio-input", Input)
        time_inp = app.screen.query_one("#option-time-input", Input)
        seq_cb = app.screen.query_one("#option-seq-checkbox", Checkbox)

        up.value = "0"
        down.value = "off"
        ratio.value = "0"
        time_inp.value = "unlimited"
        seq_cb.value = False

        await pilot.press("enter")
        await pilot.pause()

    assert len(captured) == 1
    opts = captured[0]
    assert opts is not None
    assert opts.upload_limit == -1
    assert opts.download_limit == -1
    assert opts.max_ratio is None
    assert opts.max_seeding_time is None
    assert opts.sequential_download is False


async def test_torrent_options_invalid_speed_shows_error(app: TorrraApp):
    captured: list[TorrentOptions | None] = []
    async with app.run_test() as pilot:
        app.push_screen(
            TorrentOptionsScreen(title="Ubuntu ISO"),
            captured.append,
        )
        await pilot.pause()

        up = app.screen.query_one("#option-up-input", Input)
        up.value = "invalid_speed"

        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.screen, TorrentOptionsScreen)
        assert not captured
        assert not app.screen.query_one("#torrent-options-error").has_class("hidden")


async def test_torrent_options_invalid_ratio_shows_error(app: TorrraApp):
    captured: list[TorrentOptions | None] = []
    async with app.run_test() as pilot:
        app.push_screen(
            TorrentOptionsScreen(title="Ubuntu ISO"),
            captured.append,
        )
        await pilot.pause()

        ratio = app.screen.query_one("#option-ratio-input", Input)
        ratio.value = "not_a_ratio"

        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.screen, TorrentOptionsScreen)
        assert not captured
        assert not app.screen.query_one("#torrent-options-error").has_class("hidden")


async def test_torrent_options_invalid_time_shows_error(app: TorrraApp):
    captured: list[TorrentOptions | None] = []
    async with app.run_test() as pilot:
        app.push_screen(
            TorrentOptionsScreen(title="Ubuntu ISO"),
            captured.append,
        )
        await pilot.pause()

        time_inp = app.screen.query_one("#option-time-input", Input)
        time_inp.value = "bad_time"

        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.screen, TorrentOptionsScreen)
        assert not captured
        assert not app.screen.query_one("#torrent-options-error").has_class("hidden")


async def test_torrent_options_prefill_from_options(app: TorrraApp):
    opts = TorrentOptions(
        upload_limit=1024 * 1024,
        download_limit=2 * 1024 * 1024,
        max_ratio=1.75,
        max_seeding_time=180,
        sequential_download=True,
    )
    async with app.run_test() as pilot:
        app.push_screen(
            TorrentOptionsScreen(title="Ubuntu ISO", options=opts),
        )
        await pilot.pause()

        up = app.screen.query_one("#option-up-input", Input)
        down = app.screen.query_one("#option-down-input", Input)
        ratio = app.screen.query_one("#option-ratio-input", Input)
        time_inp = app.screen.query_one("#option-time-input", Input)
        seq_cb = app.screen.query_one("#option-seq-checkbox", Checkbox)

        assert up.value == "1M"
        assert down.value == "2M"
        assert ratio.value == "1.75"
        assert time_inp.value == "3h"
        assert seq_cb.value is True
