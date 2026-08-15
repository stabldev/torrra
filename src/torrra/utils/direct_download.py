import os
from typing import TYPE_CHECKING

import libtorrent as lt
from textual.widgets import ContentSwitcher

from torrra.core.torrent import get_torrent_manager
from torrra.utils.download_flow import start_download
from torrra.utils.magnet import resolve_magnet_uri
from torrra.widgets.sidebar import Sidebar

if TYPE_CHECKING:
    from torrra.screens.home import HomeScreen


async def handle_direct_download(home_screen: "HomeScreen", input_path: str) -> None:
    tm = get_torrent_manager()

    # Check if it's a local torrent file
    if os.path.isfile(input_path) and input_path.endswith(".torrent"):
        try:
            # Load torrent file and convert to magnet URI
            info = lt.torrent_info(input_path)
            magnet_uri = lt.make_magnet_uri(info)

            record = await start_download(
                home_screen.app,
                magnet_uri=magnet_uri,
                title=info.name(),
                size=info.total_size(),
                source="Direct Download",
                torrent_info=info,
            )
            if record is None:
                return
            tm.add_torrent(record)
            _switch_to_downloads(home_screen)
        except (RuntimeError, OSError, ValueError) as e:
            home_screen.app.notify(
                f"Error processing torrent file: {e!s}", severity="error"
            )
    else:
        # It's a magnet URI or URL, resolve it
        if magnet_uri := await resolve_magnet_uri(input_path):
            record = await start_download(
                home_screen.app,
                magnet_uri=magnet_uri,
                title=magnet_uri.split("&")[0]
                if magnet_uri.startswith("magnet:")
                else input_path,
                source="Direct Download",
            )
            if record is None:
                return
            tm.add_torrent(record)
            _switch_to_downloads(home_screen)
        else:
            home_screen.app.notify("Failed to resolve magnet URI", severity="error")


def _switch_to_downloads(home_screen: "HomeScreen") -> None:
    home_screen.query_one(
        "#content_switcher", ContentSwitcher
    ).current = "downloads_content"
    home_screen.query_one("#sidebar", Sidebar).select_node_by_group_id(
        "downloads_content"
    )
