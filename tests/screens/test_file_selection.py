from typing import Any
from unittest.mock import MagicMock

import pytest
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Static

from torrra._types import Torrent
from torrra.core.download import get_download_manager
from torrra.core.torrent import get_torrent_manager
from torrra.screens.file_selection import FileSelectionList, FileSelectionScreen


def create_mock_torrent_info() -> MagicMock:
    ti = MagicMock()
    ti.name.return_value = "Ubuntu 24.04 Pack"
    fs = MagicMock()
    fs.num_files.return_value = 3
    fs.file_flags.return_value = 0
    fs.file_path.side_effect = lambda i: [
        "Ubuntu/ubuntu-24.04-desktop.iso",
        "Ubuntu/SHA256SUMS",
        "Ubuntu/README.md",
    ][i]
    fs.file_size.side_effect = lambda i: [2_500_000_000, 1024, 2048][i]
    ti.files.return_value = fs
    return ti


class DummyHostApp(App[None]):
    def __init__(self, screen_to_push: FileSelectionScreen):
        super().__init__()
        self.screen_to_push = screen_to_push
        self.result: list[int] | None = "UNSET"  # type: ignore

    def on_mount(self) -> None:
        self.push_screen(self.screen_to_push, self._on_result)

    def _on_result(self, res: list[int] | None) -> None:
        self.result = res


async def test_file_selection_screen_initial_state():
    mock_ti = create_mock_torrent_info()
    torrent = Torrent(
        magnet_uri="magnet:?xt=urn:btih:mocktest",
        title="Ubuntu 24.04 Pack",
        size=2_500_003_072,
        seeders=10,
        leechers=2,
        source="Mock",
    )

    screen = FileSelectionScreen(torrent=torrent, torrent_info=mock_ti)
    app = DummyHostApp(screen)

    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, FileSelectionScreen)

        selection_list = app.screen.query_one(FileSelectionList)
        # All 3 files should be initially selected
        assert set(selection_list.selected) == {0, 1, 2}

        stats = app.screen.query_one("#selection-stats", Static)
        assert "3/3" in str(stats.content)


async def test_file_selection_screen_filename_truncation_with_size():
    long_name = "Very.Long.Series.Title.2026.S01E01.1080p.BluRay.x265.10bit.DTS-HD.MA.7.1-GROUP/Subs/English_Full_SDH_Commentary.srt"
    mock_ti = MagicMock()
    mock_ti.name.return_value = "Long Torrent Title"
    mock_files = MagicMock()
    mock_files.num_files.return_value = 1
    mock_files.file_path.side_effect = lambda idx: long_name
    mock_files.file_size.side_effect = lambda idx: 50000
    mock_files.file_flags.side_effect = lambda idx: 0
    mock_ti.files.return_value = mock_files

    torrent = Torrent(
        magnet_uri="magnet:?xt=urn:btih:mocklong",
        title="Long Torrent Title",
        size=50000,
        seeders=10,
        leechers=2,
        source="Mock",
    )

    screen = FileSelectionScreen(torrent=torrent, torrent_info=mock_ti)
    app = DummyHostApp(screen)

    async with app.run_test() as pilot:
        await pilot.pause()
        selection_list = app.screen.query_one(FileSelectionList)
        prompt_text = str(selection_list.get_option_at_index(0).prompt)
        assert "..." in prompt_text
        assert "48.83 KB" in prompt_text


async def test_file_selection_screen_select_none_and_all():
    mock_ti = create_mock_torrent_info()
    torrent = Torrent(
        magnet_uri="magnet:?xt=urn:btih:mocktest",
        title="Ubuntu 24.04 Pack",
        size=2_500_003_072,
        seeders=10,
        leechers=2,
        source="Mock",
    )

    screen = FileSelectionScreen(torrent=torrent, torrent_info=mock_ti)
    app = DummyHostApp(screen)

    async with app.run_test() as pilot:
        await pilot.pause()
        selection_list = app.screen.query_one(FileSelectionList)

        # Press 'n' for none
        await pilot.press("n")
        await pilot.pause()
        assert len(selection_list.selected) == 0

        # Press 'a' for all
        await pilot.press("a")
        await pilot.pause()
        assert set(selection_list.selected) == {0, 1, 2}


