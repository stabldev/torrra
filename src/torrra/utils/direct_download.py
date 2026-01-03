import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from torrra.screens.home import HomeScreen

import libtorrent as lt

from torrra._types import Torrent
from torrra.core.download import get_download_manager
from torrra.core.torrent import get_torrent_manager
from torrra.utils.magnet import resolve_magnet_uri


async def handle_direct_download(home_screen: "HomeScreen", input_path: str) -> None:
    dm, tm = get_download_manager(), get_torrent_manager()

    # Check if it's a local torrent file
    if os.path.isfile(input_path) and input_path.endswith(".torrent"):
        try:
            # Load torrent file and convert to magnet URI
            info = lt.torrent_info(input_path)
            magnet_uri = lt.make_magnet_uri(info)

            # Add to download manager
            dm.add_torrent(magnet_uri, is_paused=False)

            # Create torrent record with actual metadata from the file
            torrent_record = Torrent(
                magnet_uri=magnet_uri,
                title=info.name(),
                size=info.total_size(),
                source="Direct Download",
                seeders=0,
                leechers=0,
            )
            tm.add_torrent(torrent_record)

            # Switch to downloads content and select the new torrent
            home_screen.query_one("#content_switcher").current = "downloads_content"
            home_screen.query_one("#sidebar").select_node_by_group_id(
                "downloads_content"
            )
        except Exception as e:
            home_screen.app.notify(
                f"Error processing torrent file: {str(e)}", severity="error"
            )
    else:
        # It's a magnet URI or URL, resolve it
        if magnet_uri := await resolve_magnet_uri(input_path):
            # Add to download manager
            dm.add_torrent(magnet_uri, is_paused=False)

            # Create a basic torrent record to add to the database
            # For direct downloads, we'll use the magnet URI as the title initially
            # The actual title will be updated when the torrent metadata is available
            tm.add_torrent(
                Torrent(
                    magnet_uri=magnet_uri,
                    title=magnet_uri.split("&")[0]
                    if magnet_uri.startswith("magnet:")
                    else input_path,
                    size=0,  # Size will be updated when metadata is available
                    source="Direct Download",
                    seeders=0,
                    leechers=0,
                )
            )

            # Switch to downloads content and select the new torrent
            home_screen.query_one("#content_switcher").current = "downloads_content"
            home_screen.query_one("#sidebar").select_node_by_group_id(
                "downloads_content"
            )
        else:
            home_screen.app.notify("Failed to resolve magnet URI", severity="error")
