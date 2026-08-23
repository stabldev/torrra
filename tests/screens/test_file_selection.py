from typing import Any
from unittest.mock import MagicMock

import pytest
from textual.app import App
from textual.widgets import Input, Static

from torrra._types import DownloadSelection, Torrent
from torrra.core.download import get_download_manager
from torrra.core.torrent import get_torrent_manager
from torrra.screens.file_selection import FileSelectionScreen, FileSelectionTree


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
        self.result: DownloadSelection | None | object = object()

    def on_mount(self) -> None:
        self.push_screen(self.screen_to_push, self._on_result)

    def _on_result(self, res: DownloadSelection | None) -> None:
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

        selection_tree = app.screen.query_one(FileSelectionTree)
        # All 3 files should be initially selected
        assert selection_tree.selected == {0, 1, 2}

        # Redundant root directory "Ubuntu/" should be removed from the tree
        labels = selection_tree.file_labels()
        assert labels[0].startswith("[x] ubuntu-24.04-desktop.iso")
        assert "Ubuntu/" not in labels[0]
        assert labels[1].startswith("[x] SHA256SUMS")
        assert labels[2].startswith("[x] README.md")

        stats = app.screen.query_one("#selection-stats", Static)
        assert "3/3" in str(stats.content)


async def test_file_selection_screen_strips_root_preserves_subdirs():
    mock_ti = MagicMock()
    mock_ti.name.return_value = "Series Pack"
    fs = MagicMock()
    fs.num_files.return_value = 3
    fs.file_flags.return_value = 0
    fs.file_path.side_effect = lambda i: [
        "Series Pack/Season 1/S01E01.mkv",
        "Series Pack/Season 2/S02E01.mkv",
        "Series Pack/info.nfo",
    ][i]
    fs.file_size.side_effect = lambda i: [1_000_000, 1_000_000, 500][i]
    ti_files = fs
    mock_ti.files.return_value = ti_files

    torrent = Torrent(
        magnet_uri="magnet:?xt=urn:btih:mockseries",
        title="Series Pack",
        size=2_000_500,
        seeders=5,
        leechers=1,
        source="Mock",
    )

    screen = FileSelectionScreen(torrent=torrent, torrent_info=mock_ti)
    app = DummyHostApp(screen)

    async with app.run_test() as pilot:
        await pilot.pause()
        selection_tree = app.screen.query_one(FileSelectionTree)
        labels = selection_tree.file_labels()
        assert labels[0].startswith("[x] S01E01.mkv")
        assert labels[1].startswith("[x] S02E01.mkv")
        assert labels[2].startswith("[x] info.nfo")

        folders = selection_tree.folder_labels()
        assert set(folders) == {"Season 1", "Season 2"}


async def test_file_selection_screen_filename_truncation_with_size():
    long_name = "Very.Long.Series.Title.2026.S01E01.1080p.BluRay.x265.10bit.DTS-HD.MA.7.1-GROUP.mkv"
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
        selection_tree = app.screen.query_one(FileSelectionTree)
        prompt_text = selection_tree.file_labels()[0]
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
        selection_tree = app.screen.query_one(FileSelectionTree)

        # Press 'n' for none
        await pilot.press("n")
        await pilot.pause()
        assert len(selection_tree.selected) == 0

        # Press 'a' for all
        await pilot.press("a")
        await pilot.pause()
        assert selection_tree.selected == {0, 1, 2}


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
        selection_tree = app.screen.query_one(FileSelectionTree)
        assert selection_tree.selected == {0}

        # Press 'i' to invert
        await pilot.press("i")
        await pilot.pause()
        assert selection_tree.selected == {1, 2}


