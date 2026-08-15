from textual import work
from textual.app import App

from torrra._types import TorrentFileStatus
from torrra.screens.file_manager import FileManagerScreen
from torrra.widgets.data_table import AutoResizingDataTable

STATUS = [
    TorrentFileStatus(index=0, path="readme.txt", size=10, downloaded=10, priority=1),
    TorrentFileStatus(index=1, path="video.mp4", size=20, downloaded=5, priority=0),
    TorrentFileStatus(index=2, path="subs/en.srt", size=5, downloaded=0, priority=1),
]


class _ScreenApp(App[None]):
    @work(exclusive=True)
    async def _open_and_wait(self, screen: FileManagerScreen) -> None:
        return await self.push_screen_wait(screen)


async def _load_status() -> list[TorrentFileStatus] | None:
    return STATUS


async def _open(app: App, pilot) -> FileManagerScreen:
    screen = FileManagerScreen("Test Torrent", _load_status)
    app._open_and_wait(screen)
    await pilot.pause()
    await pilot.pause()
    return screen


async def test_file_manager_lists_file_status():
    app = _ScreenApp()

    async with app.run_test() as pilot:
        screen = await _open(app, pilot)

        table = screen.query_one("#file_manager_table", AutoResizingDataTable)
        assert table.row_count == 3
        assert table.get_cell("0", "sel") == "\\[x]"
        assert table.get_cell("1", "sel") == "\\[ ]"
        assert table.get_cell("0", "done") == "100%"
        assert table.get_cell("1", "done") == "25%"
        assert table.get_cell("2", "done") == "0%"
        assert table.get_cell("1", "downloaded") == "5B"
        assert table.get_cell("2", "name") == "subs/en.srt"
        assert "selected 15.00 B (2 files)" in str(
            screen.query_one("#file_manager_header").content
        )


async def test_file_manager_toggle_on_and_apply_returns_selection():
    app = _ScreenApp()

    async with app.run_test() as pilot:
        worker = app._open_and_wait(FileManagerScreen("Test Torrent", _load_status))
        await pilot.pause()
        await pilot.pause()

        table = app.screen.query_one("#file_manager_table", AutoResizingDataTable)
        table.move_cursor(row=1)  # video.mp4 (currently deselected)
        await pilot.press("space")

        assert table.get_cell("1", "sel") == "\\[x]"
        assert "selected 35.00 B (3 files)" in str(
            app.screen.query_one("#file_manager_header").content
        )

        await pilot.click("#file_manager_apply")

        assert await worker.wait() == [0, 1, 2]


async def test_file_manager_toggle_off_and_apply_returns_selection():
    app = _ScreenApp()

    async with app.run_test() as pilot:
        worker = app._open_and_wait(FileManagerScreen("Test Torrent", _load_status))
        await pilot.pause()
        await pilot.pause()

        table = app.screen.query_one("#file_manager_table", AutoResizingDataTable)
        table.move_cursor(row=0)  # readme.txt (currently selected)
        await pilot.press("space")

        assert table.get_cell("0", "sel") == "\\[ ]"

        await pilot.click("#file_manager_apply")

        assert await worker.wait() == [2]


async def test_file_manager_escape_returns_none():
    app = _ScreenApp()

    async with app.run_test() as pilot:
        worker = app._open_and_wait(FileManagerScreen("Test Torrent", _load_status))
        await pilot.pause()
        await pilot.pause()

        await pilot.press("escape")

        assert await worker.wait() is None


async def test_file_manager_close_button_returns_none():
    app = _ScreenApp()

    async with app.run_test() as pilot:
        worker = app._open_and_wait(FileManagerScreen("Test Torrent", _load_status))
        await pilot.pause()
        await pilot.pause()

        await pilot.click("#file_manager_close")

        assert await worker.wait() is None


async def test_file_manager_empty_selection_blocked():
    async def _empty() -> list[TorrentFileStatus] | None:
        return [
            TorrentFileStatus(index=0, path="a.bin", size=10, downloaded=0, priority=0),
            TorrentFileStatus(index=1, path="b.bin", size=20, downloaded=0, priority=0),
        ]

    app = _ScreenApp()

    async with app.run_test() as pilot:
        worker = app._open_and_wait(FileManagerScreen("Test Torrent", _empty))
        await pilot.pause()
        await pilot.pause()

        await pilot.click("#file_manager_apply")
        await pilot.pause()

        # screen should still be open (no dismissal happened)
        assert app.screen is not None
        assert not worker.is_finished


async def test_file_manager_load_error_dismisses():
    def _raise() -> list[TorrentFileStatus] | None:
        raise RuntimeError("boom")

    app = _ScreenApp()

    async with app.run_test() as pilot:
        worker = app._open_and_wait(FileManagerScreen("Test Torrent", _raise))
        await pilot.pause()
        await pilot.pause()

        assert await worker.wait() is None


async def test_file_manager_loads_even_when_not_yet_mounted():
    # Regression: the load worker can run before Textual sets is_mounted (the
    # real app's event loop), which used to silently skip population forever.
    app = _ScreenApp()

    async with app.run_test() as pilot:
        worker = app._open_and_wait(FileManagerScreen("Test Torrent", _load_status))
        await pilot.pause()
        await pilot.pause()

        screen = app.screen
        screen._is_mounted = False
        await FileManagerScreen._load_data.__wrapped__(screen)

        table = screen.query_one("#file_manager_table", AutoResizingDataTable)
        assert table.row_count == 3
        assert not table.has_class("hidden")
        assert not worker.is_finished


async def test_file_manager_waiting_for_metadata_then_populates():
    calls = {"n": 0}

    async def _flaky() -> list[TorrentFileStatus] | None:
        calls["n"] += 1
        return None if calls["n"] == 1 else STATUS

    app = _ScreenApp()

    async with app.run_test() as pilot:
        worker = app._open_and_wait(FileManagerScreen("Test Torrent", _flaky))
        await pilot.pause()
        await pilot.pause()

        screen = app.screen
        table = screen.query_one("#file_manager_table", AutoResizingDataTable)
        loader = screen.query_one("#file_manager_loader")
        assert table.has_class("hidden")  # still waiting for metadata
        assert not loader.has_class("hidden")

        await screen._refresh()

        assert table.row_count == 3
        assert table.has_class("hidden") is False
        assert not worker.is_finished


async def test_file_manager_metadata_timeout_dismisses():
    async def _never() -> list[TorrentFileStatus] | None:
        return None

    app = _ScreenApp()

    async with app.run_test() as pilot:
        worker = app._open_and_wait(
            FileManagerScreen("Test Torrent", _never, metadata_timeout=0.0)
        )
        await pilot.pause()
        await pilot.pause()

        await app.screen._refresh()

        assert await worker.wait() is None


async def test_file_manager_refresh_error_keeps_table():
    calls = {"n": 0}

    async def _flaky() -> list[TorrentFileStatus] | None:
        calls["n"] += 1
        if calls["n"] == 1:
            return STATUS
        raise RuntimeError("refresh boom")

    app = _ScreenApp()

    async with app.run_test() as pilot:
        worker = app._open_and_wait(FileManagerScreen("Test Torrent", _flaky))
        await pilot.pause()
        await pilot.pause()

        table = app.screen.query_one("#file_manager_table", AutoResizingDataTable)
        assert table.row_count == 3

        await app.screen._refresh()

        assert table.row_count == 3
        assert not worker.is_finished
