import os
import sys
try:
    import libtorrent as lt
except ImportError:
    print("Error: libtorrent not found")
    print("Installation guide: https://github.com/stabldev/torrra?tab=readme-ov-file#installation")
    sys.exit(1)

import time
from rich.progress import (
    Progress,
    BarColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
    TextColumn,
    TaskProgressColumn,
    DownloadColumn,
)
from rich.console import Console

console = Console()


def download_magnet(magnet_uri: str, path: str):
    ses = lt.session()
    ses.listen_on(6881, 6891)

    # handle relative and absolute paths
    save_path = os.path.abspath(os.path.expanduser(path))

    params = {
        "save_path": save_path,
        "storage_mode": lt.storage_mode_t(2),
    }

    handle = lt.add_magnet_uri(ses, magnet_uri, params)

    console.print("[bold green]Downloading metadata...[/bold green]")
    while not handle.has_metadata():
        time.sleep(0.5)

    torrent_info = handle.get_torrent_info()
    total_size = torrent_info.total_size()
    file_count = torrent_info.num_files()

    console.print(
        f"[bold green]Starting download: [cyan]{handle.name()}[/cyan][/bold green]"
    )
    console.print(
        f"[yellow]Size:[/yellow] {total_size/(1024*1024):.2f} MB | [yellow]Files:[/yellow] {file_count}"
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

    console.print(
        f"\n[bold green]✓ Download complete: [cyan]{handle.name()}[/cyan][/bold green]"
    )
    console.print(f"[green]Saved to: [underline]{save_path}[/underline][/green]")