async def test_file_selection_tree_expand_collapse_folder():
    mock_ti = MagicMock()
    mock_ti.name.return_value = "Series Pack"
    fs = MagicMock()
    fs.num_files.return_value = 3
    fs.file_flags.return_value = 0
    fs.file_path.side_effect = lambda i: [
        "Series Pack/Season 1/S01E01.mkv",
        "Series Pack/Season 2/S02E01.mkv",
        "Series Pack/info.nfo",
    ][i]
    fs.file_size.side_effect = lambda i: [1_000_000, 1_000_000, 500][i]
    mock_ti.files.return_value = fs

    torrent = Torrent(
        magnet_uri="magnet:?xt=urn:btih:mockseries",
        title="Series Pack",
        size=2_000_500,
        seeders=5,
        leechers=1,
        source="Mock",
    )

    screen = FileSelectionScreen(torrent=torrent, torrent_info=mock_ti)
    app = DummyHostApp(screen)

    async with app.run_test() as pilot:
        await pilot.pause()
        selection_tree = app.screen.query_one(FileSelectionTree)
        folders = selection_tree.folder_nodes()
        assert len(folders) == 2

        # Cursor starts on the first folder (Season 1), expanded by default
        assert selection_tree.cursor_node is folders[0]
        assert folders[0].is_expanded

        # 'right' on an already-expanded folder does nothing harmful
        await pilot.press("right")
        await pilot.pause()
        assert folders[0].is_expanded

        # 'left' collapses it, 'right' expands it again
        await pilot.press("left")
        await pilot.pause()
        assert folders[0].is_collapsed

        await pilot.press("right")
        await pilot.pause()
        assert folders[0].is_expanded


async def test_file_selection_tree_folder_toggle():
    mock_ti = MagicMock()
    mock_ti.name.return_value = "Series Pack"
    fs = MagicMock()
    fs.num_files.return_value = 3
    fs.file_flags.return_value = 0
    fs.file_path.side_effect = lambda i: [
        "Series Pack/Season 1/S01E01.mkv",
        "Series Pack/Season 1/S01E02.mkv",
        "Series Pack/info.nfo",
    ][i]
    fs.file_size.side_effect = lambda i: [1_000_000, 1_000_000, 500][i]
    mock_ti.files.return_value = fs

    torrent = Torrent(
        magnet_uri="magnet:?xt=urn:btih:mockseries",
        title="Series Pack",
        size=2_000_500,
        seeders=5,
        leechers=1,
        source="Mock",
    )

    screen = FileSelectionScreen(torrent=torrent, torrent_info=mock_ti)
    app = DummyHostApp(screen)

    async with app.run_test() as pilot:
        await pilot.pause()
        selection_tree = app.screen.query_one(FileSelectionTree)
        folder = selection_tree.folder_nodes()[0]
        assert folder.is_expanded

        # Deselect all, then space on the folder selects all its files only
        await pilot.press("n")
        await pilot.pause()
        await pilot.press("space")
        await pilot.pause()
        assert selection_tree.selected == {0, 1}

        # Space again on the folder deselects its subtree
        await pilot.press("space")
        await pilot.pause()
        assert selection_tree.selected == set()

        # Folder label reflects the aggregate selection
        folder_label = selection_tree.folder_labels()["Season 1"]
        assert "[ ]" in folder_label and "0/2" in folder_label


async def test_file_selection_tree_nested_folder_toggle():
    mock_ti = MagicMock()
    mock_ti.name.return_value = "Deep Series Pack"
    fs = MagicMock()
    fs.num_files.return_value = 3
    fs.file_flags.return_value = 0
    fs.file_path.side_effect = lambda i: [
        "Deep Series Pack/Season 1/Extras/behind_the_scenes.mp4",
        "Deep Series Pack/Season 1/S01E01.mkv",
        "Deep Series Pack/info.nfo",
    ][i]
    fs.file_size.side_effect = lambda i: [500_000, 1_000_000, 500][i]
    mock_ti.files.return_value = fs

    torrent = Torrent(
        magnet_uri="magnet:?xt=urn:btih:mockdeep",
        title="Deep Series Pack",
        size=1_500_500,
        seeders=5,
        leechers=1,
        source="Mock",
    )

    screen = FileSelectionScreen(torrent=torrent, torrent_info=mock_ti)
    app = DummyHostApp(screen)

    async with app.run_test() as pilot:
        await pilot.pause()
        selection_tree = app.screen.query_one(FileSelectionTree)

        # Initially all selected
        assert "[x] Season 1 (2/2)" in selection_tree.folder_labels()["Season 1"]
        assert "[x] Extras (1/1)" in selection_tree.folder_labels()["Extras"]

        # Deselect Season 1 subtree
        await pilot.press("space")
        await pilot.pause()

        # Both Season 1 and nested Extras should update properly
        assert "[ ] Season 1 (0/2)" in selection_tree.folder_labels()["Season 1"]
        assert "[ ] Extras (0/1)" in selection_tree.folder_labels()["Extras"]


