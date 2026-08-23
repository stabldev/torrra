from __future__ import annotations

import os
from functools import lru_cache
from typing import ClassVar

import libtorrent as lt

from torrra._types import SessionStats, TorrentFileInfo, TorrentStatus
from torrra.core.config import get_config
from torrra.utils.helpers import coerce_speed_limit
from torrra.utils.magnet import enhance_magnet_uri, fix_magnet_uri


@lru_cache
def get_download_manager() -> DownloadManager:
    return DownloadManager()


class DownloadManager:
    _STATE_MAP: ClassVar[dict[int, tuple[str, str]]] = {
        lt.torrent_status.states.downloading: ("Downloading", "DOWN"),
        lt.torrent_status.states.seeding: ("Seeding", "SEED"),
        lt.torrent_status.states.finished: ("Completed", "DONE"),
        lt.torrent_status.states.downloading_metadata: ("Fetching", "META"),
        lt.torrent_status.states.checking_files: ("Checking", "CHCK"),
        lt.torrent_status.states.checking_resume_data: ("Checking", "CHCK"),
        lt.torrent_status.states.queued_for_checking: ("Checking", "CHCK"),
        lt.torrent_status.states.allocating: ("Allocating", "ALOC"),
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
        self._limits: dict[str, tuple[int, int]] = {}
        self._metadata_updated: set[str] = (
            set()
        )  # Track torrents whose metadata has been updated
        # apply session-wide speed limits from config ("turtle mode"),
        # a no-op when disabled or unset
        self.apply_global_limits()

    def add_torrent(
        self,
        magnet_uri: str,
        is_paused: bool = False,
        file_priorities: list[int] | None = None,
        torrent_info: lt.torrent_info | None = None,
        upload_limit: int | None = None,
        download_limit: int | None = None,
    ) -> None:
        if file_priorities is not None:
            self._file_priorities[magnet_uri] = file_priorities

        # Seed per-torrent speed limits (e.g. loaded from the database).
        # -1 means unlimited, which is libtorrent's sentinel value.
        if upload_limit is not None or download_limit is not None:
            up = upload_limit if upload_limit is not None else -1
            down = download_limit if download_limit is not None else -1
            self._limits[magnet_uri] = (up, down)

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

                # Re-apply any stored per-torrent speed limits
                self._apply_stored_limits(handle, magnet_uri)

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

            # Apply any stored per-torrent speed limits
            self._apply_stored_limits(handle, magnet_uri)
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

    def set_torrent_limits(
        self, magnet_uri: str, upload_limit: int, download_limit: int
    ) -> None:
        # store limits keyed by magnet_uri; -1 means unlimited
        self._limits[magnet_uri] = (upload_limit, download_limit)
        handle = self.torrents.get(magnet_uri)
        if handle and handle.is_valid():
            self._apply_stored_limits(handle, magnet_uri)
        # also persist to the database so limits survive restarts
        self._tm_update_limits(magnet_uri, upload_limit, download_limit)

    def get_torrent_limits(self, magnet_uri: str) -> tuple[int, int] | None:
        handle = self.torrents.get(magnet_uri)
        if handle and handle.is_valid():
            try:
                # libtorrent uses -1 (and 0) to mean unlimited; normalize so
                # callers and the UI only ever see -1 for "no limit"
                up = handle.upload_limit()
                down = handle.download_limit()
                return (
                    -1 if up is None or up <= 0 else up,
                    -1 if down is None or down <= 0 else down,
                )
            except (AttributeError, RuntimeError):
                pass
        return self._limits.get(magnet_uri)

    def apply_global_limits(self) -> None:
        # session-wide bandwidth caps from [speed_limit] in config.toml.
        # 0 means unlimited, which is also libtorrent's sentinel value,
        # so values pass through unchanged. caps coexist with per-torrent
        # limits (the effective rate is the lower of the two).
        config = get_config()
        up = coerce_speed_limit(config.get("speed_limit.upload_limit", 0))
        down = coerce_speed_limit(config.get("speed_limit.download_limit", 0))
        try:
            self.session.apply_settings(
                {
                    "upload_rate_limit": max(0, up),
                    "download_rate_limit": max(0, down),
                }
            )
        except (AttributeError, RuntimeError):
            pass

    def is_speed_limit_enabled(self) -> bool:
        return bool(get_config().get("speed_limit.enabled", False))

    def set_speed_limit_enabled(self, enabled: bool) -> None:
        get_config().set("speed_limit.enabled", str(enabled).lower())
        if enabled:
            self.apply_global_limits()
        else:
            try:
                self.session.apply_settings(
                    {"upload_rate_limit": 0, "download_rate_limit": 0}
                )
            except (AttributeError, RuntimeError):
                pass

    def _apply_stored_limits(self, handle: lt.torrent_handle, magnet_uri: str) -> None:
        limits = self._limits.get(magnet_uri)
        if limits is None:
            return
        up, down = limits
        try:
            handle.set_upload_limit(up)
            handle.set_download_limit(down)
        except (AttributeError, RuntimeError):
            pass

    def _tm_update_limits(
        self, magnet_uri: str, upload_limit: int, download_limit: int
    ) -> None:
        from torrra.core.torrent import get_torrent_manager

        try:
            get_torrent_manager().update_torrent_limits(
                magnet_uri, upload_limit, download_limit
            )
        except (AttributeError, RuntimeError):
            pass

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

    def recheck_torrent(self, magnet_uri: str) -> None:
        handle = self.torrents.get(magnet_uri)
        if handle and handle.is_valid():
            try:
                handle.force_recheck()
            except (AttributeError, RuntimeError):
                pass

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

        error_msg: str | None = None
        if s.errc and s.errc.value() != 0:
            error_msg = s.errc.message()
        elif s.error:
            error_msg = s.error

        error_file = getattr(s, "error_file", -1)

        is_paused = (s.flags & lt.torrent_flags.paused) != 0
        is_auto_managed = (s.flags & lt.torrent_flags.auto_managed) != 0
        is_queued = is_paused and is_auto_managed

        is_missing_files = False
        if error_msg and (
            error_file >= 0
            or "no such file" in error_msg.lower()
            or "not found" in error_msg.lower()
            or "missing" in error_msg.lower()
        ):
            is_missing_files = True

        if (
            not is_missing_files
            and s.has_metadata
            and (is_seeding or s.progress >= 1.0)
        ):
            try:
                info = handle.torrent_file()
                if info:
                    save_path = s.save_path or get_config().get("general.download_path")
                    if save_path:
                        fs = info.files()
                        priorities = self.get_file_priorities(magnet_uri)
                        for i in range(fs.num_files()):
                            if (
                                priorities is not None
                                and i < len(priorities)
                                and priorities[i] == 0
                            ):
                                continue
                            if hasattr(lt.file_storage, "flag_pad_file") and (
                                fs.file_flags(i) & lt.file_storage.flag_pad_file
                            ):
                                continue
                            file_path = os.path.join(save_path, fs.file_path(i))
                            if not os.path.exists(file_path):
                                is_missing_files = True
                                break
            except (AttributeError, RuntimeError, OSError):
                pass

        connected_seeds = s.num_seeds
        total_seeds = max(connected_seeds, getattr(s, "list_seeds", 0))
        connected_peers = getattr(s, "num_peers", 0)
        total_peers = max(connected_peers, getattr(s, "list_peers", 0))

        return TorrentStatus(
            state=s.state,
            progress=s.progress * 100,
            down_speed=s.download_rate,
            up_speed=s.upload_rate,
            seeders=connected_seeds,
            total_seeders=total_seeds,
            leechers=connected_peers,
            peers=connected_peers,
            total_peers=total_peers,
            is_paused=is_paused,
            eta=eta,
            is_seeding=is_seeding,
            error=error_msg,
            error_file=error_file,
            is_missing_files=is_missing_files,
            is_queued=is_queued,
        )

    def get_torrent_state_text(self, status: TorrentStatus, short: bool = False) -> str:
        # Check missing files and errors first
        if status.get("is_missing_files"):
            return "MISS" if short else "Missing Files"

        if error := status.get("error"):
            error_msg = error.lower()
            if (
                status.get("error_file", -1) >= 0
                or "no such file" in error_msg
                or "not found" in error_msg
                or "missing" in error_msg
            ):
                return "MISS" if short else "Missing Files"
            return "ERRO" if short else "Error"

        # Check paused and queued states
        if status.get("is_paused"):
            if status.get("is_queued"):
                return "QUEU" if short else "Queued"
            return "PAUS" if short else "Paused"

        state = status.get("state")

        # Stalled download
        if (
            state == lt.torrent_status.states.downloading
            and status.get("down_speed", 0) == 0
        ):
            return "STAL" if short else "Stalled"

        # Seeding fallback when is_seeding is set but state is not finished
        if state != lt.torrent_status.states.finished and status.get("is_seeding"):
            return "SEED" if short else "Seeding"

        # Standard state lookup from _STATE_MAP
        idx = 1 if short else 0
        if state is not None and state in self._STATE_MAP:
            return self._STATE_MAP[state][idx]

        return "N/A"

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
                try:
                    torrent_info = handle.torrent_file()
                    if torrent_info:
                        title = torrent_info.name()
                        size = torrent_info.total_size()

                        # Apply pending file priorities if any
                        if magnet_uri in self._file_priorities:
                            handle.prioritize_files(self._file_priorities[magnet_uri])

                        # Re-apply per-torrent speed limits
                        self._apply_stored_limits(handle, magnet_uri)

                        tm.update_torrent_metadata(magnet_uri, title, size)
                        self._metadata_updated.add(magnet_uri)
                except (AttributeError, RuntimeError):
                    continue

    def get_session_stats(self) -> SessionStats:
        try:
            import warnings

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                status = self.session.status()
            return SessionStats(
                download_rate=float(status.download_rate),
                upload_rate=float(status.upload_rate),
                dht_nodes=int(status.dht_nodes),
            )
        except (AttributeError, RuntimeError):
            down_speed = 0.0
            up_speed = 0.0
            for handle in self.torrents.values():
                if handle.is_valid():
                    try:
                        s = handle.status()
                        down_speed += s.download_rate
                        up_speed += s.upload_rate
                    except (AttributeError, RuntimeError):
                        pass
            return SessionStats(
                download_rate=down_speed,
                upload_rate=up_speed,
                dht_nodes=0,
            )
