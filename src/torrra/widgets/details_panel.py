from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import DataTable, ProgressBar, Static, TabbedContent, TabPane
from typing_extensions import override

from torrra._types import PeerInfo, TorrentFileProgress, TrackerInfo
from torrra.utils.helpers import human_readable_size


class DetailsPanel(Vertical):
    class Closed(Message):
        """Posted when the panel is closed."""

    class TabChanged(Message):
        """Posted when the active tab is changed."""

        def __init__(self, tab_id: str) -> None:
            super().__init__()
            self.tab_id = tab_id

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("left", "previous_tab", "Previous Tab", priority=True),
        Binding("right", "next_tab", "Next Tab", priority=True),
        Binding("escape", "close_panel", "Close Panel", priority=True),
    ]

    PEER_COLS: ClassVar[list[tuple[str, str, int]]] = [
        ("IP:Port", "ip", 22),
        ("Client", "client", 20),
        ("Down", "down_speed", 10),
        ("Up", "up_speed", 10),
        ("Done", "done_percent", 6),
        ("Flags", "flags", 8),
    ]

    TRACKER_COLS: ClassVar[list[tuple[str, str, int]]] = [
        ("Tier", "tier", 5),
        ("URL", "url", 35),
        ("Status", "status", 14),
        ("Seeds", "seeds", 7),
        ("Peers", "peers", 7),
        ("Message", "message", 20),
    ]

    FILE_COLS: ClassVar[list[tuple[str, str, int]]] = [
        ("Path", "path", 35),
        ("Size", "size", 10),
        ("Done", "done", 6),
        ("Priority", "priority", 10),
    ]

    TAB_IDS: ClassVar[list[str]] = [
        "tab_general",
        "tab_peers",
        "tab_trackers",
        "tab_files",
    ]

    def __init__(
        self,
        show_progress_bar: bool = False,
        enable_tabs: bool | None = None,
    ) -> None:
        self.show_progress_bar: bool = show_progress_bar
        self.is_tabbed: bool = show_progress_bar if enable_tabs is None else enable_tabs
        super().__init__(classes="hidden tabbed" if self.is_tabbed else "hidden")

        # UI refs
        self._content_widget: Static
        self._progress_bar: ProgressBar | None = None
        self._eta_widget: Static | None = None
        self._shortcuts_widget: Static
        self._tabs: TabbedContent | None = None
        self._peers_table: DataTable[str] | None = None
        self._trackers_table: DataTable[str] | None = None
        self._files_table: DataTable[str] | None = None

    @override
    def compose(self) -> ComposeResult:
        if self.is_tabbed:
            with TabbedContent(id="details_tabs"):
                with TabPane("General", id="tab_general"):
                    yield Static(id="details_content")
                    if self.show_progress_bar:
                        with Horizontal(id="details_progress_row"):
                            yield ProgressBar(total=100, show_eta=False)
                            yield Static(id="details_eta")
                with TabPane("Peers", id="tab_peers"):
                    yield DataTable[str](id="peers_table", cursor_type="none")
                with TabPane("Trackers", id="tab_trackers"):
                    yield DataTable[str](id="trackers_table", cursor_type="none")
                with TabPane("Files", id="tab_files"):
                    yield DataTable[str](id="files_table", cursor_type="none")
        else:
            yield Static(id="details_content")
            if self.show_progress_bar:
                with Horizontal(id="details_progress_row"):
                    yield ProgressBar(total=100, show_eta=False)
                    yield Static(id="details_eta")

        yield Static(id="details_shortcuts")

    def on_mount(self) -> None:
        self._content_widget = self.query_one("#details_content", Static)
        if self.show_progress_bar:
            self._progress_bar = self.query_one(ProgressBar)
            self._eta_widget = self.query_one("#details_eta", Static)
        self._shortcuts_widget = self.query_one("#details_shortcuts", Static)

        if self.is_tabbed:
            self._tabs = self.query_one(TabbedContent)
            from textual.widgets import Tabs

            try:
                content_tabs = self._tabs.query_one(Tabs)
                content_tabs.can_focus = False
                content_tabs._highlight_active = lambda animate=False: (
                    Tabs._highlight_active(content_tabs, animate=False)
                )
            except Exception:
                pass

            self._peers_table = self.query_one("#peers_table", DataTable)
            self._peers_table.can_focus = False
            self._peers_table.show_cursor = False
            for label, key, width in self.PEER_COLS:
                self._peers_table.add_column(label, width=width, key=key)

            self._trackers_table = self.query_one("#trackers_table", DataTable)
            self._trackers_table.can_focus = False
            self._trackers_table.show_cursor = False
            for label, key, width in self.TRACKER_COLS:
                self._trackers_table.add_column(label, width=width, key=key)

            self._files_table = self.query_one("#files_table", DataTable)
            self._files_table.can_focus = False
            self._files_table.show_cursor = False
            for label, key, width in self.FILE_COLS:
                self._files_table.add_column(label, width=width, key=key)

        # enable focus for this widget
        self.can_focus = True

    @property
    def active_tab(self) -> str:
        if self.is_tabbed and self._tabs:
            return str(self._tabs.active)
        return "tab_general"

    def _get_active_table(self) -> DataTable[str] | None:
        if not self.is_tabbed:
            return None
        active = self.active_tab
        if active == "tab_peers":
            return self._peers_table
        if active == "tab_trackers":
            return self._trackers_table
        if active == "tab_files":
            return self._files_table
        return None

    def action_next_tab(self) -> None:
        if not self.is_tabbed or not self._tabs:
            return
        if self._tabs.active in self.TAB_IDS:
            idx = self.TAB_IDS.index(self._tabs.active)
            new_tab = self.TAB_IDS[(idx + 1) % len(self.TAB_IDS)]
            self._tabs.active = new_tab
            self.post_message(self.TabChanged(new_tab))

    def action_previous_tab(self) -> None:
        if not self.is_tabbed or not self._tabs:
            return
        if self._tabs.active in self.TAB_IDS:
            idx = self.TAB_IDS.index(self._tabs.active)
            new_tab = self.TAB_IDS[(idx - 1) % len(self.TAB_IDS)]
            self._tabs.active = new_tab
            self.post_message(self.TabChanged(new_tab))

    def on_tabbed_content_tab_activated(
        self, event: TabbedContent.TabActivated
    ) -> None:
        self.post_message(self.TabChanged(str(event.pane.id)))

    def key_up(self) -> None:
        table = self._get_active_table()
        if table:
            table.scroll_relative(y=-1, animate=False)

    def key_down(self) -> None:
        table = self._get_active_table()
        if table:
            table.scroll_relative(y=1, animate=False)

    def key_k(self) -> None:
        self.key_up()

    def key_j(self) -> None:
        self.key_down()

    def action_close_panel(self) -> None:
        self.add_class("hidden")
        self.post_message(self.Closed())

    def key_escape(self) -> None:
        self.action_close_panel()

    def update_content(
        self,
        content: str,
        progress: float | None = None,
        eta: str | None = None,
        shortcuts: str | None = None,
    ) -> None:
        self._content_widget.update(content)
        if self._progress_bar and progress is not None:
            self._progress_bar.progress = progress
        if self._eta_widget and eta is not None:
            self._eta_widget.update(f"ETA: [b]{eta}[/b]" if eta else "")
        if shortcuts is not None:
            self._shortcuts_widget.update(shortcuts)

    def update_peers(self, peers: list[PeerInfo]) -> None:
        if not self._peers_table:
            return
        self._peers_table.clear()
        if not peers:
            self._peers_table.add_row(
                "[dim]No connected peers[/dim]",
                "[dim]-[/dim]",
                "[dim]-[/dim]",
                "[dim]-[/dim]",
                "[dim]-[/dim]",
                "[dim]-[/dim]",
            )
            return
        for p in peers:
            down_speed = p.get("down_speed", 0.0)
            up_speed = p.get("up_speed", 0.0)
            down_str = f"{human_readable_size(down_speed, short=True)}/s"
            up_str = f"{human_readable_size(up_speed, short=True)}/s"
            down = f"[b]{down_str}[/b]" if down_speed > 0 else f"[dim]{down_str}[/dim]"
            up = f"{up_str}" if up_speed > 0 else f"[dim]{up_str}[/dim]"
            done = f"[b]{int(p.get('progress', 0.0))}%[/b]"
            self._peers_table.add_row(
                f"[dim]{p.get('ip', '0.0.0.0')}[/dim]",
                p.get("client", "Unknown"),
                down,
                up,
                done,
                f"[dim]{p.get('flags', '-')}[/dim]",
            )

    def update_trackers(self, trackers: list[TrackerInfo]) -> None:
        if not self._trackers_table:
            return
        self._trackers_table.clear()
        if not trackers:
            self._trackers_table.add_row(
                "[dim]-[/dim]",
                "[dim]No trackers found (DHT / PeX only)[/dim]",
                "[dim]-[/dim]",
                "[dim]-[/dim]",
                "[dim]-[/dim]",
                "[dim]-[/dim]",
            )
            return
        for t in trackers:
            status_raw = t.get("status", "Unknown")
            if status_raw == "Working":
                status = "[green]Working[/green]"
            elif status_raw == "Updating":
                status = "[yellow]Updating[/yellow]"
            elif status_raw == "Error":
                status = "[red]Error[/red]"
            else:
                status = f"[dim]{status_raw}[/dim]"

            seeds_count = t.get("seeds", 0)
            seeds = (
                f"[b]{seeds_count}[/b]"
                if seeds_count > 0
                else f"[dim]{seeds_count}[/dim]"
            )
            peers_count = t.get("peers", 0)
            peers = f"{peers_count}" if peers_count > 0 else f"[dim]{peers_count}[/dim]"

            self._trackers_table.add_row(
                f"[dim]{t.get('tier', 0)}[/dim]",
                t.get("url", ""),
                status,
                seeds,
                peers,
                f"[dim]{t.get('message', '')}[/dim]",
            )

    def update_files(self, files: list[TorrentFileProgress] | None) -> None:
        if not self._files_table:
            return
        self._files_table.clear()
        if files is None:
            self._files_table.add_row(
                "[dim]Fetching torrent metadata...[/dim]",
                "[dim]-[/dim]",
                "[dim]-[/dim]",
                "[dim]-[/dim]",
            )
            return
        if not files:
            self._files_table.add_row(
                "[dim]No files found[/dim]",
                "[dim]-[/dim]",
                "[dim]-[/dim]",
                "[dim]-[/dim]",
            )
            return
        for f in files:
            prio_label = f.get("priority_label", "Normal")
            if prio_label == "High":
                prio = "[b]High[/b]"
            elif prio_label == "Skipped":
                prio = "[dim]Skipped[/dim]"
            else:
                prio = "[dim]Normal[/dim]"

            progress_val = int(f.get("progress", 0.0))
            done = (
                f"[b]{progress_val}%[/b]" if progress_val == 100 else f"{progress_val}%"
            )

            self._files_table.add_row(
                f.get("path", ""),
                f"[dim]{human_readable_size(f.get('size', 0))}[/dim]",
                done,
                prio,
            )