async def test_file_selection_tree_vim_navigation_and_parent_jump():
    mock_ti = MagicMock()
    mock_ti.name.return_value = "Series Pack"
    fs = MagicMock()
    fs.num_files.return_value = 2
    fs.file_flags.return_value = 0
    fs.file_path.side_effect = lambda i: [
        "Series Pack/Season 1/S01E01.mkv",
        "Series Pack/info.nfo",
    ][i]
    fs.file_size.side_effect = lambda i: [1_000_000, 500][i]
    mock_ti.files.return_value = fs

    torrent = Torrent(
        magnet_uri="magnet:?xt=urn:btih:mockseries",
        title="Series Pack",
        size=1_000_500,
        seeders=5,
        leechers=1,
        source="Mock",
    )

    screen = FileSelectionScreen(torrent=torrent, torrent_info=mock_ti)
    app = DummyHostApp(screen)

    async with app.run_test() as pilot:
        await pilot.pause()
        selection_tree = app.screen.query_one(FileSelectionTree)
        folder = selection_tree.folder_nodes()[0]
        assert selection_tree.cursor_node is folder
        assert folder.is_expanded

        # 'h' collapses the folder
        await pilot.press("h")
        await pilot.pause()
        assert folder.is_collapsed

        # 'l' expands the folder
        await pilot.press("l")
        await pilot.pause()
        assert folder.is_expanded

        # Move down to child using 'j'
        await pilot.press("j")
        await pilot.pause()
        assert selection_tree.cursor_node is not folder
        assert selection_tree.cursor_node.parent is folder

        # 'h' or 'left' on a child moves cursor back to parent folder
        await pilot.press("h")
        await pilot.pause()
        assert selection_tree.cursor_node is folder


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

        selection_tree = app.screen.query_one(FileSelectionTree)
        assert selection_tree.selected == {0}

        # Confirm with enter
        await pilot.press("enter")
        await pilot.pause()

        # Returned priorities: file 0 has 4, files 1 and 2 have 0
        assert isinstance(app.result, DownloadSelection)
        assert app.result.file_priorities == [4, 0, 0]
        assert app.result.save_path is None


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
        assert isinstance(app.result, DownloadSelection)
        assert app.result.file_priorities is None
        assert app.result.save_path is None


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


async def test_file_selection_screen_returns_custom_save_path(tmp_path: Any):
    custom_path = tmp_path / "custom-downloads"
    screen = FileSelectionScreen(
        torrent=Torrent(
            magnet_uri="magnet:?xt=urn:btih:custompath",
            title="Custom Path",
            size=100,
            seeders=1,
            leechers=0,
            source="Mock",
        ),
        torrent_info=create_mock_torrent_info(),
        initial_save_path=str(custom_path),
    )
    app = DummyHostApp(screen)

    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.screen.query_one("#save-path", Input).value == str(custom_path)

        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.result, DownloadSelection)
        assert app.result.save_path == str(custom_path)
        assert custom_path.is_dir()


