from typing import cast

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.timer import Timer
from typing_extensions import override

from torrra._types import TorrentRecord, TorrentStatus
from torrra.core.download import DownloadManager, get_download_manager
from torrra.core.torrent import TorrentManager
from torrra.utils.helpers import human_readable_size
from torrra.widgets.data_table import AutoResizingDataTable
from torrra.widgets.details_panel import DetailsPanel


class DownloadsContent(Vertical):
    COLS: list[tuple[str, str, int]] = [
        ("No", "no_col", 2),
        ("Title", "title", 25),
        ("St.", "status", 3),
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
        self._details_panel: DetailsPanel

    @override
    def compose(self) -> ComposeResult:
        yield AutoResizingDataTable(cursor_type="row")
        yield DetailsPanel()

    def on_mount(self) -> None:
        self._table = self.query_one(AutoResizingDataTable)
        self._table.expand_col = "title"

        self._details_panel = self.query_one(DetailsPanel)
        self._details_panel.border_title = "details"
        # setup table
        for label, key, width in self.COLS:
            self._table.add_column(label, width=width, key=key)
        # start prime torrents download
        self._prime_downloads()

    def on_show(self) -> None:
        tm = TorrentManager()
        self._torrents = tm.get_all_torrents()

        self._table.clear()
        self._table.border_title = f"all ({len(self._torrents)})"

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
        # run timer to update results table
        self._update_timer = self.set_interval(1, self._update_table_data)

    def on_hide(self) -> None:
        if self._update_timer:
            self._update_timer.stop()

    def on_unmount(self) -> None:
        if self._update_timer:
            self._update_timer.stop()

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
        self._details_panel.add_class("hidden")
        self._selected_torrent = None

    def on_details_panel_closed(self):
        self._selected_torrent = None

    def on_data_table_row_selected(
        self, event: AutoResizingDataTable.RowSelected
    ) -> None:
        row_key = cast(str, event.row_key.value)
        self._selected_torrent = next(
            (d for d in self._torrents if d["magnet_uri"] == row_key), None
        )

        if self._selected_torrent and self._selected_torrent["magnet_uri"]:
            if status := self._download_manager.get_torrent_status(
                self._selected_torrent["magnet_uri"]
            ):
                self._update_details_panel(status)
            self._details_panel.remove_class("hidden")
            self._details_panel.focus()
        else:  # selected torrent is invalid
            self._details_panel.add_class("hidden")

    def _prime_downloads(self) -> None:
        tm = TorrentManager()
        torrents = tm.get_all_torrents()
        for torrent in torrents:
            self._download_manager.add_torrent(torrent["magnet_uri"])

    def _update_table_data(self) -> None:
        if not self._torrents:
            return

        for torrent in self._torrents:
            status = self._download_manager.get_torrent_status(torrent["magnet_uri"])
            if not status:
                continue

            self._table.update_cell(
                torrent["magnet_uri"],
                "status",
                self._download_manager.get_torrent_state_text(status, short=True),
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
                # update the details panel if its open and
                # showing this torrent data
                self._update_details_panel(status)

    def _update_details_panel(self, status: TorrentStatus) -> None:
        if not self._selected_torrent:
            return

        state_text = self._download_manager.get_torrent_state_text(status)
        size = human_readable_size(float(self._selected_torrent["size"]))
        up_speed = f"{human_readable_size(status['up_speed'])}/s"
        down_speed = f"{human_readable_size(status['down_speed'])}/s"

        details = f"""
[b]{self._selected_torrent["title"]}[/]
[b]Size:[/] {size} - [b]Status:[/] {state_text} - [b]Source:[/] {self._selected_torrent["source"]}
[b]S/L:[/] {status["seeders"]}/{status["leechers"]} - [b]Up:[/b] {up_speed} - [b]Down:[/] {down_speed}

[dim]Press 'p' to pause/resume, 'd' to delete.[/dim]
"""
        # update details panel internal widgets
        self._details_panel.update(details.strip(), status["progress"])
