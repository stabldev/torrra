from textual.app import ComposeResult
from textual.containers import Vertical
from typing_extensions import override

from torrra.widgets.data_table import AutoResizingDataTable

MOCK_DOWNLOADS = [
    {
        "title": "The.Big.Bang.Theory.S12E01.HDTV.x264-LOL[ettv]",
        "status": "DL",
        "done_percent": 69,
        "up_speed": "0 B/s",
        "down_speed": "1.2 MB/s",
    },
    {
        "title": "Modern.Family.S10E01.HDTV.x264-SVA[eztv]",
        "status": "SD",
        "done_percent": 100,
        "up_speed": "100 KB/s",
        "down_speed": "0 B/s",
    },
    {
        "title": "Game.of.Thrones.S08E01.1080p.WEB.H264-MEMENTO[rarbg]",
        "status": "CP",
        "done_percent": 100,
        "up_speed": "0 B/s",
        "down_speed": "0 B/s",
    },
    {
        "title": "Chernobyl.S01E01.1080p.WEB.H264-METCON[rarbg]",
        "status": "PD",
        "done_percent": 25,
        "up_speed": "0 B/s",
        "down_speed": "0 B/s",
    },
]


class DownloadsContent(Vertical):
    COLS: list[tuple[str, str, int]] = [
        ("No.", "no_col", 3),
        ("Title", "title", 25),
        ("St", "status", 2),
        ("Done", "done_percent", 4),
        ("Up", "up_speed", 8),
        ("Down", "down_speed", 8),
    ]

    def __init__(self) -> None:
        super().__init__(id="downloads_content")

    @override
    def compose(self) -> ComposeResult:
        yield AutoResizingDataTable(
            id="downloads_table",
            cursor_type="row",
            show_cursor=True,
        )

    def on_mount(self) -> None:
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