async def test_file_selection_screen_prefills_global_path_as_fallback(
    mock_config: Any, tmp_path: Any
):
    default_path = tmp_path / "default-downloads"
    mock_config.set("general.download_path", str(default_path))
    screen = FileSelectionScreen(
        torrent=Torrent(
            magnet_uri="magnet:?xt=urn:btih:defaultpath",
            title="Default Path",
            size=100,
            seeders=1,
            leechers=0,
            source="Mock",
        ),
        torrent_info=create_mock_torrent_info(),
    )
    app = DummyHostApp(screen)

    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.screen.query_one("#save-path", Input).value == str(default_path)

        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.result, DownloadSelection)
        assert app.result.save_path is None
        assert default_path.is_dir()


async def test_file_selection_screen_rejects_relative_save_path():
    screen = FileSelectionScreen(
        torrent=Torrent(
            magnet_uri="magnet:?xt=urn:btih:relativepath",
            title="Relative Path",
            size=100,
            seeders=1,
            leechers=0,
            source="Mock",
        ),
        torrent_info=create_mock_torrent_info(),
    )
    app = DummyHostApp(screen)
    initial_result = app.result

    async with app.run_test() as pilot:
        await pilot.pause()
        app.screen.query_one("#save-path", Input).value = "relative/path"
        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.screen, FileSelectionScreen)
        assert app.result is initial_result


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
        assert "Ubuntu 24.04 Pack" in str(
            app.screen.query_one("#torrent-name", Static).content
        )
        footer = app.screen.query_one("#shortcuts-hint", Static)
        assert "save" in str(footer.content)

        selection_tree = app.screen.query_one(FileSelectionTree)
        assert selection_tree.selected == {0, 2}


async def test_search_content_one_step_enter(mock_indexer: MagicMock, tmp_path: Any):
    from torrra._types import Indexer
    from torrra.app import TorrraApp
    from torrra.widgets.data_table import AutoResizingDataTable

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
        assert app.screen.query_one(AutoResizingDataTable) is not None
        # Select first row directly with enter
        await pilot.press("enter")
        await pilot.pause()

        # Should immediately open FileSelectionScreen in 1 step!
        assert isinstance(app.screen, FileSelectionScreen)
        custom_path = tmp_path / "search-downloads"
        app.screen.query_one("#save-path", Input).value = str(custom_path)

        # Confirm on FileSelectionScreen with enter
        await pilot.press("enter")
        await pilot.pause()

        # Should be on HomeScreen with downloads view, NOT a second FileSelectionScreen!
        from torrra.screens.home import HomeScreen

        assert isinstance(app.screen, HomeScreen)
        stored_torrent = get_torrent_manager().get_all_torrents()[0]
        assert stored_torrent["save_path"] == str(custom_path)


async def test_torrent_manager_file_priorities_persistence(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
):
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


async def test_downloads_content_action_select_files(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
):
    from torrra._types import Indexer
    from torrra.app import TorrraApp
    from torrra.core import db as db_module
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


async def test_direct_download_modal_shown_on_downloads_section(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
):
    from textual.widgets import ContentSwitcher

    from torrra._types import Indexer
    from torrra.app import TorrraApp
    from torrra.core import db as db_module
    from torrra.screens.home import HomeScreen
    from torrra.widgets.downloads import DownloadsContent
    from torrra.widgets.sidebar import Sidebar

    temp_db = tmp_path / "test.db"
    monkeypatch.setattr(db_module, "DB_FILE", temp_db)
    monkeypatch.setattr(db_module, "DB_DIR", tmp_path)
    db_module.init_db()

    magnet = "magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567&dn=Direct+Download+Test"
    app = TorrraApp(
        indexer=Indexer(name="jackett", url="http://mock.url", api_key="key"),
        use_cache=False,
        search_query="",
        direct_download=magnet,
        direct_save_path=str(tmp_path / "direct-downloads"),
    )

    async with app.run_test() as pilot:
        await pilot.pause()
        # Verify FileSelectionScreen modal is pushed on top
        assert isinstance(app.screen, FileSelectionScreen)

        # Verify underlying screen is HomeScreen with downloads section active
        home_screen = next(s for s in app.screen_stack if isinstance(s, HomeScreen))
        assert (
            home_screen.query_one("#content_switcher", ContentSwitcher).current
            == "downloads_content"
        )
        sidebar = home_screen.query_one("#sidebar", Sidebar)
        assert sidebar.cursor_node is not None
        assert sidebar.cursor_node.data is not None
        assert sidebar.cursor_node.data.get("group_id") == "downloads_content"

        # Confirm download with enter (skip metadata / download all)
        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.screen, HomeScreen)
        tm = get_torrent_manager()
        assert len(tm.get_all_torrents()) == 1
        assert tm.get_all_torrents()[0]["magnet_uri"] == magnet
        assert tm.get_all_torrents()[0]["save_path"] == str(
            tmp_path / "direct-downloads"
        )

        downloads_content = app.screen.query_one(DownloadsContent)
        assert downloads_content._table.row_count == 1


