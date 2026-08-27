from textual.app import App, ComposeResult
from textual.widgets import ProgressBar, Static

from torrra.widgets.details_panel import DetailsPanel


class DetailsPanelTestApp(App[None]):
    def __init__(self, show_progress_bar: bool = False) -> None:
        super().__init__()
        self.show_progress_bar = show_progress_bar

    def compose(self) -> ComposeResult:
        yield DetailsPanel(show_progress_bar=self.show_progress_bar)


async def test_details_panel_without_progress_bar():
    app = DetailsPanelTestApp(show_progress_bar=False)
    async with app.run_test() as pilot:
        panel = app.query_one(DetailsPanel)
        assert panel.has_class("hidden")
        assert len(panel.query(ProgressBar)) == 0
        assert len(panel.query("#details_eta")) == 0

        panel.update_content("Test info")
        content = panel.query_one("#details_content", Static)
        assert "Test info" in str(content.content)

        # escape closes the panel
        panel.remove_class("hidden")
        panel.focus()
        await pilot.press("escape")
        assert panel.has_class("hidden")


async def test_details_panel_with_progress_bar_and_eta():
    app = DetailsPanelTestApp(show_progress_bar=True)
    async with app.run_test():
        panel = app.query_one(DetailsPanel)
        assert len(panel.query(ProgressBar)) == 1
        assert len(panel.query("#details_eta")) == 1
        assert len(panel.query("#details_shortcuts")) == 1

        panel.update_content(
            "Torrent Details",
            progress=65.5,
            eta="12m 30s",
            shortcuts="[p] pause · [d] delete",
        )
        content = panel.query_one("#details_content", Static)
        progress_bar = panel.query_one(ProgressBar)
        eta_widget = panel.query_one("#details_eta", Static)
        shortcuts_widget = panel.query_one("#details_shortcuts", Static)

        assert "Torrent Details" in str(content.content)
        assert progress_bar.progress == 65.5
        assert "ETA:" in str(eta_widget.content)
        assert "12m 30s" in str(eta_widget.content)
        assert "[p] pause · [d] delete" in str(shortcuts_widget.content)


async def test_details_panel_tabs_and_data_tables():
    from textual.widgets import DataTable

    from torrra._types import PeerInfo, TorrentFileProgress, TrackerInfo

    app = DetailsPanelTestApp(show_progress_bar=True)
    async with app.run_test() as pilot:
        panel = app.query_one(DetailsPanel)
        assert panel.is_tabbed is True
        assert panel.active_tab == "tab_general"

        # Tab navigation via Right arrow
        panel.focus()
        await pilot.press("right")
        assert panel.active_tab == "tab_peers"
        await pilot.press("right")
        assert panel.active_tab == "tab_trackers"
        await pilot.press("right")
        assert panel.active_tab == "tab_files"
        await pilot.press("right")
        assert panel.active_tab == "tab_general"

        # Tab navigation via Left arrow
        await pilot.press("left")
        assert panel.active_tab == "tab_files"
        await pilot.press("left")
        assert panel.active_tab == "tab_trackers"

        # Test peers table update
        peers_table = panel.query_one("#peers_table", DataTable)
        panel.update_peers([])
        assert len(peers_table.rows) == 1

        panel.update_peers(
            [
                PeerInfo(
                    ip="1.2.3.4:5678",
                    client="Transmission/4.0",
                    down_speed=1024.0 * 1024.0,
                    up_speed=512.0 * 1024.0,
                    progress=80.0,
                    flags="IO",
                )
            ]
        )
        assert len(peers_table.rows) == 1

        # Test trackers table update
        trackers_table = panel.query_one("#trackers_table", DataTable)
        panel.update_trackers([])
        assert len(trackers_table.rows) == 1

        panel.update_trackers(
            [
                TrackerInfo(
                    url="udp://tracker.openbittorrent.com:80",
                    tier=0,
                    status="Working",
                    seeds=120,
                    peers=45,
                    message="",
                )
            ]
        )
        assert len(trackers_table.rows) == 1

        # Test files table update
        files_table = panel.query_one("#files_table", DataTable)
        panel.update_files(None)
        assert len(files_table.rows) == 1

        panel.update_files([])
        assert len(files_table.rows) == 1

        panel.update_files(
            [
                TorrentFileProgress(
                    index=0,
                    path="sample.mkv",
                    size=1048576,
                    done=524288,
                    progress=50.0,
                    priority=1,
                    priority_label="Normal",
                )
            ]
        )
        assert len(files_table.rows) == 1

        # Up/Down row navigation on active table
        await pilot.press("down")
        await pilot.press("up")

        # Escape closes panel
        await pilot.press("escape")
        assert panel.has_class("hidden")


async def test_details_panel_in_place_updates_and_scroll_retention():
    from textual.widgets import DataTable, TabbedContent

    from torrra._types import PeerInfo

    app = DetailsPanelTestApp(show_progress_bar=True)
    async with app.run_test() as pilot:
        panel = app.query_one(DetailsPanel)
        panel.remove_class("hidden")
        tc = panel.query_one(TabbedContent)
        tc.active = "tab_peers"
        await pilot.pause()

        peers_table = panel.query_one("#peers_table", DataTable)
        peers_table.styles.height = 10

        # Generate 20 peers
        initial_peers = [
            PeerInfo(
                ip=f"10.0.0.{i}:6881",
                client=f"Client/{i}",
                down_speed=1000.0 * i,
                up_speed=500.0 * i,
                progress=float(i * 4),
                flags="I",
            )
            for i in range(20)
        ]
        panel.update_peers(initial_peers)
        assert len(peers_table.rows) == 20
        await pilot.pause()

        # Scroll down in the table
        peers_table.scroll_to(y=5, animate=False)
        await pilot.pause()
        assert peers_table.scroll_y == 5

        # Update peers in-place (same peer list, updated speeds/progress)
        updated_peers = [
            PeerInfo(
                ip=f"10.0.0.{i}:6881",
                client=f"Client/{i}",
                down_speed=2000.0 * i,
                up_speed=1000.0 * i,
                progress=float(i * 4 + 1),
                flags="IO",
            )
            for i in range(20)
        ]
        panel.update_peers(updated_peers)
        await pilot.pause()

        # Row count unchanged and scroll offset retained!
        assert len(peers_table.rows) == 20
        assert peers_table.scroll_y == 5

        # Remove peer 0, add new peer 99
        updated_peers = updated_peers[1:] + [
            PeerInfo(
                ip="10.0.0.99:6881",
                client="Client/99",
                down_speed=5000.0,
                up_speed=1000.0,
                progress=99.0,
                flags="IO",
            )
        ]
        panel.update_peers(updated_peers)
        await pilot.pause()

        assert len(peers_table.rows) == 20
        assert "10.0.0.99:6881" in peers_table.rows
        assert "10.0.0.0:6881" not in peers_table.rows
        assert peers_table.scroll_y == 5

        # Clear tables
        panel.clear_tables()
        assert len(peers_table.rows) == 0
