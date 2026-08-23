from typing import Any
from unittest.mock import MagicMock

from textual.pilot import Pilot

from torrra._types import Torrent
from torrra.core.config import Config
from torrra.screens.file_selection import FileSelectionScreen


def test_home_screen_snapshot(
    app_factory: Any,
    mock_indexer: MagicMock,
    mock_config: Config,
    snap_compare: Any,
):
    # mock_config keeps sort/filter defaults hermetic, so the snapshot
    # doesn't depend on the developer's real config.toml
    # return mock torrents as result
    mock_indexer.search.return_value = [
        Torrent(
            magnet_uri="magnet:?xt=urn:btih:arch_new",
            title="Arch Linux 2025.11.01",
            size=1073741824,
            seeders=850,
            leechers=50,
            source="LinuxTacker",
        ),
        Torrent(
            magnet_uri="magnet:?xt=urn:btih:arch_old",
            title="Arch Linux 2024.01.01",
            size=838860800,
            seeders=5,
            leechers=15,
            source="LinuxTacker",
        ),
    ]

    async def run_before(pilot: Pilot[Any]):
        await pilot.pause()

    app = app_factory("arch linux iso")
    app.theme = "textual-dark"  # default theme
    assert snap_compare(app, run_before=run_before)


def test_welcome_screen_snapshot(app_factory: Any, snap_compare: Any):
    async def run_before(pilot: Pilot[Any]):
        await pilot.press(*list("arch linux iso"))
        await pilot.pause()

    app = app_factory()
    app.theme = "textual-dark"  # default theme
    assert snap_compare(app, run_before=run_before)


def test_theme_selector_screen_snapshot(app_factory: Any, snap_compare: Any):
    async def run_before(pilot: Pilot[Any]):
        await pilot.press("ctrl+t")
        await pilot.pause()

    app = app_factory()
    app.theme = "textual-dark"  # default theme
    assert snap_compare(app, run_before=run_before)


def test_sort_selector_screen_snapshot(
    app_factory: Any,
    mock_indexer: MagicMock,
    mock_config: Config,
    snap_compare: Any,
):
    mock_indexer.search.return_value = [
        Torrent(
            magnet_uri="magnet:?xt=urn:btih:arch_new",
            title="Arch Linux 2025.11.01",
            size=1073741824,
            seeders=850,
            leechers=50,
            source="LinuxTacker",
        ),
    ]

    async def run_before(pilot: Pilot[Any]):
        await pilot.pause()
        await pilot.press("s")
        await pilot.pause()

    app = app_factory("arch linux iso")
    app.theme = "textual-dark"  # default theme
    assert snap_compare(app, run_before=run_before)


def test_help_screen_snapshot(app_factory: Any, snap_compare: Any):
    # the other help tests assert content but not layout, and the panel is
    # sized to fit its rows, so this is what catches a row wrapping or a
    # section getting pushed out of view when a shortcut is added.
    # sized larger than the other snapshots deliberately: the full list needs
    # ~40 rows and the panel is capped at 80% of the screen, so anything
    # shorter than 50 clips the bottom sections and a regression down there
    # would go unseen. grow this if SHORTCUTS grows.
    async def run_before(pilot: Pilot[Any]):
        pilot.app.screen.set_focus(None)  # "?" is suppressed while an Input has focus
        await pilot.press("question_mark")
        await pilot.pause()

    app = app_factory()
    app.theme = "textual-dark"  # default theme
    assert snap_compare(app, run_before=run_before, terminal_size=(90, 50))


def test_file_selection_screen_snapshot(
    app_factory: Any,
    mock_config: Config,
    snap_compare: Any,
):
    torrent_info = MagicMock()
    torrent_info.name.return_value = "Linux Images"
    files = MagicMock()
    files.num_files.return_value = 2
    files.file_flags.return_value = 0
    files.file_path.side_effect = [
        "Linux Images/linux.iso",
        "Linux Images/checksums.txt",
    ]
    files.file_size.side_effect = [2_000_000_000, 1024]
    torrent_info.files.return_value = files

    async def run_before(pilot: Pilot[Any]):
        pilot.app.push_screen(
            FileSelectionScreen(
                torrent=Torrent(
                    magnet_uri="magnet:?xt=urn:btih:snapshot",
                    title="Linux Images",
                    size=2_000_001_024,
                    seeders=10,
                    leechers=1,
                    source="Snapshot",
                ),
                torrent_info=torrent_info,
            )
        )
        await pilot.pause()

    app = app_factory()
    app.theme = "textual-dark"
    assert snap_compare(app, run_before=run_before, terminal_size=(90, 30))
