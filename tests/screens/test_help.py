from typing import Any

import pytest
from textual.containers import VerticalScroll
from textual.widgets import Input

from torrra.app import TorrraApp
from torrra.screens.help import SHORTCUTS, HelpScreen


@pytest.fixture
def app(app_factory: Any) -> TorrraApp:
    return app_factory()


async def test_help_opens_with_question_mark_and_closes_with_escape(app: TorrraApp):
    async with app.run_test() as pilot:
        app.screen.set_focus(None)

        await pilot.press("question_mark")
        assert isinstance(app.screen, HelpScreen)
        assert len(app.screen_stack) == 3  # default + welcome + help

        await pilot.press("escape")
        assert len(app.screen_stack) == 2  # default + welcome screen


@pytest.mark.parametrize("key", ["question_mark", "q"])
async def test_help_closes_with_its_other_keys(app: TorrraApp, key: str):
    async with app.run_test() as pilot:
        app.screen.set_focus(None)

        await pilot.press("question_mark")
        assert isinstance(app.screen, HelpScreen)

        await pilot.press(key)
        assert not isinstance(app.screen, HelpScreen)


async def test_help_does_not_stack_duplicate_screens(app: TorrraApp):
    async with app.run_test() as pilot:
        app.screen.set_focus(None)

        await pilot.press("question_mark")
        depth = len(app.screen_stack)

        # the binding stays active while help is open, so a second press must
        # close it rather than push another copy
        await pilot.press("question_mark")
        assert len(app.screen_stack) < depth


async def test_question_mark_types_into_a_search_box_instead_of_opening_help(
    app: TorrraApp,
):
    """The binding has priority, so it must step aside while a query is typed."""
    async with app.run_test() as pilot:
        search_input = app.screen.query_one(Input)
        search_input.focus()
        await pilot.pause()

        await pilot.press("question_mark")

        assert not isinstance(app.screen, HelpScreen)
        assert search_input.value == "?"


async def test_help_lists_every_documented_shortcut(app: TorrraApp):
    async with app.run_test() as pilot:
        app.screen.set_focus(None)
        await pilot.press("question_mark")
        assert isinstance(app.screen, HelpScreen)

        rendered = " ".join(
            str(widget.render()) for widget in app.screen.query(".help-row")
        )
        section_titles = " ".join(
            str(widget.render()) for widget in app.screen.query(".help-section")
        )
        for title, shortcuts in SHORTCUTS:
            assert title in section_titles
            for keys, description in shortcuts:
                assert keys in rendered
                assert description in rendered


@pytest.mark.parametrize(
    ("keys", "expected"),
    [
        (["j"], "one line down"),
        (["j", "j", "k"], "one line down"),
        (["down"], "one line down"),
        (["G"], "bottom"),
        (["ctrl+d"], "page down"),
        (["G", "g", "g"], "top"),
        (["G", "ctrl+u"], "page up from bottom"),
    ],
)
async def test_help_scrolls_with_the_same_keys_as_the_rest_of_the_app(
    app: TorrraApp, keys: list[str], expected: str
):
    """The list outgrows a short terminal, and it only gets longer as bindings
    are added, so arrows alone are not enough."""
    async with app.run_test(size=(90, 20)) as pilot:
        app.screen.set_focus(None)
        await pilot.press("question_mark")
        assert isinstance(app.screen, HelpScreen)

        container = app.screen.query_one("#help-container", VerticalScroll)
        bottom = container.max_scroll_y
        assert bottom > 0, "expected the panel to overflow this size"

        await pilot.press(*keys)
        # the target is set synchronously; the position itself animates.
        # asserted relative to the container rather than against fixed offsets
        # so that adding a shortcut doesn't break this
        actual = container.scroll_target_y
        if expected == "one line down":
            assert actual == 1
        elif expected == "top":
            assert actual == 0
        elif expected == "bottom":
            assert actual == bottom
        elif expected == "page down":
            assert 1 < actual <= bottom
        else:  # page up from bottom
            assert 0 <= actual < bottom
