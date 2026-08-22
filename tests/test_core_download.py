from typing import Any

import libtorrent as lt
import pytest

from torrra._types import TorrentStatus
from torrra.core.download import DownloadManager


def test_state_text_stalled_and_downloading():
    dm = DownloadManager()

    # Stalled when downloading and down_speed is 0
    stalled_status: TorrentStatus = {
        "state": lt.torrent_status.states.downloading,
        "progress": 50.0,
        "down_speed": 0.0,
        "up_speed": 0.0,
        "seeders": 0,
        "leechers": 0,
        "is_paused": False,
        "eta": None,
        "is_seeding": False,
    }
    assert dm.get_torrent_state_text(stalled_status) == "Stalled"
    assert dm.get_torrent_state_text(stalled_status, short=True) == "STAL"

    # Downloading when downloading and down_speed > 0
    down_status: TorrentStatus = {
        "state": lt.torrent_status.states.downloading,
        "progress": 50.0,
        "down_speed": 1024.0,
        "up_speed": 512.0,
        "seeders": 5,
        "leechers": 10,
        "is_paused": False,
        "eta": 100.0,
        "is_seeding": False,
    }
    assert dm.get_torrent_state_text(down_status) == "Downloading"
    assert dm.get_torrent_state_text(down_status, short=True) == "DOWN"


def test_state_text_missing_files_and_error():
    dm = DownloadManager()

    # Missing files flag
    missing_status: TorrentStatus = {
        "state": lt.torrent_status.states.seeding,
        "progress": 100.0,
        "down_speed": 0.0,
        "up_speed": 0.0,
        "seeders": 0,
        "leechers": 0,
        "is_paused": False,
        "eta": None,
        "is_seeding": True,
        "is_missing_files": True,
    }
    assert dm.get_torrent_state_text(missing_status) == "Missing Files"
    assert dm.get_torrent_state_text(missing_status, short=True) == "MISS"

    # Missing file through error message
    missing_err_status: TorrentStatus = {
        "state": lt.torrent_status.states.downloading,
        "progress": 10.0,
        "down_speed": 0.0,
        "up_speed": 0.0,
        "seeders": 0,
        "leechers": 0,
        "is_paused": False,
        "eta": None,
        "is_seeding": False,
        "error": "No such file or directory",
        "error_file": 0,
    }
    assert dm.get_torrent_state_text(missing_err_status) == "Missing Files"
    assert dm.get_torrent_state_text(missing_err_status, short=True) == "MISS"

    # Generic error
    error_status: TorrentStatus = {
        "state": lt.torrent_status.states.downloading,
        "progress": 10.0,
        "down_speed": 0.0,
        "up_speed": 0.0,
        "seeders": 0,
        "leechers": 0,
        "is_paused": False,
        "eta": None,
        "is_seeding": False,
        "error": "Permission denied",
        "error_file": -1,
    }
    assert dm.get_torrent_state_text(error_status) == "Error"
    assert dm.get_torrent_state_text(error_status, short=True) == "ERRO"


def test_state_text_checking():
    dm = DownloadManager()

    checking_status: TorrentStatus = {
        "state": lt.torrent_status.states.checking_files,
        "progress": 30.0,
        "down_speed": 0.0,
        "up_speed": 0.0,
        "seeders": 0,
        "leechers": 0,
        "is_paused": False,
        "eta": None,
        "is_seeding": False,
    }
    assert dm.get_torrent_state_text(checking_status) == "Checking"
    assert dm.get_torrent_state_text(checking_status, short=True) == "CHCK"

    resume_status: TorrentStatus = {
        "state": lt.torrent_status.states.checking_resume_data,
        "progress": 0.0,
        "down_speed": 0.0,
        "up_speed": 0.0,
        "seeders": 0,
        "leechers": 0,
        "is_paused": False,
        "eta": None,
        "is_seeding": False,
    }
    assert dm.get_torrent_state_text(resume_status) == "Checking"
    assert dm.get_torrent_state_text(resume_status, short=True) == "CHCK"


