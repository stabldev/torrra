import time
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label, Static
from typing_extensions import override

# (section title, [(keys, description), ...])
#
# Kept as data rather than markup so the sections stay readable next to the
# BINDINGS they document. Grouped by where a key applies, using the same
# sections as docs/usage.md, because most of these only do something in one
# of the two views.
SHORTCUTS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Anywhere",
        [
            ("tab", "move focus"),
            ("ctrl+t", "change theme"),
            ("?", "show this help"),
            ("ctrl+q", "quit torrra"),
        ],
    ),
    (
        "Lists",
        [
            ("j / down", "move down"),
            ("k / up", "move up"),
            ("ctrl+d", "page down"),
            ("ctrl+u", "page up"),
            ("gg", "jump to top"),
            ("G", "jump to bottom"),
        ],
    ),
    (
        "Search results",
        [
            ("enter / l", "show torrent details"),
            ("enter", "download (in details)"),
            ("esc", "close details"),
            ("s", "open the sort menu"),
            ("S", "reverse sort order"),
            ("f", "toggle hiding 0 seeders"),
            ("x", "reset to your defaults"),
        ],
    ),
    (
        "Downloads",
        [
            ("enter / l", "show download details"),
            ("p", "pause or resume"),
            ("d", "remove torrent"),
            ("D", "remove and delete files"),
        ],
    ),
    (
        "Menus",
        [
            ("j / k", "move up or down"),
            ("enter", "apply and close"),
            ("esc", "cancel"),
        ],
    ),
]


class HelpScreen(ModalScreen[None]):
    """List every keyboard shortcut, grouped by where it applies."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "close_screen"),
        Binding("question_mark", "close_screen"),
        Binding("q", "close_screen"),
        Binding("j", "scroll_down"),
        Binding("k", "scroll_up"),
        Binding("G", "scroll_bottom"),
        Binding("ctrl+d", "page_down"),
        Binding("ctrl+u", "page_up"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._container: VerticalScroll
        self._last_g_press: float = 0

    @override
    def compose(self) -> ComposeResult:
        with VerticalScroll(id="help-container"):
            yield Label("[b]Keyboard Shortcuts[/b]")
            yield Label("j/k: scroll - esc: close", classes="help-subtext")
            for title, shortcuts in SHORTCUTS:
                yield Static(f"[b]{title}[/b]", classes="help-section")
                for keys, description in shortcuts:
                    yield Static(
                        f"[$accent]{keys:<12}[/$accent] {description}",
                        classes="help-row",
                    )

    def on_mount(self) -> None:
        self._container = self.query_one("#help-container", VerticalScroll)

    # this list only grows as bindings are added, and it already overflows on a
    # short terminal, so the panel scrolls with the same keys the rest of the
    # app uses instead of arrows only
    def key_g(self) -> None:
        current_time = time.time()
        if current_time - self._last_g_press < 0.4:
            self._container.action_scroll_home()
            self._last_g_press = 0
        else:  # save for next event
            self._last_g_press = current_time

    def action_scroll_down(self) -> None:
        self._container.action_scroll_down()

    def action_scroll_up(self) -> None:
        self._container.action_scroll_up()

    def action_scroll_bottom(self) -> None:
        self._container.action_scroll_end()

    def action_page_down(self) -> None:
        self._container.action_page_down()

    def action_page_up(self) -> None:
        self._container.action_page_up()

    def action_close_screen(self) -> None:
        self.app.pop_screen()