async def test_direct_download_modal_cancel(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
):
    from textual.widgets import ContentSwitcher

    from torrra._types import Indexer
    from torrra.app import TorrraApp
    from torrra.core import db as db_module
    from torrra.screens.home import HomeScreen
    from torrra.widgets.sidebar import Sidebar

    temp_db = tmp_path / "test.db"
    monkeypatch.setattr(db_module, "DB_FILE", temp_db)
    monkeypatch.setattr(db_module, "DB_DIR", tmp_path)
    db_module.init_db()

    magnet = "magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567&dn=Direct+Download+Test"
    app = TorrraApp(
        indexer=Indexer(name="jackett", url="http://mock.url", api_key="key"),
        use_cache=False,
        search_query="",
        direct_download=magnet,
    )

    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, FileSelectionScreen)

        # Cancel with escape
        await pilot.press("escape")
        await pilot.pause()

        assert isinstance(app.screen, HomeScreen)
        tm = get_torrent_manager()
        assert len(tm.get_all_torrents()) == 0

        home_screen = app.screen
        assert (
            home_screen.query_one("#content_switcher", ContentSwitcher).current
            == "downloads_content"
        )
        sidebar = home_screen.query_one("#sidebar", Sidebar)
        assert sidebar.cursor_node is not None
        assert sidebar.cursor_node.data.get("group_id") == "downloads_content"


async def test_home_restores_persisted_custom_save_path(tmp_path: Any):
    from torrra.app import TorrraApp

    magnet = "magnet:?xt=urn:btih:89abcdef0123456789abcdef0123456789abcdef"
    destination = tmp_path / "persisted-downloads"
    destination.mkdir()
    tm = get_torrent_manager()
    tm.add_torrent(
        Torrent(
            magnet_uri=magnet,
            title="Persisted Path",
            size=1024,
            seeders=0,
            leechers=0,
            source="Test",
        ),
        save_path=str(destination),
    )

    app = TorrraApp(
        indexer=None,
        use_cache=False,
        search_query=None,
        show_downloads=True,
    )

    async with app.run_test() as pilot:
        await pilot.pause()

        handle = get_download_manager().torrents[magnet]
        assert handle.status().save_path == str(destination)


async def test_home_does_not_recreate_missing_custom_save_path(tmp_path: Any):
    from torrra.app import TorrraApp

    magnet = "magnet:?xt=urn:btih:fedcba9876543210fedcba9876543210fedcba98"
    destination = tmp_path / "unmounted-downloads"
    tm = get_torrent_manager()
    tm.add_torrent(
        Torrent(
            magnet_uri=magnet,
            title="Unmounted Path",
            size=1024,
            seeders=0,
            leechers=0,
            source="Test",
        ),
        save_path=str(destination),
    )

    app = TorrraApp(
        indexer=None,
        use_cache=False,
        search_query=None,
        show_downloads=True,
    )

    async with app.run_test() as pilot:
        await pilot.pause()

        assert magnet not in get_download_manager().torrents
        assert not destination.exists()
