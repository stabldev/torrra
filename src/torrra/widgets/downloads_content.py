from typing import Any, cast

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import ProgressBar, Static
from typing_extensions import override

from torrra.utils.helpers import human_readable_size
from torrra.widgets.data_table import AutoResizingDataTable

MOCK_DOWNLOADS = [
    {
        "title": "The.Big.Bang.Theory.S12E01.HDTV.x264-LOL[ettv]",
        "status": "DL",
        "done_percent": 69,
        "up_speed": "0 B/s",
        "down_speed": "1.2 MB/s",
        "size": 350 * 1024 * 1024,
        "seeders": 12,
        "leechers": 4,
        "source": "ettv",
    },
    {
        "title": "Modern.Family.S10E01.HDTV.x264-SVA[eztv]",
        "status": "SD",
        "done_percent": 100,
        "up_speed": "100 KB/s",
        "down_speed": "0 B/s",
        "size": 200 * 1024 * 1024,
        "seeders": 20,
        "leechers": 1,
        "source": "eztv",
    },
    {
        "title": "Game.of.Thrones.S08E01.1080p.WEB.H264-MEMENTO[rarbg]",
        "status": "CP",
        "done_percent": 100,
        "up_speed": "0 B/s",
        "down_speed": "0 B/s",
        "size": 1500 * 1024 * 1024,
        "seeders": 0,
        "leechers": 0,
        "source": "rarbg",
    },
    {
        "title": "Chernobyl.S01E01.1080p.WEB.H264-METCON[rarbg]",
        "status": "PD",
        "done_percent": 25,
        "up_speed": "0 B/s",
        "down_speed": "0 B/s",
        "size": 2200 * 1024 * 1024,
        "seeders": 5,
        "leechers": 2,
        "source": "rarbg",
    },
]


class DownloadsContent(Vertical):
    COLS: list[tuple[str, str, int]] = [
        ("No", "no_col", 2),
        ("Title", "title", 25),
        ("St", "status", 2),
        ("Done", "done_percent", 4),
        ("Up", "up_speed", 8),
        ("Down", "down_speed", 8),
    ]

    def __init__(self) -> None:
        super().__init__(id="downloads_content")
        # application states
        self._selected_download: dict[str, Any] | None = None
        # ui refs (cached later)
        self._details_container: Container
        self._details_content: Static
        self._details_progress: ProgressBar

    @override
    def compose(self) -> ComposeResult:
        yield AutoResizingDataTable(
            id="downloads_table",
            cursor_type="row",
            show_cursor=True,
        )
        with Container(id="details_container", classes="hidden"):
            yield Static(id="details_content")
            yield ProgressBar(id="details_progress", total=100)

    def on_mount(self) -> None:
        self._details_container = self.query_one("#details_container", Container)
        self._details_content = self.query_one("#details_content", Static)
        self._details_progress = self.query_one("#details_progress", ProgressBar)
        self._details_container.can_focus = True
        self._details_container.border_title = "details"

        table = self.query_one(AutoResizingDataTable[str])
        table.expand_col = "title"
        table.border_title = f"all ({len(MOCK_DOWNLOADS)})"

        for label, key, width in self.COLS:
            table.add_column(label, width=width, key=key)

        for idx, download in enumerate(MOCK_DOWNLOADS):
            table.add_row(
                str(idx + 1),
                download["title"],
                download["status"],
                f"{download['done_percent']}%",
                download["down_speed"],
                download["up_speed"],
                key=download["title"],
            )

    @on(AutoResizingDataTable.RowSelected, "#downloads_table")
    def _handle_select(self, event: AutoResizingDataTable.RowSelected) -> None:
        row_key = cast(str, event.row_key.value)
        self._selected_download = next(
            (d for d in MOCK_DOWNLOADS if d["title"] == row_key), None
        )
        if self._selected_download is None:
            return

        status = self._get_full_status_text(self._selected_download["status"])
        size = human_readable_size(self._selected_download["size"])
        details = f"""
[b]{self._selected_download["title"]}[/b]
[b]Size:[/b] {size} - [b]Seeders:[/b] {self._selected_download["seeders"]} - [b]Leechers:[/b] {self._selected_download["leechers"]} - [b]Source:[/b] {self._selected_download["source"]}
[b]Status:[/b] {status} - [b]Up:[/b] {self._selected_download["up_speed"]} - [b]Down:[/] {self._selected_download["down_speed"]}

[dim]Press 'p' to pause/resume, 'd' to delete.[/dim]
"""
        self._details_content.update(details.strip())
        self._details_progress.progress = self._selected_download["done_percent"]
        self._details_container.remove_class("hidden")
        self._details_container.focus()

    def _get_full_status_text(self, status: str) -> str:
        return {
            "DL": "Download",
            "SD": "Seed",
            "CP": "Completed",
            "PD": "Paused",
        }.get(status, "Unknown")