def test_state_text_paused_and_queued():
    dm = DownloadManager()

    paused_status: TorrentStatus = {
        "state": lt.torrent_status.states.downloading,
        "progress": 50.0,
        "down_speed": 0.0,
        "up_speed": 0.0,
        "seeders": 0,
        "leechers": 0,
        "is_paused": True,
        "is_queued": False,
        "eta": None,
        "is_seeding": False,
    }
    assert dm.get_torrent_state_text(paused_status) == "Paused"
    assert dm.get_torrent_state_text(paused_status, short=True) == "PAUS"

    queued_status: TorrentStatus = {
        "state": lt.torrent_status.states.downloading,
        "progress": 50.0,
        "down_speed": 0.0,
        "up_speed": 0.0,
        "seeders": 0,
        "leechers": 0,
        "is_paused": True,
        "is_queued": True,
        "eta": None,
        "is_seeding": False,
    }
    assert dm.get_torrent_state_text(queued_status) == "Queued"
    assert dm.get_torrent_state_text(queued_status, short=True) == "QUEU"


def test_state_text_seeding_completed_fetching():
    dm = DownloadManager()

    seeding_status: TorrentStatus = {
        "state": lt.torrent_status.states.seeding,
        "progress": 100.0,
        "down_speed": 0.0,
        "up_speed": 1024.0,
        "seeders": 0,
        "leechers": 2,
        "is_paused": False,
        "eta": None,
        "is_seeding": True,
    }
    assert dm.get_torrent_state_text(seeding_status) == "Seeding"
    assert dm.get_torrent_state_text(seeding_status, short=True) == "SEED"

    completed_status: TorrentStatus = {
        "state": lt.torrent_status.states.finished,
        "progress": 100.0,
        "down_speed": 0.0,
        "up_speed": 0.0,
        "seeders": 0,
        "leechers": 0,
        "is_paused": False,
        "eta": None,
        "is_seeding": True,
    }
    assert dm.get_torrent_state_text(completed_status) == "Completed"
    assert dm.get_torrent_state_text(completed_status, short=True) == "DONE"

    meta_status: TorrentStatus = {
        "state": lt.torrent_status.states.downloading_metadata,
        "progress": 0.0,
        "down_speed": 0.0,
        "up_speed": 0.0,
        "seeders": 0,
        "leechers": 5,
        "is_paused": False,
        "eta": None,
        "is_seeding": False,
    }
    assert dm.get_torrent_state_text(meta_status) == "Fetching"
    assert dm.get_torrent_state_text(meta_status, short=True) == "META"


def test_get_session_stats():
    dm = DownloadManager()
    stats = dm.get_session_stats()
    assert "download_rate" in stats
    assert "upload_rate" in stats
    assert "dht_nodes" in stats
    assert isinstance(stats["download_rate"], (int, float))
    assert isinstance(stats["upload_rate"], (int, float))
    assert isinstance(stats["dht_nodes"], int)


def test_get_session_stats_fallback():
    from unittest.mock import MagicMock

    dm = DownloadManager()
    dm.session = MagicMock()
    dm.session.status.side_effect = RuntimeError("session status failed")

    handle_mock = MagicMock()
    handle_mock.is_valid.return_value = True
    handle_status_mock = MagicMock()
    handle_status_mock.download_rate = 1048576
    handle_status_mock.upload_rate = 524288
    handle_mock.status.return_value = handle_status_mock

    dm.torrents = {"magnet:?xt=urn:btih:mock": handle_mock}

    stats = dm.get_session_stats()
    assert stats["download_rate"] == 1048576.0
    assert stats["upload_rate"] == 524288.0
    assert stats["dht_nodes"] == 0


