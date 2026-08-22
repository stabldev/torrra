from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static
from typing_extensions import override

from torrra.core.config import get_config
from torrra.utils.helpers import human_readable_size


class StatusBar(Horizontal):
    """Bottom status bar displaying shortcut hints on the left and aggregate stats on the right."""

    def __init__(self, id: str | None = "status_bar") -> None:
        super().__init__(id=id)
        self._shortcuts_widget = Static("? for shortcuts", id="shortcuts")
        self._stats_widget = Static("", id="stats")
        self._last_stats: tuple[float, float, int] = (0.0, 0.0, 0)
        self.update_stats(0.0, 0.0, 0)

    @override
    def compose(self) -> ComposeResult:
        yield self._shortcuts_widget
        yield self._stats_widget

    def update_stats(
        self, download_rate: float, upload_rate: float, dht_nodes: int
    ) -> None:
        self._last_stats = (download_rate, upload_rate, dht_nodes)
        self._refresh_display()

    def _limit_badge(self) -> str:
        # "turtle mode" indicator when global speed limits are active
        config = get_config()
        enabled = bool(config.get("speed_limit.enabled", False))
        if not enabled:
            return ""

        parts: list[str] = []
        for arrow, key in (
            ("↓", "speed_limit.download_limit"),
            ("↑", "speed_limit.upload_limit"),
        ):
            limit = int(config.get(key, 0) or 0)
            if limit > 0:
                parts.append(f"{arrow}{human_readable_size(limit, short=True)}/s")
        label = "TURTLE" + (" " + "·".join(parts) if parts else "")
        return f"[reverse] {label} [/] "

    def _refresh_display(self) -> None:
        download_rate, upload_rate, dht_nodes = self._last_stats
        # fmt: off
        down_speed = f"{human_readable_size(download_rate)}/s" if download_rate > 0 else "0 B/s"
        up_speed = f"{human_readable_size(upload_rate)}/s" if upload_rate > 0 else "0 B/s"
        nodes_str = "1 node" if dht_nodes == 1 else f"{dht_nodes} nodes"
        # fmt: on

        badge = self._limit_badge()
        self._stats_widget.update(
            f"{badge}[b]↓[/b] {down_speed} · [b]↑[/b] {up_speed} · [b]DHT:[/b] {nodes_str}"
        )
