from __future__ import annotations

from functools import lru_cache
from typing import ClassVar

import libtorrent as lt

from torrra._types import TorrentFileInfo, TorrentStatus
from torrra.core.config import get_config
from torrra.utils.magnet import enhance_magnet_uri, fix_magnet_uri


@lru_cache
def get_download_manager() -> DownloadManager:
    return DownloadManager()


class DownloadManager:
    _STATE_MAP: ClassVar[dict[int, tuple[str, str]]] = {
        lt.torrent_status.states.downloading: ("Downloading", "DL"),
        lt.torrent_status.states.seeding: ("Seeding", "SE"),
        lt.torrent_status.states.finished: ("Completed", "CD"),
        lt.torrent_status.states.downloading_metadata: ("Fetching", "FE"),
    }

    def __init__(self) -> None:
        settings: lt.settings_pack = {
            "listen_interfaces": "0.0.0.0:6881,[::]:6881,0.0.0.0:0",
            "enable_dht": True,
            "dht_bootstrap_nodes": "router.bittorrent.com:6881,dht.transmissionbt.com:6881,router.utorrent.com:6881,dht.libtorrent.org:25401",
            "enable_lsd": True,
            "enable_upnp": True,
            "enable_natpmp": True,
            "announce_to_all_trackers": True,
            "announce_to_all_tiers": True,
            "prefer_udp_trackers": True,
        }
        self.session: lt.session = lt.session(settings)
        self.torrents: dict[str, lt.torrent_handle] = {}
        self._file_priorities: dict[str, list[int]] = {}
        self._metadata_updated: set[str] = (
            set()
        )  # Track torrents whose metadata has been updated

    def add_torrent(
        self,
        magnet_uri: str,
        is_paused: bool = False,
        file_priorities: list[int] | None = None,
        torrent_info: lt.torrent_info | None = None,
    ) -> None:
        if file_priorities is not None:
            self._file_priorities[magnet_uri] = file_priorities

        if magnet_uri in self.torrents:
            # Torrent already exists, update paused state and priorities if needed
            handle = self.torrents[magnet_uri]
            if not handle.is_valid():
                # If handle is invalid, remove it and add the torrent fresh
                del self.torrents[magnet_uri]
            else:
                if file_priorities is not None and handle.status().has_metadata:
                    try:
                        handle.prioritize_files(file_priorities)
                    except (AttributeError, RuntimeError):
                        pass

                # Check current paused state and update if different
                current_status = handle.status()
                is_currently_paused = (
                    current_status.flags & lt.torrent_flags.paused
                ) != 0
                if is_currently_paused != is_paused:
                    if is_paused:
                        handle.unset_flags(lt.torrent_flags.auto_managed)
                        handle.pause()
                    else:
                        handle.set_flags(lt.torrent_flags.auto_managed)
                        handle.resume()
                return

        # Parse the magnet URI into torrent parameters (modern libtorrent 2.x API)
        # Handle malformed URIs (missing 'xt=urn:') and add default public trackers
        proper_magnet_uri = enhance_magnet_uri(fix_magnet_uri(magnet_uri))

        try:
            atp = lt.parse_magnet_uri(proper_magnet_uri)
            atp.save_path = get_config().get("general.download_path")
            if torrent_info is not None:
                atp.ti = torrent_info

            if is_paused:
                if torrent_info is not None or (
                    hasattr(atp, "ti") and atp.ti is not None
                ):
                    atp.flags |= lt.torrent_flags.paused
                    atp.flags &= ~lt.torrent_flags.auto_managed
                else:
                    # When fetching metadata from swarm before download, enable auto_managed
                    # and default_dont_download so metadata is fetched without downloading payload
                    atp.flags |= lt.torrent_flags.auto_managed
                    atp.flags |= lt.torrent_flags.default_dont_download
            else:
                atp.flags |= lt.torrent_flags.auto_managed

            # Add the torrent to the session and start tracking
            handle = self.session.add_torrent(atp)
            self.torrents[magnet_uri] = handle

            if (
                file_priorities is not None
                and handle.is_valid()
                and handle.status().has_metadata
            ):
                try:
                    handle.prioritize_files(file_priorities)
                except (AttributeError, RuntimeError):
                    pass
        except (RuntimeError, ValueError):
            return

    def remove_torrent(self, magnet_uri: str, delete_files: bool = False) -> None:
        handle = self.torrents.get(magnet_uri)
        if handle and handle.is_valid():
            if delete_files:
                self.session.remove_torrent(handle, lt.session.delete_files)
            else:
                self.session.remove_torrent(handle)
            del self.torrents[magnet_uri]
        self._file_priorities.pop(magnet_uri, None)
        self._metadata_updated.discard(magnet_uri)

    def set_file_priorities(self, magnet_uri: str, priorities: list[int]) -> None:
        self._file_priorities[magnet_uri] = priorities
        handle = self.torrents.get(magnet_uri)
        if handle and handle.is_valid() and handle.status().has_metadata:
            try:
                handle.prioritize_files(priorities)
            except (AttributeError, RuntimeError):
                pass

    def get_file_priorities(self, magnet_uri: str) -> list[int] | None:
        handle = self.torrents.get(magnet_uri)
        if handle and handle.is_valid() and handle.status().has_metadata:
            try:
                return [int(p) for p in handle.get_file_priorities()]
            except (AttributeError, RuntimeError):
                pass
        return self._file_priorities.get(magnet_uri)

    def get_torrent_files(self, magnet_uri: str) -> list[TorrentFileInfo] | None:
        handle = self.torrents.get(magnet_uri)
        if not handle or not handle.is_valid() or not handle.status().has_metadata:
            return None
        try:
            info = handle.torrent_file()
            if not info:
                return None
            fs = info.files()
            files: list[TorrentFileInfo] = []
            for i in range(fs.num_files()):
                if hasattr(lt.file_storage, "flag_pad_file") and (
                    fs.file_flags(i) & lt.file_storage.flag_pad_file
                ):
                    continue
                files.append(
                    TorrentFileInfo(
                        index=i,
                        path=fs.file_path(i).replace("\\", "/"),
                        size=fs.file_size(i),
                    )
                )
            return files
        except (AttributeError, RuntimeError):
            return None

    def toggle_pause(self, magnet_uri: str) -> None:
        handle = self.torrents.get(magnet_uri)
        if not handle or not handle.is_valid():
            return

        status = handle.status()
        if (status.flags & lt.torrent_flags.paused) != 0:
            handle.set_flags(lt.torrent_flags.auto_managed)
            handle.resume()
        else:  # if not paused
            handle.unset_flags(lt.torrent_flags.auto_managed)
            handle.pause()

    def get_torrent_status(self, magnet_uri: str) -> TorrentStatus | None:
        handle = self.torrents.get(magnet_uri)
        if not handle or not handle.is_valid():
            return None

        s = handle.status()
        is_seeding = (
            s.is_seeding
            or s.is_finished
            or s.state == lt.torrent_status.states.seeding
            or s.state == lt.torrent_status.states.finished
        )
        eta: float | None = None
        if not is_seeding:
            remaining_bytes = s.total_wanted - s.total_wanted_done
            if remaining_bytes > 0 and s.download_rate > 0:
                eta = remaining_bytes / s.download_rate

        return TorrentStatus(
            state=s.state,
            progress=s.progress * 100,
            down_speed=s.download_rate,
            up_speed=s.upload_rate,
            seeders=s.num_seeds,
            leechers=s.num_peers,
            is_paused=(s.flags & lt.torrent_flags.paused) != 0,
            eta=eta,
            is_seeding=is_seeding,
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
                and handle.status().has_metadata
            ):
                # Get the torrent info
                try:
                    torrent_info = handle.torrent_file()
                    if torrent_info:
                        title = torrent_info.name()
                        size = torrent_info.total_size()

                        # Apply pending file priorities if any
                        if magnet_uri in self._file_priorities:
                            handle.prioritize_files(self._file_priorities[magnet_uri])

                        # Update the database with the actual metadata
                        tm.update_torrent_metadata(magnet_uri, title, size)
                        # Mark this torrent as having its metadata updated
                        self._metadata_updated.add(magnet_uri)
                except (AttributeError, RuntimeError):
                    # Skip if metadata is not fully available yet
                    continue
