from typing import ClassVar, cast

from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import Vertical
from typing_extensions import override

from torrra._types import (
    DownloadSelection,
    Torrent,
    TorrentOptions,
    TorrentRecord,
    TorrentStatus,
)
from torrra.core.download import DownloadManager, get_download_manager
from torrra.core.exceptions import ConfigError, DownloadError
from torrra.core.torrent import TorrentManager, get_torrent_manager
from torrra.screens.file_selection import FileSelectionScreen
from torrra.screens.torrent_options import TorrentOptionsScreen
from torrra.utils.helpers import human_readable_eta, human_readable_size
from torrra.widgets.data_table import AutoResizingDataTable
from torrra.widgets.details_panel import DetailsPanel


class DownloadsContent(Vertical):
    COLS: ClassVar[list[tuple[str, str, int]]] = [
        ("No", "no_col", 2),
        ("Title", "title", 25),
        ("Stat", "status", 4),
        ("Done", "done_percent", 4),
        ("Up", "up_speed", 9),
        ("Down", "down_speed", 10),
    ]

    BINDINGS: ClassVar[list[tuple[str, str]]] = [
        ("d", "delete_torrent"),
        ("D", "delete_torrent_with_data"),
        ("f", "select_files"),
        ("o", "show_torrent_options"),
        ("r", "reannounce_trackers"),
    ]

    def __init__(self) -> None:
        super().__init__(id="downloads_content")
        self._torrents: list[TorrentRecord] = []
        self._selected_torrent: TorrentRecord | None = None
        self._group_filter: str | None = None
        self._statuses: dict[str, TorrentStatus | None] = {}

        self._dm: DownloadManager = get_download_manager()
        self._tm: TorrentManager = get_torrent_manager()

        self._table: AutoResizingDataTable[str]
        self._details_panel: DetailsPanel

    @override
    def compose(self) -> ComposeResult:
        yield AutoResizingDataTable(cursor_type="row")
        yield DetailsPanel(show_progress_bar=True)

    def on_mount(self) -> None:
        self._table = self.query_one(AutoResizingDataTable)
        self._table.expand_col = "title"

        self._details_panel = self.query_one(DetailsPanel)
        # setup table
        for label, key, width in self.COLS:
            self._table.add_column(label, width=width, key=key)

    def on_show(self) -> None:
        self.refresh_torrents()

    def set_group_filter(self, group_type: str | None) -> None:
        if self._group_filter != group_type:
            self._group_filter = group_type
            self._filter_table()

    def _matches_filter(self, status: TorrentStatus | None) -> bool:
        if self._group_filter is None:
            return True
        if not status:
            return False
        state_text = self._dm.get_torrent_state_text(status)
        if self._group_filter == "Downloading":
            return state_text in ("Downloading", "Fetching", "Allocating")
        if self._group_filter == "Stalled":
            return state_text == "Stalled"
        if self._group_filter == "Seeding":
            return state_text == "Seeding"
        if self._group_filter == "Paused":
            return state_text in ("Paused", "Queued")
        if self._group_filter == "Completed":
            return state_text == "Completed"
        if self._group_filter == "Checking":
            return state_text == "Checking"
        if self._group_filter == "Error":
            return state_text in ("Missing Files", "Error")
        return state_text == self._group_filter

    def _filter_table(self) -> None:
        if not hasattr(self, "_table") or not self._table.columns:
            return

        self._table.clear()
        matching_torrents = [
            t
            for t in self._torrents
            if self._matches_filter(self._statuses.get(t["magnet_uri"]))
        ]
        title_prefix = (
            "all" if self._group_filter is None else self._group_filter.lower()
        )
        self._table.border_title = f"{title_prefix} ({len(matching_torrents)})"

        for idx, torrent in enumerate(matching_torrents):
            status = self._statuses.get(torrent["magnet_uri"])
            state_text = (
                self._dm.get_torrent_state_text(status, short=True) if status else "N/A"
            )
            progress_text = f"{int(status['progress'])}%" if status else "0%"
            up_text = (
                f"{human_readable_size(status['up_speed'], short=True)}/s"
                if status
                else "0 B/s"
            )
            down_text = (
                f"{human_readable_size(status['down_speed'], short=True)}/s"
                if status
                else "0 B/s"
            )

            self._table.add_row(
                str(idx + 1),
                torrent["title"],
                state_text,
                progress_text,
                up_text,
                down_text,
                key=torrent["magnet_uri"],
            )

        if self._selected_torrent and self._selected_torrent["magnet_uri"] not in [
            t["magnet_uri"] for t in matching_torrents
        ]:
            self._details_panel.add_class("hidden")
            self._selected_torrent = None

    def refresh_torrents(self) -> None:
        self._torrents = self._tm.get_all_torrents()

        for torrent in self._torrents:
            try:
                self._dm.add_torrent(
                    torrent["magnet_uri"],
                    is_paused=torrent["is_paused"],
                    file_priorities=torrent.get("file_priorities"),
                    upload_limit=torrent.get("upload_limit"),
                    download_limit=torrent.get("download_limit"),
                    save_path=torrent.get("save_path"),
                    create_path=torrent.get("save_path") is None,
                    max_ratio=torrent.get("max_ratio"),
                    max_seeding_time=torrent.get("max_seeding_time"),
                    sequential_download=torrent.get("sequential_download", False),
                )
            except (ConfigError, DownloadError) as exc:
                self.notify(
                    f"Could not restore '{torrent['title']}': {exc}",
                    title="Torrent Restore Failed",
                    severity="error",
                )

        self._filter_table()

    def key_p(self) -> None:
        if not self._selected_torrent:
            return

        magnet_uri = self._selected_torrent["magnet_uri"]

        status = self._dm.get_torrent_status(magnet_uri)
        if not status:
            return

        target_paused = not status["is_paused"]

        self._dm.toggle_pause(magnet_uri)
        self._tm.update_torrent_paused_state(magnet_uri, target_paused)

        if self._selected_torrent:
            self._selected_torrent["is_paused"] = target_paused

    def action_delete_torrent(self) -> None:
        self._remove_selected_torrent()

    def action_delete_torrent_with_data(self) -> None:
        self._remove_selected_torrent(delete_files=True)

    def action_select_files(self) -> None:
        if not self._selected_torrent:
            return

        magnet_uri = self._selected_torrent["magnet_uri"]
        current_priorities = self._dm.get_file_priorities(
            magnet_uri
        ) or self._selected_torrent.get("file_priorities")

        self.app.push_screen(
            FileSelectionScreen(
                torrent=Torrent(
                    magnet_uri=self._selected_torrent["magnet_uri"],
                    title=self._selected_torrent["title"],
                    size=self._selected_torrent["size"],
                    source=self._selected_torrent["source"],
                    seeders=0,
                    leechers=0,
                    file_priorities=current_priorities,
                    save_path=self._selected_torrent.get("save_path"),
                ),
                existing_priorities=current_priorities,
                is_edit_mode=True,
            ),
            self._on_edit_files_done,
        )

    def action_show_torrent_options(self) -> None:
        if not self._selected_torrent:
            return

        magnet_uri = self._selected_torrent["magnet_uri"]
        title = self._selected_torrent["title"]
        short_title = (title[:50] + "...") if len(title) > 40 else title

        opts = self._dm.get_torrent_options(magnet_uri)

        self.app.push_screen(
            TorrentOptionsScreen(
                title=short_title,
                options=opts,
            ),
            self._on_torrent_options_set,
        )

    def _on_torrent_options_set(self, options: TorrentOptions | None) -> None:
        if options is None or not self._selected_torrent:
            return

        magnet_uri = self._selected_torrent["magnet_uri"]
        self._dm.set_torrent_options(magnet_uri, options)

        self._selected_torrent["upload_limit"] = options.upload_limit
        self._selected_torrent["download_limit"] = options.download_limit
        self._selected_torrent["max_ratio"] = options.max_ratio
        self._selected_torrent["max_seeding_time"] = options.max_seeding_time
        self._selected_torrent["sequential_download"] = options.sequential_download

        # refresh the details panel so the new options are visible
        if status := self._dm.get_torrent_status(magnet_uri):
            self._update_details_panel(status)

    def _on_speed_limit_set(self, limits: tuple[int, int] | None) -> None:
        if limits is None or not self._selected_torrent:
            return

        up, down = limits
        magnet_uri = self._selected_torrent["magnet_uri"]
        self._dm.set_torrent_limits(magnet_uri, up, down)

        # refresh the details panel so the new limits are visible
        if status := self._dm.get_torrent_status(magnet_uri):
            self._update_details_panel(status)

    def _on_edit_files_done(self, selection: DownloadSelection | None) -> None:
        if selection is None or not self._selected_torrent:
            return

        magnet_uri = self._selected_torrent["magnet_uri"]
        priorities = selection.file_priorities
        if priorities is None:
            return
        self._selected_torrent["file_priorities"] = priorities

        self._dm.set_file_priorities(magnet_uri, priorities)
        self._tm.update_torrent_file_priorities(magnet_uri, priorities)

    def _remove_selected_torrent(self, delete_files: bool = False) -> None:
        if not self._selected_torrent:
            return

        magnet_uri = self._selected_torrent["magnet_uri"]

        self._dm.remove_torrent(magnet_uri, delete_files=delete_files)
        self._tm.remove_torrent(magnet_uri)

        self._torrents = [t for t in self._torrents if t["magnet_uri"] != magnet_uri]
        self._statuses.pop(magnet_uri, None)
        self._selected_torrent = None
        self._details_panel.add_class("hidden")
        self._filter_table()

    def on_details_panel_closed(self) -> None:
        self._selected_torrent = None

    def on_details_panel_tab_changed(self, event: DetailsPanel.TabChanged) -> None:
        if not self._selected_torrent:
            return
        if status := self._dm.get_torrent_status(self._selected_torrent["magnet_uri"]):
            self._update_details_panel(status)

    def action_reannounce_trackers(self) -> None:
        if not self._selected_torrent:
            return
        magnet_uri = self._selected_torrent["magnet_uri"]
        self._dm.force_reannounce_torrent(magnet_uri)
        self.notify(
            "Sent force reannounce to trackers",
            title="Trackers Reannounced",
        )
        if self._details_panel.active_tab == "tab_trackers":
            trackers = self._dm.get_torrent_trackers(magnet_uri)
            self._details_panel.update_trackers(trackers)

    def on_data_table_row_selected(
        self, event: AutoResizingDataTable.RowSelected
    ) -> None:
        row_key = cast(str, event.row_key.value)
        new_torrent = next(
            (d for d in self._torrents if d["magnet_uri"] == row_key), None
        )
        if self._selected_torrent != new_torrent:
            self._details_panel.clear_tables()
        self._selected_torrent = new_torrent

        if self._selected_torrent:
            self._details_panel.border_title = self._selected_torrent["title"]
            if status := self._dm.get_torrent_status(
                self._selected_torrent["magnet_uri"]
            ):
                self._update_details_panel(status)
            self._details_panel.remove_class("hidden")
            self._details_panel.focus()
        else:  # selected torrent is invalid
            self._details_panel.add_class("hidden")

    def focus_table(self) -> None:
        self._table.focus()

    def update_table_data(self, statuses: dict[str, TorrentStatus | None]) -> None:
        self._statuses = statuses

        # First, update the torrent list from the database to catch new or updated torrents
        updated_torrents = self._tm.get_all_torrents()
        current_uris = [t["magnet_uri"] for t in self._torrents]
        updated_uris = [t["magnet_uri"] for t in updated_torrents]
        if current_uris != updated_uris:
            self.refresh_torrents()
            return

        if not self._torrents:
            return

        torrent_map = {t["magnet_uri"]: t for t in updated_torrents}

        for torrent in self._torrents:
            # Update the local torrent record if it was updated in the database
            if torrent["magnet_uri"] in torrent_map:
                db_torrent = torrent_map[torrent["magnet_uri"]]
                # Update the local record if title or size changed
                if (
                    torrent["title"] != db_torrent["title"]
                    or torrent["size"] != db_torrent["size"]
                ):
                    torrent.update(
                        {"title": db_torrent["title"], "size": db_torrent["size"]}
                    )
                    try:
                        self._table.update_cell(
                            torrent["magnet_uri"], "title", db_torrent["title"]
                        )
                    except KeyError:
                        pass

        # If a filter is active, check if visible row set needs updating
        if self._group_filter is not None:
            matching_uris = [
                t["magnet_uri"]
                for t in self._torrents
                if self._matches_filter(self._statuses.get(t["magnet_uri"]))
            ]
            table_uris = [str(k.value) for k in self._table.rows]
            if matching_uris != table_uris:
                self._filter_table()
                return

        for torrent in self._torrents:
            if not self._matches_filter(statuses.get(torrent["magnet_uri"])):
                continue

            status = statuses.get(torrent["magnet_uri"])
            if not status:
                continue

            try:
                self._table.update_cell(
                    torrent["magnet_uri"],
                    "status",
                    self._dm.get_torrent_state_text(status, short=True),
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
            except KeyError:
                pass

            # check if torrent is already downloaded/notified
            # if not, send notification and update record
            if status["progress"] == 100 and not torrent["is_notified"]:
                title = torrent["title"]
                short_title = (title[:50] + "...") if len(title) > 40 else title
                self.notify(
                    f"Finished downloading [b]{short_title}[/b]",
                    title="Download Finished",
                )
                self._tm.update_torrent_is_notified(torrent["magnet_uri"])
                torrent["is_notified"] = True

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

        # Get the most up-to-date torrent info from the database
        updated_torrents = self._tm.get_all_torrents()
        current_torrent = next(
            (
                t
                for t in updated_torrents
                if t["magnet_uri"] == self._selected_torrent["magnet_uri"]
            ),
            self._selected_torrent,
        )

        state_text = self._dm.get_torrent_state_text(status)
        total_size = float(current_torrent["size"])
        downloaded = status.get("total_done")
        if downloaded is None or downloaded == 0:
            downloaded = (status.get("progress", 0.0) / 100.0) * total_size
        else:
            downloaded = float(downloaded)

        if total_size > 0:
            downloaded = min(downloaded, total_size)

        size = f"{human_readable_size(downloaded)} / {human_readable_size(total_size)}"
        eta_text = human_readable_eta(status["eta"], is_seeding=status["is_seeding"])
        limits = self._dm.get_torrent_limits(self._selected_torrent["magnet_uri"])
        up_limit_suffix = (
            f" [dim][{human_readable_size(limits[0], short=True)}/s][/dim]"
            if limits and limits[0] is not None and limits[0] > 0
            else ""
        )
        down_limit_suffix = (
            f" [dim][{human_readable_size(limits[1], short=True)}/s][/dim]"
            if limits and limits[1] is not None and limits[1] > 0
            else ""
        )
        up_speed = f"{human_readable_size(status['up_speed'])}/s{up_limit_suffix}"
        down_speed = f"{human_readable_size(status['down_speed'])}/s{down_limit_suffix}"

        seeders_text = f"{status.get('seeders', 0)}/{status.get('total_seeders', 0)}"
        peers_text = f"{status.get('peers', 0)}/{status.get('total_peers', 0)}"
        save_path = escape(status["save_path"])

        ratio = status.get("ratio", 0.0)
        max_ratio = status.get("max_ratio")
        ratio_part = (
            f" [dim]·[/dim] Ratio: [b]{ratio:.2f}[/b]/{max_ratio:.2f}"
            if max_ratio is not None and max_ratio > 0
            else ""
        )
        seq_badge = " [dim]\\[Seq][/dim]" if status.get("sequential_download") else ""

        details = (
            f"Status: [b]{state_text}[/b]{seq_badge} [dim]·[/dim] Size: {size}{ratio_part} [dim]·[/dim] [dim]Source:[/dim] [dim]{current_torrent['source']}[/dim]\n"
            f"Down: [b]{down_speed}[/b] [dim]·[/dim] Up: {up_speed} [dim]·[/dim] [dim]Seeds:[/dim] [dim]{seeders_text}[/dim] [dim]·[/dim] [dim]Peers:[/dim] [dim]{peers_text}[/dim]\n"
            f"[dim]Save to:[/dim] [dim]{save_path}[/dim]"
        )
        shortcuts = (
            r"[dim]\[p] pause/resume · \[r] reannounce · "
            r"\[f] files · \[o] options · \[d/D] delete · \[esc] close[/dim]"
        )
        # update details panel internal widgets
        self._details_panel.border_title = current_torrent["title"]
        self._details_panel.update_content(
            details,
            progress=status["progress"],
            eta=eta_text,
            shortcuts=shortcuts,
        )

        active_tab = self._details_panel.active_tab
        magnet_uri = self._selected_torrent["magnet_uri"]
        if active_tab == "tab_peers":
            peers = self._dm.get_torrent_peers(magnet_uri)
            self._details_panel.update_peers(peers)
        elif active_tab == "tab_trackers":
            trackers = self._dm.get_torrent_trackers(magnet_uri)
            self._details_panel.update_trackers(trackers)
        elif active_tab == "tab_files":
            files = self._dm.get_torrent_files_progress(magnet_uri)
            self._details_panel.update_files(files)