def test_get_torrent_status_abi2_error_handling():
    from unittest.mock import MagicMock

    dm = DownloadManager()
    handle_mock = MagicMock()
    handle_mock.is_valid.return_value = True

    status_mock = MagicMock(
        spec=[
            "state",
            "progress",
            "download_rate",
            "upload_rate",
            "total_wanted",
            "total_wanted_done",
            "errc",
            "error_file",
            "flags",
            "is_seeding",
            "is_finished",
            "has_metadata",
            "save_path",
            "num_seeds",
            "num_peers",
            "list_seeds",
            "list_peers",
        ]
    )
    status_mock.state = lt.torrent_status.states.downloading
    status_mock.progress = 0.5
    status_mock.download_rate = 0
    status_mock.upload_rate = 0
    status_mock.total_wanted = 1000
    status_mock.total_wanted_done = 500
    status_mock.flags = 0
    status_mock.is_seeding = False
    status_mock.is_finished = False
    status_mock.has_metadata = False
    status_mock.save_path = ""
    status_mock.num_seeds = 0
    status_mock.num_peers = 0
    status_mock.list_seeds = 0
    status_mock.list_peers = 0
    status_mock.error_file = -1

    # Simulate libtorrent ABI 2 errc without .error attribute
    errc_mock = MagicMock()
    errc_mock.value.return_value = 1
    errc_mock.message.return_value = "No such file or directory"
    status_mock.errc = errc_mock

    handle_mock.status.return_value = status_mock
    magnet = "magnet:?xt=urn:btih:abi2mocktest"
    dm.torrents = {magnet: handle_mock}

    status = dm.get_torrent_status(magnet)
    assert status is not None
    assert status["error"] == "No such file or directory"
    assert status["is_missing_files"] is True


def test_state_map_abi2():
    expected_states = {
        lt.torrent_status.states.downloading,
        lt.torrent_status.states.seeding,
        lt.torrent_status.states.finished,
        lt.torrent_status.states.downloading_metadata,
        lt.torrent_status.states.checking_files,
        lt.torrent_status.states.checking_resume_data,
    }
    assert set(DownloadManager._STATE_MAP.keys()) == expected_states


def test_add_torrent_save_path_expanded(
    monkeypatch: pytest.MonkeyPatch, mock_config: Any
):
    import os
    from unittest.mock import MagicMock

    mock_config.set("general.download_path", "~/custom_dl_path")
    dm = DownloadManager()
    captured_atp = []

    def mock_add_torrent(atp: Any):
        captured_atp.append(atp)
        handle = MagicMock()
        handle.is_valid.return_value = True
        handle.status.return_value.has_metadata = False
        return handle

    monkeypatch.setattr(dm.session, "add_torrent", mock_add_torrent)
    dm.add_torrent("magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567")

    assert len(captured_atp) == 1
    expected = os.path.abspath(os.path.expanduser("~/custom_dl_path"))
    assert captured_atp[0].save_path == expected


def test_get_torrent_status_save_path_expanded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any, mock_config: Any
):
    from pathlib import Path
    from unittest.mock import MagicMock

    dm = DownloadManager()
    handle_mock = MagicMock()
    handle_mock.is_valid.return_value = True

    status_mock = MagicMock()
    status_mock.state = lt.torrent_status.states.seeding
    status_mock.progress = 1.0
    status_mock.download_rate = 0
    status_mock.upload_rate = 0
    status_mock.total_wanted = 1000
    status_mock.total_wanted_done = 1000
    status_mock.flags = 0
    status_mock.is_seeding = True
    status_mock.is_finished = True
    status_mock.has_metadata = True
    status_mock.save_path = str(tmp_path)
    status_mock.num_seeds = 1
    status_mock.num_peers = 1
    status_mock.list_seeds = 1
    status_mock.list_peers = 1
    status_mock.error_file = -1
    status_mock.errc = None

    # Create dummy file
    test_file = Path(tmp_path) / "test.txt"
    test_file.write_text("hello")

    torrent_info_mock = MagicMock()
    fs_mock = MagicMock()
    fs_mock.num_files.return_value = 1
    fs_mock.file_path.return_value = "test.txt"
    fs_mock.file_flags.return_value = 0
    torrent_info_mock.files.return_value = fs_mock
    handle_mock.torrent_file.return_value = torrent_info_mock

    handle_mock.status.return_value = status_mock
    magnet = "magnet:?xt=urn:btih:mock_save_path_test"
    dm.torrents = {magnet: handle_mock}

    status = dm.get_torrent_status(magnet)
    assert status is not None
    assert status["is_missing_files"] is False
