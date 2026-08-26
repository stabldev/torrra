import time
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical, VerticalScroll
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
            ("t", "toggle turtle mode"),
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
            ("f", "select files to download"),
            ("o / s", "torrent options (limits, ratio, sequential)"),
            ("d", "remove torrent"),
            ("D", "remove and delete files"),
        ],
    ),
    (
        "File selection",
        [
            ("space", "toggle file / folder selection"),
            ("left / right", "collapse / expand folder"),
            ("j / k", "move up or down"),
            ("a", "select all files"),
            ("n", "select no files"),
            ("i", "invert file selection"),
            ("enter", "confirm and download"),
            ("d", "download all (skip wait)"),
            ("esc", "cancel"),
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


class HelpContent(VerticalScroll):
    """Scrollable container for help shortcuts with hidden scrollbar."""

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        super().watch_scroll_y(old_value, new_value)
        if isinstance(self.screen, HelpScreen):
            self.screen.update_remaining(new_value)


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
        self._container: HelpContent
        self._remaining_label: Static
        self._row_positions: list[int] | None = None
        self._last_g_press: float = 0

    @override
    def compose(self) -> ComposeResult:
        with Vertical(id="help-container"):
            yield Label("[b]Keyboard Shortcuts[/b]")
            yield Label("j/k: scroll - esc: close", classes="help-subtitle")
            with HelpContent(id="help-content"):
                for title, shortcuts in SHORTCUTS:
                    with Vertical(classes="help-group"):
                        yield Static(f"[b]{title}[/b]", classes="help-section")
                        for keys, description in shortcuts:
                            yield Static(
                                f"[$accent]{keys:<12}[/$accent] {description}",
                                classes="help-row",
                            )
            yield Static("", id="help-remaining", classes="hidden")

    def on_mount(self) -> None:
        self._container = self.query_one("#help-content", HelpContent)
        self._container.show_vertical_scrollbar = False
        self._remaining_label = self.query_one("#help-remaining", Static)
        self.call_after_refresh(self.update_remaining)

    def on_resize(self) -> None:
        self._row_positions = None
        self.call_after_refresh(self.update_remaining)

    def update_remaining(self, scroll_y: float | None = None) -> None:
        if not hasattr(self, "_container") or not hasattr(self, "_remaining_label"):
            return

        current_scroll = self._container.scroll_y if scroll_y is None else scroll_y
        visible_height = self._container.size.height
        if visible_height <= 0:
            return

        visible_end = current_scroll + visible_height

        if self._row_positions is None:
            groups = list(self.query(".help-group"))
            positions: list[int] = []
            for g in groups:
                gy = g.virtual_region.y
                for r in g.query(".help-row"):
                    positions.append(gy + r.virtual_region.y)
            self._row_positions = positions

        if not self._row_positions:
            return

        below_count = sum(1 for y in self._row_positions if y + 1 > visible_end)
        if below_count > 0:
            self._remaining_label.update(f"({below_count} more)")
            self._remaining_label.remove_class("hidden")
        else:
            self._remaining_label.update("")
            self._remaining_label.add_class("hidden")

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
