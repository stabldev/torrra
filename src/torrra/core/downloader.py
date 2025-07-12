import os
import time

import libtorrent as lt
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from torrra.constants import UI_STRINGS

console = Console()


def download_magnet(magnet_uri: str, path: str) -> None:
    ses = lt.session()
    ses.listen_on(6881, 6891)

    # handle relative and absolute paths
    save_path = os.path.abspath(os.path.expanduser(path))

    params = {
        "save_path": save_path,
        "storage_mode": lt.storage_mode_t(2),
    }

    handle = lt.add_magnet_uri(ses, magnet_uri, params)

    console.print(UI_STRINGS["status_downloading_metadata"])

    while not handle.has_metadata():
        time.sleep(0.5)

    torrent_info = handle.get_torrent_info()
    total_size = torrent_info.total_size()
    file_count = torrent_info.num_files()

    console.print(UI_STRINGS["status_starting_download"].format(name=handle.name()))
    console.print(
        UI_STRINGS["info_size_files"].format(
            size=total_size / (1024 * 1024), count=file_count
        )
    )

    with Progress(
        TextColumn("[bold blue]{task.fields[filename]}"),
        BarColumn(),
        TaskProgressColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "download", filename=handle.name(), peers=0, total=total_size
        )

        prev_downloaded = 0
        prev_time = time.time()

        while not handle.is_seed():
            s = handle.status()

            # calculate real-time download speed
            cur_time = time.time()
            downloaded = s.total_done
            elapsed = cur_time - prev_time
            speed = (downloaded - prev_downloaded) / elapsed if elapsed > 0 else 0

            progress.update(task, completed=downloaded, speed=speed)

            prev_downloaded = downloaded
            prev_time = cur_time
            time.sleep(0.5)

    console.print(UI_STRINGS["status_download_complete"].format(name=handle.name()))
    console.print(UI_STRINGS["info_saved_to"].format(path=save_path))
