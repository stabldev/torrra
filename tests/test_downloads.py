from unittest.mock import MagicMock, patch

from textual.app import App

from torrra._types import Indexer, TorrentFileStatus
from torrra.screens import home as home_module
from torrra.screens.home import HomeScreen
from torrra.widgets import downloads as downloads_module
from torrra.widgets.downloads import DownloadsContent

RECORDS = [
    {
        "magnet_uri": "magnet:?xt=urn:btih:abc",
        "title": "Selective",
        "size": 100.0,
        "source": "test",
        "is_paused": False,
        "is_notified": False,
        "selected_files": [0, 2],
    },
    {
        "magnet_uri": "magnet:?xt=urn:btih:def",
        "title": "Full",
        "size": 200.0,
        "source": "test",
        "is_paused": True,
        "is_notified": False,
        "selected_files": None,
    },
]


class _Harness(App[None]):
    def compose(self):
        yield HomeScreen(
            indexer=Indexer(
                name="jackett",
                url="http://mock.indexer.url",
                api_key="mock_api_key",
            ),
            search_query="",
            use_cache=False,
        )


async def test_startup_restore_applies_saved_selection_priorities():
    dm = MagicMock()
    dm.torrents = {}
    tm = MagicMock()
    tm.get_all_torrents.return_value = RECORDS

    with (
        patch.object(home_module, "get_download_manager", return_value=dm),
        patch.object(home_module, "get_torrent_manager", return_value=tm),
    ):
        async with _Harness().run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

    dm.add_torrent.assert_any_call(
        "magnet:?xt=urn:btih:abc",
        is_paused=False,
        file_priorities=[1, 0, 1],
    )
    dm.add_torrent.assert_any_call(
        "magnet:?xt=urn:btih:def",
        is_paused=True,
        file_priorities=None,
    )


async def test_f_opens_file_manager_and_applies_selection():
    from torrra.screens.file_manager import FileManagerScreen

    dm = MagicMock()
    dm.torrents = {}
    dm.get_file_details.return_value = [
        TorrentFileStatus(index=0, path="a.bin", size=10, downloaded=0, priority=1),
        TorrentFileStatus(index=1, path="b.bin", size=20, downloaded=0, priority=0),
    ]
    dm.prioritize_files.return_value = True
    tm = MagicMock()
    tm.get_all_torrents.return_value = RECORDS

    with (
        patch.object(home_module, "get_download_manager", return_value=dm),
        patch.object(home_module, "get_torrent_manager", return_value=tm),
        patch.object(downloads_module, "get_download_manager", return_value=dm),
        patch.object(downloads_module, "get_torrent_manager", return_value=tm),
    ):
        async with _Harness().run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            downloads = pilot.app.query_one(DownloadsContent)
            pilot.app.query_one("#content_switcher").current = "downloads_content"
            await pilot.pause()
            await pilot.pause()
            downloads._selected_torrent = RECORDS[0]

            assert ("f", "show_file_manager") in DownloadsContent.BINDINGS
            downloads.action_show_file_manager()
            await pilot.pause()
            await pilot.pause()

            assert isinstance(pilot.app.screen, FileManagerScreen)

            table = pilot.app.screen.query_one("#file_manager_table")
            table.move_cursor(row=1)  # b.bin (currently deselected)
            await pilot.press("space")
            await pilot.click("#file_manager_apply")
            await pilot.pause()

    dm.prioritize_files.assert_called_once_with("magnet:?xt=urn:btih:abc", {0, 1})
    tm.update_torrent_selected_files.assert_called_once_with(
        "magnet:?xt=urn:btih:abc", [0, 1]
    )
