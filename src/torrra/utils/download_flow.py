from typing import TYPE_CHECKING

import libtorrent as lt

from torrra._types import Torrent
from torrra.core.config import get_config
from torrra.core.download import get_download_manager
from torrra.screens.file_selection import DOWNLOAD_ALL

if TYPE_CHECKING:
    from torrra.app import TorrraApp


async def start_download(
    app: "TorrraApp",
    *,
    magnet_uri: str,
    title: str,
    source: str,
    size: float = 0,
    torrent_info: lt.torrent_info | None = None,
) -> Torrent | None:
    """Start a torrent download, optionally letting the user pick files first.

    When `general.select_files` is enabled the torrent is added in upload mode
    so it runs only long enough to fetch metadata without downloading anything,
    the user picks which files to download, and only the selected files are
    prioritized before resuming.

    Returns a `Torrent` record to store in the database, or `None` if the
    user cancelled or metadata could not be fetched.
    """
    dm = get_download_manager()

    if not get_config().get("general.select_files", True):
        dm.add_torrent(magnet_uri, is_paused=False, torrent_info=torrent_info)
        return _build_record(magnet_uri, title, size, source)

    dm.add_torrent(magnet_uri, metadata_only=True, torrent_info=torrent_info)

    worker = app._run_file_selection(magnet_uri, title)
    selected = await worker.wait()
    if selected is None:
        dm.remove_torrent(magnet_uri)
        return None

    if selected == DOWNLOAD_ALL:
        # Download everything: restore file priorities to 1 when metadata is
        # already available (otherwise default_dont_download is lifted by
        # resume_torrent before metadata arrives, so files default to 1).
        if files := dm.get_files(magnet_uri):
            dm.prioritize_files(magnet_uri, {f.index for f in files})
        dm.resume_torrent(magnet_uri)
    else:
        if not dm.prioritize_files(magnet_uri, set(selected)):
            # Metadata vanished mid-selection; don't resume into a
            # download-everything state, drop the torrent instead.
            dm.remove_torrent(magnet_uri)
            app.notify(
                "Could not apply file selection",
                title="Download Failed",
                severity="error",
            )
            return None
        dm.resume_torrent(magnet_uri)

    # Prefer metadata from libtorrent when available (authoritative title/size)
    record_title, record_size = title, size
    if metadata := dm.get_metadata(magnet_uri):
        record_title, record_size = metadata

    record = _build_record(magnet_uri, record_title, record_size, source)
    if selected is not None and selected != DOWNLOAD_ALL:
        record.selected_files = sorted(selected)
    return record


def _build_record(magnet_uri: str, title: str, size: float, source: str) -> Torrent:
    return Torrent(
        magnet_uri=magnet_uri,
        title=title,
        size=size,
        seeders=0,
        leechers=0,
        source=source,
    )
