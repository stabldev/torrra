from typing import cast

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.timer import Timer
from textual.widgets import ProgressBar, Static
from typing_extensions import override

from torrra._types import TorrentRecord, TorrentStatus
from torrra.core.download import DownloadManager, get_download_manager
from torrra.core.torrent import TorrentManager
from torrra.utils.helpers import human_readable_size
from torrra.widgets.data_table import AutoResizingDataTable


class DownloadsContent(Vertical):
    COLS: list[tuple[str, str, int]] = [
        ("No", "no_col", 2),
        ("Title", "title", 25),
        ("St.", "status", 4),
        ("Done", "done_percent", 4),
        ("Up", "up_speed", 6),
        ("Down", "down_speed", 6),
    ]

    def __init__(self) -> None:
        super().__init__(id="downloads_content")
        self._torrents: list[TorrentRecord] = []
        self._selected_torrent: TorrentRecord | None = None
        self._download_manager: DownloadManager = get_download_manager()
        self._update_timer: Timer | None = None

        self._table: AutoResizingDataTable[str]
        self._details_container: Container
        self._details_content: Static
        self._details_progress: ProgressBar

    @override
    def compose(self) -> ComposeResult:
        yield AutoResizingDataTable(id="downloads_table", cursor_type="row")
        with Container(id="details_container", classes="hidden"):
            yield Static(id="details_content")
            yield ProgressBar(id="details_progress", total=100, show_eta=True)

    def on_mount(self) -> None:
        self._table = self.query_one(AutoResizingDataTable)
        self._details_container = self.query_one("#details_container", Container)
        self._details_content = self.query_one("#details_content", Static)
        self._details_progress = self.query_one("#details_progress", ProgressBar)
        self._details_container.can_focus = True
        self._details_container.border_title = "details"

        tm = TorrentManager()
        self._torrents = tm.get_all_torrents()

        self._table.expand_col = "title"
        self._table.border_title = f"all ({len(self._torrents)})"

        for label, key, width in self.COLS:
            self._table.add_column(label, width=width, key=key)

        for idx, torrent in enumerate(self._torrents):
            self._download_manager.add_torrent(torrent["magnet_uri"])
            self._table.add_row(
                str(idx + 1),
                torrent["title"],
                "N/A",
                "0%",
                "0 B/s",
                "0 B/s",
                key=torrent["magnet_uri"],
            )
        # trigger update table every second
        self._update_timer = self.set_interval(1, self._update_table_data)

    def on_unmount(self) -> None:
        if self._update_timer:
            self._update_timer.stop()

    def _update_table_data(self) -> None:
        for torrent in self._torrents:
            if status := self._download_manager.get_torrent_status(
                torrent["magnet_uri"]
            ):
                self._table.update_cell(
                    torrent["magnet_uri"],
                    "status",
                    self._download_manager.get_torrent_state_text(
                        status["state"], short=True
                    ),
                )
                self._table.update_cell(
                    torrent["magnet_uri"],
                    "done_percent",
                    f"{int(status['progress'])}%",
                )
                self._table.update_cell(
                    torrent["magnet_uri"],
                    "up_speed",
                    f"{human_readable_size(status['up_speed'], short=True)}/s",
                )
                self._table.update_cell(
                    torrent["magnet_uri"],
                    "down_speed",
                    f"{human_readable_size(status['down_speed'], short=True)}/s",
                )

                if (
                    self._selected_torrent
                    and self._selected_torrent["magnet_uri"] == torrent["magnet_uri"]
                ):
                    # update the details panel if its open and showing this torrent data
                    self._update_details_panel(status)

    def _update_details_panel(self, status: TorrentStatus) -> None:
        if not self._selected_torrent:
            return

        state_text = self._download_manager.get_torrent_state_text(status["state"])
        details = f"""
[b]{self._selected_torrent["title"]}[/]
[b]Size:[/] {human_readable_size(float(self._selected_torrent["size"]))} - [b]Status:[/] {state_text} - [b]Source:[/] {self._selected_torrent["source"]}
[b]S/L:[/] {status["seeders"]}/{status["leechers"]} - [b]Up:[/b] {human_readable_size(status["up_speed"])}/s - [b]Down:[/] {human_readable_size(status["down_speed"])}/s

[dim]Press 'p' to pause/resume, 'd' to delete.[/dim]
"""
        self._details_content.update(details.strip())
        self._details_progress.progress = status["progress"]

    @on(AutoResizingDataTable.RowSelected, "#downloads_table")
    def _handle_select(self, event: AutoResizingDataTable.RowSelected) -> None:
        row_key = cast(str, event.row_key.value)
        self._selected_torrent = next(
            (d for d in self._torrents if d["magnet_uri"] == row_key), None
        )

        if self._selected_torrent and self._selected_torrent["magnet_uri"]:
            if status := self._download_manager.get_torrent_status(
                self._selected_torrent["magnet_uri"]
            ):
                self._update_details_panel(status)
            self._details_container.remove_class("hidden")
            self._details_container.focus()
        else:  # selected torrent is invalid
            self._details_container.add_class("hidden")

    def key_p(self) -> None:
        if self._selected_torrent:
            self._download_manager.pause_or_resume(self._selected_torrent["magnet_uri"])

    def key_d(self) -> None:
        if not self._selected_torrent:
            return

        magnet_uri = self._selected_torrent["magnet_uri"]
        self._download_manager.remove_torrent(magnet_uri)

        tm = TorrentManager()
        tm.remove_torrent(magnet_uri)

        self._table.remove_row(magnet_uri)
        self._torrents = [t for t in self._torrents if t["magnet_uri"] != magnet_uri]
        self._table.border_title = f"all ({len(self._torrents)})"
        self._details_container.add_class("hidden")
        self._selected_torrent = None
