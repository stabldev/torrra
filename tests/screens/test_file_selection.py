import asyncio

from textual import work
from textual.app import App

from torrra._types import TorrentFile
from torrra.screens.file_selection import DOWNLOAD_ALL, FileSelectionScreen
from torrra.widgets.file_tree import FileTree


class _ScreenApp(App[None]):
    @work(exclusive=True)
    async def _open_and_wait(self, screen: FileSelectionScreen) -> None:
        return await self.push_screen_wait(screen)


FILES = [
    TorrentFile(index=0, path="readme.txt", size=10),
    TorrentFile(index=1, path="video.mp4", size=20),
    TorrentFile(index=2, path="subs/en.srt", size=5),
]


async def _load_files() -> list[TorrentFile] | None:
    return FILES


async def test_file_selection_screen_lists_files():
    app = _ScreenApp()
    screen = FileSelectionScreen("Test Torrent", _load_files)

    async with app.run_test() as pilot:
        await pilot.app.push_screen(screen)
        await pilot.pause()
        await pilot.pause()

        tree = screen.query_one("#file_selection_tree", FileTree)
        assert not tree.has_class("hidden")
        assert len(tree._file_nodes) == 3
        assert "3 files" in str(screen.query_one("#file_selection_header").content)


async def test_file_selection_confirm_returns_selected_indices():
    app = _ScreenApp()
    screen = FileSelectionScreen("Test Torrent", _load_files)

    async with app.run_test() as pilot:
        worker = app._open_and_wait(screen)
        await pilot.pause()
        await pilot.pause()

        await pilot.press("j", "space")  # deselect video.mp4
        await pilot.click("#download_button")

        result = await worker.wait()
        assert result == [0, 2]


async def test_file_selection_cancel_returns_none():
    app = _ScreenApp()
    screen = FileSelectionScreen("Test Torrent", _load_files)

    async with app.run_test() as pilot:
        worker = app._open_and_wait(screen)
        await pilot.pause()
        await pilot.pause()

        await pilot.click("#cancel_button")

        assert await worker.wait() is None


async def test_file_selection_escape_downloads_all():
    app = _ScreenApp()
    screen = FileSelectionScreen("Test Torrent", _load_files)

    async with app.run_test() as pilot:
        worker = app._open_and_wait(screen)
        await pilot.pause()
        await pilot.pause()

        await pilot.press("escape")

        assert await worker.wait() == DOWNLOAD_ALL


async def test_file_selection_escape_during_loading():
    async def _slow_load() -> list[TorrentFile] | None:
        await asyncio.sleep(5)
        return FILES

    app = _ScreenApp()
    screen = FileSelectionScreen("Test Torrent", _slow_load)

    async with app.run_test() as pilot:
        worker = app._open_and_wait(screen)
        await pilot.pause()

        await pilot.press("escape")

        assert await worker.wait() == DOWNLOAD_ALL
        assert screen._load_worker.is_cancelled


async def test_file_selection_directory_toggle_selects_descendants():
    app = _ScreenApp()
    screen = FileSelectionScreen("Test Torrent", _load_files)

    async with app.run_test() as pilot:
        app._open_and_wait(screen)
        await pilot.pause()
        await pilot.pause()

        tree = screen.query_one("#file_selection_tree", FileTree)
        await pilot.press("j", "j")  # cursor to subs/ directory node
        await pilot.press("space")  # deselect all descendants (en.srt)

        assert tree.selected_indices() == [0, 1]

        await pilot.press("space")  # re-select all descendants

        assert tree.selected_indices() == [0, 1, 2]


async def test_file_selection_blocks_empty_selection():
    app = _ScreenApp()
    screen = FileSelectionScreen("Test Torrent", _load_files)

    async with app.run_test() as pilot:
        worker = app._open_and_wait(screen)
        await pilot.pause()
        await pilot.pause()

        await pilot.click("#select_none_button")
        await pilot.pause()
        await pilot.click("#download_button")

        # screen should still be open (no dismissal happened)
        assert screen.is_mounted
        assert not worker.is_finished
        assert app.screen is screen


