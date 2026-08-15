import asyncio
import time
from functools import lru_cache
from typing import ClassVar

import libtorrent as lt

from torrra._types import TorrentFile, TorrentFileStatus, TorrentStatus
from torrra.core.config import get_config
from torrra.utils.magnet import fix_magnet_uri

METADATA_TIMEOUT = 45.0


def build_priorities(num_files: int, selected_indices: set[int]) -> list[int]:
    """Build per-file download priorities (0=skip, 1=download)."""
    return [1 if i in selected_indices else 0 for i in range(num_files)]


def selection_priorities(selected_files: list[int] | None) -> list[int] | None:
    """Build a partial priority vector from a saved file selection.

    Files beyond the vector default to 0 via `default_dont_download`, so
    only the saved selection is downloaded.
    """
    if not selected_files:
        return None
    max_index = max(selected_files)
    return [1 if i in selected_files else 0 for i in range(max_index + 1)]


@lru_cache
def get_download_manager() -> "DownloadManager":
    return DownloadManager()


class DownloadManager:
    _STATE_MAP: ClassVar[dict[int, tuple[str, str]]] = {
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

    def add_torrent(
        self,
        magnet_uri: str,
        is_paused: bool = False,
        torrent_info: lt.torrent_info | None = None,
        metadata_only: bool = False,
        file_priorities: list[int] | None = None,
    ) -> None:
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
                    if is_paused:
                        handle.unset_flags(lt.torrent_flags.auto_managed)
                        handle.pause()
                    else:
                        handle.set_flags(lt.torrent_flags.auto_managed)
                        handle.resume()
                return

        # Parse the magnet URI into torrent parameters (modern libtorrent 2.x API)
        # Handle malformed URIs (missing 'xt=urn:') that might be stored in the DB
        proper_magnet_uri = fix_magnet_uri(magnet_uri)

        atp = lt.parse_magnet_uri(proper_magnet_uri)
        atp.save_path = get_config().get("general.download_path")
        if torrent_info is not None:
            atp.ti = torrent_info
        if metadata_only:
            # Run to fetch metadata but download nothing until files are picked.
            # upload_mode + default_dont_download keep every file at priority 0,
            # so no empty placeholder files are created while metadata is fetched.
            atp.flags |= (
                lt.torrent_flags.upload_mode | lt.torrent_flags.default_dont_download
            )
            atp.flags &= ~lt.torrent_flags.paused
        elif is_paused:
            atp.flags |= lt.torrent_flags.paused
            atp.flags &= ~lt.torrent_flags.auto_managed
        else:
            atp.flags |= lt.torrent_flags.auto_managed

        if file_priorities is not None:
            # Restoring a selective download: apply the saved selection now.
            # libtorrent applies these atomically once metadata arrives, and
            # default_dont_download keeps any files beyond the vector at 0.
            atp.file_priorities = file_priorities
            atp.flags |= lt.torrent_flags.default_dont_download

        # Add the torrent to the session and start tracking
        self.torrents[magnet_uri] = self.session.add_torrent(atp)

    def remove_torrent(self, magnet_uri: str, delete_files: bool = False) -> None:
        handle = self.torrents.get(magnet_uri)
        if handle and handle.is_valid():
            if delete_files:
                self.session.remove_torrent(handle, lt.session.delete_files)
            else:
                self.session.remove_torrent(handle)
            del self.torrents[magnet_uri]

    def has_metadata(self, magnet_uri: str) -> bool:
        handle = self.torrents.get(magnet_uri)
        return bool(handle and handle.is_valid() and handle.has_metadata())

    def get_files(self, magnet_uri: str) -> list[TorrentFile] | None:
        handle = self.torrents.get(magnet_uri)
        if not handle or not handle.is_valid() or not handle.has_metadata():
            return None

        try:
            torrent_info = handle.torrent_file()
        except (AttributeError, RuntimeError):
            return None
        if not torrent_info:
            return None

        files = torrent_info.files()
        return [
            TorrentFile(index=i, path=files.file_path(i), size=files.file_size(i))
            for i in range(files.num_files())
        ]

    def get_file_details(self, magnet_uri: str) -> list[TorrentFileStatus] | None:
        handle = self.torrents.get(magnet_uri)
        if not handle or not handle.is_valid() or not handle.has_metadata():
            return None

        try:
            torrent_info = handle.torrent_file()
        except (AttributeError, RuntimeError):
            return None
        if not torrent_info:
            return None

        files = torrent_info.files()
        num_files = files.num_files()

        try:
            downloaded = handle.file_progress()
        except (AttributeError, RuntimeError):
            downloaded = []
        try:
            priorities = handle.file_priorities()
        except (AttributeError, RuntimeError):
            priorities = []

        return [
            TorrentFileStatus(
                index=i,
                path=files.file_path(i),
                size=files.file_size(i),
                downloaded=downloaded[i] if i < len(downloaded) else 0,
                priority=priorities[i] if i < len(priorities) else 0,
            )
            for i in range(num_files)
        ]

    def get_metadata(self, magnet_uri: str) -> tuple[str, int] | None:
        handle = self.torrents.get(magnet_uri)
        if not handle or not handle.is_valid() or not handle.has_metadata():
            return None

        try:
            torrent_info = handle.torrent_file()
        except (AttributeError, RuntimeError):
            return None
        if not torrent_info:
            return None

        return torrent_info.name(), torrent_info.total_size()

    async def wait_for_metadata(
        self, magnet_uri: str, timeout: float = METADATA_TIMEOUT
    ) -> list[TorrentFile] | None:
        handle = self.torrents.get(magnet_uri)
        if not handle or not handle.is_valid():
            return None

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if handle.has_metadata():
                return self.get_files(magnet_uri)
            await asyncio.sleep(0.5)
        return None

    def prioritize_files(self, magnet_uri: str, selected_indices: set[int]) -> bool:
        handle = self.torrents.get(magnet_uri)
        if not handle or not handle.is_valid() or not handle.has_metadata():
            return False

        try:
            torrent_info = handle.torrent_file()
        except (AttributeError, RuntimeError):
            return False
        if not torrent_info:
            return False

        num_files = torrent_info.files().num_files()
        handle.prioritize_files(build_priorities(num_files, selected_indices))
        return True

    def resume_torrent(self, magnet_uri: str) -> bool:
        handle = self.torrents.get(magnet_uri)
        if not handle or not handle.is_valid():
            return False

        handle.unset_flags(
            lt.torrent_flags.upload_mode | lt.torrent_flags.default_dont_download
        )
        handle.set_flags(lt.torrent_flags.auto_managed)
        handle.resume()
        return True

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

        # Once all wanted bytes are done the torrent is complete for the user.
        # libtorrent may still pull the priority-0 portion of pieces shared
        # with deselected files ("partial pieces may still be downloaded"),
        # so report no download speed while finished/seeding.
        down_speed = 0.0 if is_seeding else s.download_rate

        return TorrentStatus(
            state=s.state,
            progress=s.progress * 100,
            down_speed=down_speed,
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
