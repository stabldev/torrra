import threading
from typing import TypedDict

import libtorrent as lt

from torrra.core.config import config

_instance = None
_lock = threading.Lock()


def get_download_manager() -> "DownloadManager":
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = DownloadManager()
    return _instance


class TorrentStatus(TypedDict):
    state: lt.torrent_status.states
    progress: float
    down_speed: float
    up_speed: float
    seeders: int
    leechers: int


class DownloadManager:
    _STATE_MAP: dict[lt.torrent_status.states, tuple[str, str]] = {
        lt.torrent_status.states.downloading: ("Downloading", "DL"),
        lt.torrent_status.states.seeding: ("Seeding", "SEED"),
        lt.torrent_status.states.finished: ("Completed", "DONE"),
        lt.torrent_status.states.downloading_metadata: ("Fetching", "META"),
    }

    def __init__(self) -> None:
        self.session: lt.session = lt.session({"listen_interfaces": "0.0.0.0:6881"})
        self.torrents: dict[str, lt.torrent_handle] = {}

    def add_torrent(self, magnet_uri: str) -> None:
        if magnet_uri in self.torrents:
            return

        self.torrents[magnet_uri] = lt.add_magnet_uri(
            self.session, magnet_uri, {"save_path": config.get("general.download_path")}
        )

    def get_torrent_status(self, magnet_uri: str) -> TorrentStatus | None:
        handle = self.torrents.get(magnet_uri)
        if not handle or not handle.is_valid():
            return None

        s = handle.status()
        return TorrentStatus(
            state=s.state,
            progress=s.progress * 100,
            down_speed=s.download_rate,
            up_speed=s.upload_rate,
            seeders=s.num_seeds,
            leechers=s.num_peers,
        )

    def get_torrent_state_text(
        self, state: lt.torrent_status.states, short: bool = False
    ) -> str:
        idx = 1 if short else 0
        return self._STATE_MAP.get(state, "N/A")[idx]