async def test_file_selection_tree_shows_markers():
    app = _ScreenApp()
    screen = FileSelectionScreen("Test Torrent", _load_files)

    async with app.run_test() as pilot:
        app._open_and_wait(screen)
        await pilot.pause()
        await pilot.pause()

        tree = screen.query_one("#file_selection_tree", FileTree)
        assert tree._file_nodes[0].label.plain.startswith("[x] readme.txt")
        assert tree._file_nodes[1].label.plain.startswith("[x] video.mp4")

        await pilot.press("j", "space")  # deselect video.mp4

        assert tree._file_nodes[1].label.plain.startswith("[ ] video.mp4")
        assert tree._file_nodes[0].label.plain.startswith("[x] readme.txt")


async def test_file_selection_directory_markers():
    async def _load_dir_files() -> list[TorrentFile] | None:
        return [
            TorrentFile(index=0, path="readme.txt", size=10),
            TorrentFile(index=1, path="movies/a.mp4", size=20),
            TorrentFile(index=2, path="movies/b.mp4", size=5),
        ]

    app = _ScreenApp()
    screen = FileSelectionScreen("Test Torrent", _load_dir_files)

    async with app.run_test() as pilot:
        app._open_and_wait(screen)
        await pilot.pause()
        await pilot.pause()

        tree = screen.query_one("#file_selection_tree", FileTree)
        dir_node = tree._dir_nodes[("movies",)]
        assert dir_node.label.plain.startswith("[x] movies/")

        await pilot.press("j", "space")  # toggle movies/ dir off (all deselected)
        assert dir_node.label.plain.startswith("[ ] movies/")
        assert tree._file_nodes[1].label.plain.startswith("[ ] a.mp4")
        assert tree._file_nodes[2].label.plain.startswith("[ ] b.mp4")

        await pilot.press("space")  # re-select all descendants
        assert dir_node.label.plain.startswith("[x] movies/")

        await pilot.press("j", "space")  # deselect only a.mp4 (partial)
        assert dir_node.label.plain.startswith("[-] movies/")


async def test_file_selection_header_shows_selected_size():
    app = _ScreenApp()
    screen = FileSelectionScreen("Test Torrent", _load_files)

    async with app.run_test() as pilot:
        app._open_and_wait(screen)
        await pilot.pause()
        await pilot.pause()

        header = screen.query_one("#file_selection_header")
        assert "selected 35.00 B (3 files)" in str(header.content)

        await pilot.press("j", "space")  # deselect video.mp4 (20 B)

        assert "selected 15.00 B (2 files)" in str(header.content)

        await pilot.press("space")  # re-select video.mp4

        assert "selected 35.00 B (3 files)" in str(header.content)


async def test_file_selection_tree_expand_collapse():
    app = _ScreenApp()
    screen = FileSelectionScreen("Test Torrent", _load_files)

    async with app.run_test() as pilot:
        app._open_and_wait(screen)
        await pilot.pause()
        await pilot.pause()

        tree = screen.query_one("#file_selection_tree", FileTree)
        dir_node = tree._dir_nodes[("subs",)]
        assert dir_node.is_expanded

        await pilot.press("j", "j")  # cursor to subs/ directory node
        await pilot.press("left")  # collapse

        assert not dir_node.is_expanded

        await pilot.press("right")  # expand

        assert dir_node.is_expanded


async def test_file_selection_metadata_failure_dismisses():
    async def _fail() -> list[TorrentFile] | None:
        return None

    app = _ScreenApp()
    screen = FileSelectionScreen("Test Torrent", _fail)

    async with app.run_test() as pilot:
        worker = app._open_and_wait(screen)
        await pilot.pause()

        assert await worker.wait() is None
