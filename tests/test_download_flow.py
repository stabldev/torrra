from unittest.mock import AsyncMock, MagicMock, patch

from torrra._types import TorrentFile
from torrra.screens.file_selection import DOWNLOAD_ALL
from torrra.utils.download_flow import start_download


async def test_start_download_download_all_without_metadata_skips_prioritize():
    dm = MagicMock()
    dm.get_files.return_value = None
    dm.get_metadata.return_value = None
    worker = MagicMock()
    worker.wait = AsyncMock(return_value=DOWNLOAD_ALL)
    app = MagicMock()
    app._run_file_selection.return_value = worker

    config = MagicMock()
    config.get.return_value = True

    with (
        patch("torrra.utils.download_flow.get_download_manager", return_value=dm),
        patch("torrra.utils.download_flow.get_config", return_value=config),
    ):
        result = await start_download(
            app,
            magnet_uri="magnet:?xt=urn:btih:abc",
            title="Example",
            source="jackett",
        )

    assert result is not None
    dm.prioritize_files.assert_not_called()
    dm.resume_torrent.assert_called_once_with("magnet:?xt=urn:btih:abc")


async def test_start_download_download_all_with_metadata_prioritizes_everything():
    dm = MagicMock()
    dm.get_files.return_value = [
        TorrentFile(index=0, path="a.txt", size=10),
        TorrentFile(index=1, path="b.bin", size=20),
    ]
    dm.get_metadata.return_value = None
    worker = MagicMock()
    worker.wait = AsyncMock(return_value=DOWNLOAD_ALL)
    app = MagicMock()
    app._run_file_selection.return_value = worker

    config = MagicMock()
    config.get.return_value = True

    with (
        patch("torrra.utils.download_flow.get_download_manager", return_value=dm),
        patch("torrra.utils.download_flow.get_config", return_value=config),
    ):
        result = await start_download(
            app,
            magnet_uri="magnet:?xt=urn:btih:abc",
            title="Example",
            source="jackett",
        )

    assert result is not None
    dm.prioritize_files.assert_called_once_with("magnet:?xt=urn:btih:abc", {0, 1})
    dm.resume_torrent.assert_called_once_with("magnet:?xt=urn:btih:abc")


async def test_start_download_cancel_removes_torrent():
    dm = MagicMock()
    dm.get_metadata.return_value = None
    worker = MagicMock()
    worker.wait = AsyncMock(return_value=None)
    app = MagicMock()
    app._run_file_selection.return_value = worker

    config = MagicMock()
    config.get.return_value = True

    with (
        patch("torrra.utils.download_flow.get_download_manager", return_value=dm),
        patch("torrra.utils.download_flow.get_config", return_value=config),
    ):
        result = await start_download(
            app,
            magnet_uri="magnet:?xt=urn:btih:abc",
            title="Example",
            source="jackett",
        )

    assert result is None
    dm.remove_torrent.assert_called_once_with("magnet:?xt=urn:btih:abc")
    dm.resume_torrent.assert_not_called()
    dm.prioritize_files.assert_not_called()


async def test_start_download_selection_records_selected_files():
    dm = MagicMock()
    dm.prioritize_files.return_value = True
    dm.get_metadata.return_value = None
    worker = MagicMock()
    worker.wait = AsyncMock(return_value=[0, 2])
    app = MagicMock()
    app._run_file_selection.return_value = worker

    config = MagicMock()
    config.get.return_value = True

    with (
        patch("torrra.utils.download_flow.get_download_manager", return_value=dm),
        patch("torrra.utils.download_flow.get_config", return_value=config),
    ):
        result = await start_download(
            app,
            magnet_uri="magnet:?xt=urn:btih:abc",
            title="Example",
            source="jackett",
        )

    assert result is not None
    assert result.selected_files == [0, 2]
    dm.prioritize_files.assert_called_once_with("magnet:?xt=urn:btih:abc", {0, 2})
    dm.resume_torrent.assert_called_once_with("magnet:?xt=urn:btih:abc")


async def test_start_download_download_all_has_no_selected_files():
    dm = MagicMock()
    dm.get_files.return_value = None
    dm.get_metadata.return_value = None
    worker = MagicMock()
    worker.wait = AsyncMock(return_value=DOWNLOAD_ALL)
    app = MagicMock()
    app._run_file_selection.return_value = worker

    config = MagicMock()
    config.get.return_value = True

    with (
        patch("torrra.utils.download_flow.get_download_manager", return_value=dm),
        patch("torrra.utils.download_flow.get_config", return_value=config),
    ):
        result = await start_download(
            app,
            magnet_uri="magnet:?xt=urn:btih:abc",
            title="Example",
            source="jackett",
        )

    assert result is not None
    assert result.selected_files is None


async def test_start_download_prioritize_failure_removes_without_resume():
    dm = MagicMock()
    dm.prioritize_files.return_value = False
    worker = MagicMock()
    worker.wait = AsyncMock(return_value=[0])
    app = MagicMock()
    app._run_file_selection.return_value = worker

    config = MagicMock()
    config.get.return_value = True

    with (
        patch("torrra.utils.download_flow.get_download_manager", return_value=dm),
        patch("torrra.utils.download_flow.get_config", return_value=config),
    ):
        result = await start_download(
            app,
            magnet_uri="magnet:?xt=urn:btih:abc",
            title="Example",
            source="jackett",
        )

    assert result is None
    dm.remove_torrent.assert_called_once_with("magnet:?xt=urn:btih:abc")
    dm.resume_torrent.assert_not_called()
    app.notify.assert_called_once()
