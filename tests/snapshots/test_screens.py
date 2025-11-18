from typing import Any

from textual.pilot import Pilot


def test_search_screen_snapshot(app_factory: Any, snap_compare: Any):
    async def run_before(pilot: Pilot[Any]):
        await pilot.pause(0.1)  # fixes minor timing issue

    app = app_factory("arch linux iso")
    app.theme = "textual-dark"  # default theme
    assert snap_compare(app, run_before=run_before)


def test_welcome_screen_snapshot(app_factory: Any, snap_compare: Any):
    async def run_before(pilot: Pilot[Any]):
        await pilot.press(*list("arch linux iso"))
        await pilot.pause()

    app = app_factory()
    app.theme = "textual-dark"  # default theme
    assert snap_compare(app, run_before=run_before)


def test_theme_switcher_screen_snapshot(app_factory: Any, snap_compare: Any):
    async def run_before(pilot: Pilot[Any]):
        await pilot.press("ctrl+t")
        await pilot.pause()

    app = app_factory()
    app.theme = "textual-dark"  # default theme
    assert snap_compare(app, run_before=run_before)
