import urllib.parse
from typing import TYPE_CHECKING

from textual.widgets import ContentSwitcher

from torrra._types import Torrent
from torrra.core.download import get_download_manager
from torrra.core.torrent import get_torrent_manager
from torrra.screens.file_selection import FileSelectionScreen
from torrra.utils.magnet import resolve_torrent
from torrra.widgets.sidebar import Sidebar

if TYPE_CHECKING:
    from torrra.screens.home import HomeScreen


async def handle_direct_download(home_screen: "HomeScreen", input_path: str) -> None:
    dm, tm = get_download_manager(), get_torrent_manager()

    magnet_uri, torrent_info = await resolve_torrent(input_path)
    if not magnet_uri:
        home_screen.app.notify(
            "Failed to resolve torrent or magnet URI", severity="error"
        )
        return

    title = input_path
    size = 0
    if torrent_info is not None:
        title = torrent_info.name()
        size = torrent_info.total_size()
    elif magnet_uri.startswith("magnet:"):
        dn_list = urllib.parse.parse_qs(urllib.parse.urlsplit(magnet_uri).query).get(
            "dn"
        )
        if dn_list and dn_list[0]:
            title = dn_list[0]

    torrent_record = Torrent(
        magnet_uri=magnet_uri,
        title=title,
        size=size,
        source="Direct Download",
        seeders=0,
        leechers=0,
    )

    def on_files_selected(priorities: list[int] | None) -> None:
        if priorities is None:
            return

        actual_priorities = priorities if priorities else None
        torrent_record.file_priorities = actual_priorities
        dm.add_torrent(
            magnet_uri,
            is_paused=False,
            file_priorities=actual_priorities,
            torrent_info=torrent_info,
        )
        tm.add_torrent(torrent_record, file_priorities=actual_priorities)

        # Refresh downloads content table and ensure downloads is selected
        from torrra.widgets.downloads import DownloadsContent

        home_screen.query_one(DownloadsContent).refresh_torrents()
        home_screen.query_one(
            "#content_switcher", ContentSwitcher
        ).current = "downloads_content"
        home_screen.query_one("#sidebar", Sidebar).select_node_by_group_id(
            "downloads_content"
        )

    home_screen.app.push_screen(
        FileSelectionScreen(torrent=torrent_record, torrent_info=torrent_info),
        on_files_selected,
    )
