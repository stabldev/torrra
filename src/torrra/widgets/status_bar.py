from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static
from typing_extensions import override

from torrra.utils.helpers import human_readable_size


class StatusBar(Horizontal):
    """Bottom status bar displaying shortcut hints on the left and aggregate stats on the right."""

    def __init__(self, id: str | None = "status_bar") -> None:
        super().__init__(id=id)
        self._shortcuts_widget = Static("? for shortcuts", id="shortcuts")
        self._stats_widget = Static("", id="stats")
        self.update_stats(0.0, 0.0, 0)

    @override
    def compose(self) -> ComposeResult:
        yield self._shortcuts_widget
        yield self._stats_widget

    def update_stats(
        self, download_rate: float, upload_rate: float, dht_nodes: int
    ) -> None:
        # fmt: off
        down_speed = f"{human_readable_size(download_rate)}/s" if download_rate > 0 else "0 B/s"
        up_speed = f"{human_readable_size(upload_rate)}/s" if upload_rate > 0 else "0 B/s"
        nodes_str = "1 node" if dht_nodes == 1 else f"{dht_nodes} nodes"
        # fmt: on

        self._stats_widget.update(
            f"[b]↓[/b] {down_speed} · [b]↑[/b] {up_speed} · [b]DHT:[/b] {nodes_str}"
        )