async def test_file_selection_screen_invert():
    mock_ti = create_mock_torrent_info()
    torrent = Torrent(
        magnet_uri="magnet:?xt=urn:btih:mocktest",
        title="Ubuntu 24.04 Pack",
        size=2_500_003_072,
        seeders=10,
        leechers=2,
        source="Mock",
    )

    screen = FileSelectionScreen(
        torrent=torrent,
        torrent_info=mock_ti,
        existing_priorities=[4, 0, 0],
    )
    app = DummyHostApp(screen)

    async with app.run_test() as pilot:
        await pilot.pause()
        selection_list = app.screen.query_one(FileSelectionList)
        assert set(selection_list.selected) == {0}

        # Press 'i' to invert
        await pilot.press("i")
        await pilot.pause()
        assert set(selection_list.selected) == {1, 2}


async def test_file_selection_screen_confirm_with_enter():
    mock_ti = create_mock_torrent_info()
    torrent = Torrent(
        magnet_uri="magnet:?xt=urn:btih:mocktest",
        title="Ubuntu 24.04 Pack",
        size=2_500_003_072,
        seeders=10,
        leechers=2,
        source="Mock",
    )

    screen = FileSelectionScreen(torrent=torrent, torrent_info=mock_ti)
    app = DummyHostApp(screen)

    async with app.run_test() as pilot:
        await pilot.pause()

        # Deselect all, then toggle first file (index 0)
        await pilot.press("n")
        await pilot.pause()
        await pilot.press("space")
        await pilot.pause()

        selection_list = app.screen.query_one(FileSelectionList)
        assert set(selection_list.selected) == {0}

        # Confirm with enter
        await pilot.press("enter")
        await pilot.pause()

        # Returned priorities: file 0 has 4, files 1 and 2 have 0
        assert app.result == [4, 0, 0]


async def test_file_selection_skip_metadata_keys():
    torrent = Torrent(
        magnet_uri="magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567",
        title="Ubuntu 24.04 Pack",
        size=2_500_003_072,
        seeders=10,
        leechers=2,
        source="Mock",
    )

    # Press 'd' during loading to skip metadata
    screen = FileSelectionScreen(torrent=torrent)
    app = DummyHostApp(screen)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        assert app.result == []


async def test_file_selection_screen_cancel_with_escape():
    mock_ti = create_mock_torrent_info()
    torrent = Torrent(
        magnet_uri="magnet:?xt=urn:btih:mocktest",
        title="Ubuntu 24.04 Pack",
        size=2_500_003_072,
        seeders=10,
        leechers=2,
        source="Mock",
    )

    screen = FileSelectionScreen(torrent=torrent, torrent_info=mock_ti)
    app = DummyHostApp(screen)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()

        assert app.result is None


async def test_file_selection_screen_edit_mode():
    mock_ti = create_mock_torrent_info()
    torrent = Torrent(
        magnet_uri="magnet:?xt=urn:btih:mocktest",
        title="Ubuntu 24.04 Pack",
        size=2_500_003_072,
        seeders=10,
        leechers=2,
        source="Mock",
    )

    screen = FileSelectionScreen(
        torrent=torrent,
        existing_priorities=[4, 0, 4],
        torrent_info=mock_ti,
        is_edit_mode=True,
    )
    app = DummyHostApp(screen)

    async with app.run_test() as pilot:
        await pilot.pause()
        assert "Ubuntu 24.04 Pack" in str(app.screen.query_one("#torrent-name", Static).content)
        footer = app.screen.query_one("#shortcuts-hint", Static)
        assert "save" in str(footer.content)

        selection_list = app.screen.query_one(FileSelectionList)
        assert set(selection_list.selected) == {0, 2}


