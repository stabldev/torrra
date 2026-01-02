from functools import lru_cache

import libtorrent as lt

from torrra._types import TorrentStatus
from torrra.core.config import get_config


@lru_cache
def get_download_manager() -> "DownloadManager":
    return DownloadManager()


class DownloadManager:
    _STATE_MAP: dict[lt.torrent_status.states, tuple[str, str]] = {
        lt.torrent_status.states.downloading: ("Downloading", "DL"),
        lt.torrent_status.states.seeding: ("Seeding", "SE"),
        lt.torrent_status.states.finished: ("Completed", "CD"),
        lt.torrent_status.states.downloading_metadata: ("Fetching", "FE"),
    }

    def __init__(self) -> None:
        self.session: lt.session = lt.session({"listen_interfaces": "0.0.0.0:6881"})
        self.torrents: dict[str, lt.torrent_handle] = {}
        self._metadata_updated: set[str] = (
            set()
        )  # Track torrents whose metadata has been updated

    def add_torrent(self, magnet_uri: str, is_paused: bool = False) -> None:
        if magnet_uri in self.torrents:
            # Torrent already exists, update paused state if needed
            handle = self.torrents[magnet_uri]
            if not handle.is_valid():
                # If handle is invalid, remove it and add the torrent fresh
                del self.torrents[magnet_uri]
            else:
                # Check current paused state and update if different
                current_status = handle.status()
                is_currently_paused = (
                    current_status.flags & lt.torrent_flags.paused
                ) != 0
                if is_currently_paused != is_paused:
                    handle.pause() if is_paused else handle.resume()
                return

        # Parse the magnet URI into torrent parameters (modern libtorrent 2.x API)
        atp = lt.parse_magnet_uri(magnet_uri)
        atp.save_path = get_config().get("general.download_path")
        if is_paused:
            atp.flags |= lt.torrent_flags.paused

        # Add the torrent to the session and start tracking
        self.torrents[magnet_uri] = self.session.add_torrent(atp)

    def remove_torrent(self, magnet_uri: str) -> None:
        handle = self.torrents.get(magnet_uri)
        if handle and handle.is_valid():
            self.session.remove_torrent(handle)
            del self.torrents[magnet_uri]

    def toggle_pause(self, magnet_uri: str) -> None:
        handle = self.torrents.get(magnet_uri)
        if not handle or not handle.is_valid():
            return

        status = handle.status()
        if (status.flags & lt.torrent_flags.paused) != 0:
            handle.resume()
        else:  # if not paused
            handle.pause()

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
            is_paused=(s.flags & lt.torrent_flags.paused) != 0,
        )

    def get_torrent_state_text(self, status: TorrentStatus, short: bool = False) -> str:
        if status["is_paused"]:
            return "Paused" if not short else "PD"

        idx = 1 if short else 0
        return self._STATE_MAP.get(status["state"], ("N/A", "N/A"))[idx]

    def check_metadata_updates(self) -> None:
        from torrra.core.torrent import get_torrent_manager

        tm = get_torrent_manager()

        for magnet_uri, handle in self.torrents.items():
            # Only check for metadata if we haven't updated it yet
            if (
                magnet_uri not in self._metadata_updated
                and handle.is_valid()
                and handle.has_metadata()
            ):
                # Get the torrent info
                try:
                    torrent_info = handle.torrent_file()
                    if torrent_info:
                        title = torrent_info.name()
                        size = torrent_info.total_size()

                        # Update the database with the actual metadata
                        tm.update_torrent_metadata(magnet_uri, title, size)
                        # Mark this torrent as having its metadata updated
                        self._metadata_updated.add(magnet_uri)
                except (AttributeError, RuntimeError):
                    # Skip if metadata is not fully available yet
                    continue