async def test_search_content_one_step_enter(mock_indexer: MagicMock):
    from torrra.app import TorrraApp
    from torrra._types import Indexer
    from torrra.widgets.search import SearchContent
    from torrra.widgets.data_table import AutoResizingDataTable

    mock_ti = create_mock_torrent_info()
    mock_indexer.search.return_value = [
        Torrent(
            magnet_uri="magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567",
            title="Search Result Torrent",
            size=1024,
            seeders=10,
            leechers=2,
            source="Mock",
        )
    ]

    app = TorrraApp(
        indexer=Indexer(name="jackett", url="http://mock.url", api_key="key"),
        use_cache=False,
        search_query="test query",
    )

    async with app.run_test() as pilot:
        await pilot.pause()
        table = app.screen.query_one(AutoResizingDataTable)
        # Select first row directly with enter
        await pilot.press("enter")
        await pilot.pause()

        # Should immediately open FileSelectionScreen in 1 step!
        assert isinstance(app.screen, FileSelectionScreen)


async def test_torrent_manager_file_priorities_persistence(tmp_path: Any, monkeypatch: pytest.MonkeyPatch):
    from torrra.core import db as db_module
    from torrra.core.torrent import TorrentManager

    temp_db = tmp_path / "test.db"
    monkeypatch.setattr(db_module, "DB_FILE", temp_db)
    monkeypatch.setattr(db_module, "DB_DIR", tmp_path)

    db_module.init_db()
    tm = TorrentManager()

    torrent = Torrent(
        magnet_uri="magnet:?xt=urn:btih:persisted_uri",
        title="Persisted Torrent",
        size=1000,
        seeders=5,
        leechers=1,
        source="Test",
        file_priorities=[4, 0, 4],
    )

    tm.add_torrent(torrent, file_priorities=[4, 0, 4])

    torrents = tm.get_all_torrents()
    assert len(torrents) == 1
    assert torrents[0]["file_priorities"] == [4, 0, 4]

    # Update priorities
    tm.update_torrent_file_priorities("magnet:?xt=urn:btih:persisted_uri", [0, 4, 0])
    updated_torrents = tm.get_all_torrents()
    assert updated_torrents[0]["file_priorities"] == [0, 4, 0]


async def test_download_manager_file_priorities():
    dm = get_download_manager()
    uri = "magnet:?xt=urn:btih:dm_test_prio"

    dm.set_file_priorities(uri, [4, 0, 4])
    assert dm.get_file_priorities(uri) == [4, 0, 4]


async def test_downloads_content_action_select_files(tmp_path: Any, monkeypatch: pytest.MonkeyPatch):
    from torrra.app import TorrraApp
    from torrra._types import Indexer
    from torrra.core import db as db_module
    from torrra.core.torrent import get_torrent_manager
    from torrra.widgets.downloads import DownloadsContent

    temp_db = tmp_path / "test.db"
    monkeypatch.setattr(db_module, "DB_FILE", temp_db)
    monkeypatch.setattr(db_module, "DB_DIR", tmp_path)

    db_module.init_db()
    tm = get_torrent_manager()
    tm.add_torrent(
        Torrent(
            magnet_uri="magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567",
            title="Downloads Test Torrent",
            size=1024,
            seeders=5,
            leechers=1,
            source="Mock",
            file_priorities=[4, 4],
        ),
        file_priorities=[4, 4],
    )

    app = TorrraApp(
        indexer=Indexer(name="jackett", url="http://mock.url", api_key="key"),
        use_cache=False,
        search_query="",
        show_downloads=True,
    )

    async with app.run_test() as pilot:
        await pilot.pause()
        downloads_content = app.screen.query_one(DownloadsContent)
        # Select first row
        downloads_content._selected_torrent = tm.get_all_torrents()[0]

        # Trigger select files action
        downloads_content.action_select_files()
        await pilot.pause()

        assert isinstance(app.screen, FileSelectionScreen)
        assert app.screen.is_edit_mode is True

