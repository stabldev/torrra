from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import libtorrent as lt
import pytest

from torrra._types import TorrentOptions, TorrentStatus
from torrra.core.download import DownloadManager
from torrra.core.exceptions import DownloadError


class FakeTorrentHandle:
    def __init__(self, save_path: str, flags: Any) -> None:
        self._valid = True
        self._status = SimpleNamespace(
            has_metadata=False,
            flags=flags,
            save_path=save_path,
        )
        self.metadata: object | None = None

    def is_valid(self) -> bool:
        return self._valid

    def status(self) -> SimpleNamespace:
        return self._status

    def torrent_file(self) -> object | None:
        return self.metadata

    def prioritize_files(self, _priorities: list[int]) -> None:
        return None

    def set_flags(self, flags: Any) -> None:
        self._status.flags |= flags

    def unset_flags(self, flags: Any) -> None:
        self._status.flags &= ~flags

    def pause(self) -> None:
        self._status.flags |= lt.torrent_flags.paused

    def resume(self) -> None:
        self._status.flags &= ~lt.torrent_flags.paused


class FakeTorrentSession:
    def __init__(self) -> None:
        self.added: list[tuple[Any, FakeTorrentHandle]] = []
        self.removed: list[FakeTorrentHandle] = []

    def add_torrent(self, params: Any) -> FakeTorrentHandle:
        handle = FakeTorrentHandle(params.save_path, params.flags)
        self.added.append((params, handle))
        return handle

    def remove_torrent(self, handle: FakeTorrentHandle, _options: Any = None) -> None:
        handle._valid = False
        self.removed.append(handle)


def make_download_manager(session: FakeTorrentSession) -> DownloadManager:
    manager = DownloadManager.__new__(DownloadManager)
    manager.session = cast(Any, session)
    manager.torrents = {}
    manager._metadata_only_torrents = set()
    manager._file_priorities = {}
    manager._limits = {}
    manager._options = {}
    manager._metadata_updated = set()
    return manager


@pytest.fixture
def fake_parse_magnet(monkeypatch: pytest.MonkeyPatch):
    def parse(_uri: str) -> SimpleNamespace:
        return SimpleNamespace(save_path="", flags=0, ti=None)

    monkeypatch.setattr("torrra.core.download.lt.parse_magnet_uri", parse)


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


def test_add_torrent_sets_explicit_save_path(tmp_path: Path, fake_parse_magnet: None):
    session = FakeTorrentSession()
    manager = make_download_manager(session)
    destination = tmp_path / "custom"
    magnet = "magnet:?xt=urn:btih:customsavepath"

    manager.add_torrent(magnet, save_path=str(destination))

    params, _handle = session.added[0]
    assert params.save_path == str(destination)
    assert not (params.flags & lt.torrent_flags.default_dont_download)


def test_metadata_handle_is_replaced_with_final_save_path(
    tmp_path: Path, fake_parse_magnet: None
):
    session = FakeTorrentSession()
    manager = make_download_manager(session)
    preview_path = tmp_path / "preview"
    final_path = tmp_path / "final"
    magnet = "magnet:?xt=urn:btih:metadatapromotion"

    preview_handle = cast(
        FakeTorrentHandle,
        manager.fetch_metadata(magnet, save_path=str(preview_path)),
    )
    preview_params, _ = session.added[0]
    assert preview_params.flags & lt.torrent_flags.default_dont_download

    metadata = object()
    preview_handle.status().has_metadata = True
    preview_handle.metadata = metadata

    final_handle = manager.add_torrent(magnet, save_path=str(final_path))

    final_params, _ = session.added[1]
    assert preview_handle in session.removed
    assert final_handle is not preview_handle
    assert final_params.save_path == str(final_path)
    assert final_params.ti is metadata
    assert not (final_params.flags & lt.torrent_flags.default_dont_download)
    assert magnet not in manager._metadata_only_torrents


def test_add_torrent_rejects_active_path_change(
    tmp_path: Path, fake_parse_magnet: None
):
    session = FakeTorrentSession()
    manager = make_download_manager(session)
    magnet = "magnet:?xt=urn:btih:activepath"
    first_path = tmp_path / "first"

    manager.add_torrent(magnet, save_path=str(first_path))

    with pytest.raises(DownloadError, match="active torrent"):
        manager.add_torrent(magnet, save_path=str(tmp_path / "second"))

    assert len(session.added) == 1


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


def _sample_magnet(suffix: str) -> str:
    return f"magnet:?xt=urn:btih:{suffix * 40}"


def test_set_and_get_torrent_limits():
    dm = DownloadManager()
    magnet = _sample_magnet("a")
    dm.add_torrent(magnet)
    assert magnet in dm.torrents

    dm.set_torrent_limits(magnet, 1024 * 1024, 2 * 1024**2)
    limits = dm.get_torrent_limits(magnet)
    assert limits is not None
    up, down = limits
    assert up == 1024 * 1024
    assert down == 2 * 1024**2

    # unlimited
    dm.set_torrent_limits(magnet, -1, -1)
    limits = dm.get_torrent_limits(magnet)
    assert limits is not None
    up, down = limits
    assert up == -1
    assert down == -1


def test_limits_seeded_on_add_are_applied():
    dm = DownloadManager()
    magnet = _sample_magnet("b")
    dm.add_torrent(
        magnet,
        upload_limit=512 * 1024,
        download_limit=1024 * 1024,
    )
    assert magnet in dm.torrents
    limits = dm.get_torrent_limits(magnet)
    assert limits is not None
    up, down = limits
    assert up == 512 * 1024
    assert down == 1024 * 1024


def test_torrent_limits_persisted_to_db():
    from torrra._types import Torrent
    from torrra.core.torrent import get_torrent_manager

    magnet = _sample_magnet("c")
    # the torrent must already exist in the database, as it would in the
    # real flow where the user initiates a download
    get_torrent_manager().add_torrent(
        Torrent(
            magnet_uri=magnet,
            title="Test",
            size=1000,
            source="test",
            seeders=0,
            leechers=0,
        )
    )

    dm = DownloadManager()
    dm.add_torrent(magnet)
    dm.set_torrent_limits(magnet, 1024, 2048)

    record = get_torrent_manager().get_torrent(magnet)
    assert record is not None
    assert record.get("upload_limit") == 1024
    assert record.get("download_limit") == 2048


def test_global_speed_limits_disabled_by_default():
    dm = DownloadManager()
    assert dm.is_speed_limit_enabled() is False
    settings = dm.session.get_settings()
    assert settings["download_rate_limit"] == 0
    assert settings["upload_rate_limit"] == 0


def test_global_speed_limits_toggle():
    dm = DownloadManager()
    dm.set_speed_limit_enabled(True)
    assert dm.is_speed_limit_enabled() is True
    settings = dm.session.get_settings()
    assert settings["download_rate_limit"] == 10240
    assert settings["upload_rate_limit"] == 10240

    dm.set_speed_limit_enabled(False)
    assert dm.is_speed_limit_enabled() is False
    settings = dm.session.get_settings()
    assert settings["download_rate_limit"] == 0
    assert settings["upload_rate_limit"] == 0


def test_global_speed_limits_enabled_on_startup(mock_config):
    mock_config.set("speed_limit.enabled", "true")
    mock_config.set("speed_limit.download_limit", "2M")
    mock_config.set("speed_limit.upload_limit", "500K")

    dm = DownloadManager()
    assert dm.is_speed_limit_enabled() is True
    settings = dm.session.get_settings()
    assert settings["download_rate_limit"] == 2 * 1024 * 1024
    assert settings["upload_rate_limit"] == 500 * 1024


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

    # Setup dummy directory and file in tmp_path
    sub_dir = Path(tmp_path) / "dl_folder"
    sub_dir.mkdir()
    test_file = sub_dir / "test.txt"
    test_file.write_text("hello")

    # Set up environment variables so path expansion is required
    monkeypatch.setenv("TEST_STATUS_DIR", "dl_folder")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

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
    # Unexpanded path with tilde and environment variable
    status_mock.save_path = "~/$TEST_STATUS_DIR"
    status_mock.num_seeds = 1
    status_mock.num_peers = 1
    status_mock.list_seeds = 1
    status_mock.list_peers = 1
    status_mock.error_file = -1
    status_mock.errc = None

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


def test_get_torrent_status_save_path_config_fallback_expanded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any, mock_config: Any
):
    from pathlib import Path
    from unittest.mock import MagicMock

    sub_dir = Path(tmp_path) / "cfg_downloads"
    sub_dir.mkdir()
    test_file = sub_dir / "test.txt"
    test_file.write_text("hello")

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    mock_config.set("general.download_path", "~/cfg_downloads")

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
    status_mock.save_path = ""  # empty so it triggers config fallback
    status_mock.num_seeds = 1
    status_mock.num_peers = 1
    status_mock.list_seeds = 1
    status_mock.list_peers = 1
    status_mock.error_file = -1
    status_mock.errc = None

    torrent_info_mock = MagicMock()
    fs_mock = MagicMock()
    fs_mock.num_files.return_value = 1
    fs_mock.file_path.return_value = "test.txt"
    fs_mock.file_flags.return_value = 0
    torrent_info_mock.files.return_value = fs_mock
    handle_mock.torrent_file.return_value = torrent_info_mock

    handle_mock.status.return_value = status_mock
    magnet = "magnet:?xt=urn:btih:mock_save_path_cfg_test"
    dm.torrents = {magnet: handle_mock}

    status = dm.get_torrent_status(magnet)
    assert status is not None
    assert status["is_missing_files"] is False


def test_save_and_load_session_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from torrra.core import db as db_module

    session_dir = tmp_path / "test_db_dir"
    session_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(db_module, "DB_DIR", session_dir)
    monkeypatch.setattr("torrra.core.download.DB_DIR", session_dir)

    dm = DownloadManager()
    dm.save_session_state()

    session_file = session_dir / "session.dat"
    assert session_file.exists()
    assert session_file.stat().st_size > 0

    # Test loading existing session file
    dm2 = DownloadManager()
    assert dm2.session is not None


def test_set_and_get_torrent_options():
    from unittest.mock import MagicMock

    dm = DownloadManager()
    handle_mock = MagicMock()
    handle_mock.is_valid.return_value = True

    magnet = "magnet:?xt=urn:btih:mock_options_test"
    dm.torrents = {magnet: handle_mock}

    opts = TorrentOptions(
        upload_limit=10240,
        download_limit=20480,
        max_ratio=1.5,
        max_seeding_time=120,
        sequential_download=True,
    )
    dm.set_torrent_options(magnet, opts)

    retrieved = dm.get_torrent_options(magnet)
    assert retrieved.upload_limit == 10240
    assert retrieved.download_limit == 20480
    assert retrieved.max_ratio == 1.5
    assert retrieved.max_seeding_time == 120
    assert retrieved.sequential_download is True

    handle_mock.set_upload_limit.assert_called_with(10240)
    handle_mock.set_download_limit.assert_called_with(20480)


def test_auto_pause_on_ratio_limit_reached():
    from unittest.mock import MagicMock

    dm = DownloadManager()
    handle_mock = MagicMock()
    handle_mock.is_valid.return_value = True

    status_mock = MagicMock()
    status_mock.state = lt.torrent_status.states.seeding
    status_mock.progress = 1.0
    status_mock.download_rate = 0
    status_mock.upload_rate = 100
    status_mock.total_done = 1000
    status_mock.total_wanted = 1000
    status_mock.total_wanted_done = 1000
    status_mock.all_time_upload = 2000
    status_mock.all_time_download = 1000
    status_mock.seeding_duration = 60
    status_mock.flags = 0
    status_mock.is_seeding = True
    status_mock.is_finished = True
    status_mock.has_metadata = False
    status_mock.save_path = "test"
    status_mock.num_seeds = 1
    status_mock.num_peers = 1
    status_mock.list_seeds = 1
    status_mock.list_peers = 1
    status_mock.error_file = -1
    status_mock.errc = None

    handle_mock.status.return_value = status_mock
    magnet = "magnet:?xt=urn:btih:mock_ratio_test"
    dm.torrents = {magnet: handle_mock}

    # Ratio limit is 1.5, actual ratio is 2.0 (2000 / 1000)
    opts = TorrentOptions(max_ratio=1.5)
    dm.set_torrent_options(magnet, opts)

    status = dm.get_torrent_status(magnet)
    assert status is not None
    assert status["ratio"] == 2.0
    assert status["is_paused"] is True
    handle_mock.pause.assert_called_once()


def test_auto_pause_on_seeding_time_limit_reached():
    from unittest.mock import MagicMock

    dm = DownloadManager()
    handle_mock = MagicMock()
    handle_mock.is_valid.return_value = True

    status_mock = MagicMock()
    status_mock.state = lt.torrent_status.states.seeding
    status_mock.progress = 1.0
    status_mock.download_rate = 0
    status_mock.upload_rate = 100
    status_mock.total_done = 1000
    status_mock.total_wanted = 1000
    status_mock.total_wanted_done = 1000
    status_mock.all_time_upload = 500
    status_mock.all_time_download = 1000
    status_mock.seeding_duration = 3600  # 60 minutes
    status_mock.flags = 0
    status_mock.is_seeding = True
    status_mock.is_finished = True
    status_mock.has_metadata = False
    status_mock.save_path = "test"
    status_mock.num_seeds = 1
    status_mock.num_peers = 1
    status_mock.list_seeds = 1
    status_mock.list_peers = 1
    status_mock.error_file = -1
    status_mock.errc = None

    handle_mock.status.return_value = status_mock
    magnet = "magnet:?xt=urn:btih:mock_time_test"
    dm.torrents = {magnet: handle_mock}

    # Seeding time limit is 30 minutes, actual is 60 minutes
    opts = TorrentOptions(max_seeding_time=30)
    dm.set_torrent_options(magnet, opts)

    status = dm.get_torrent_status(magnet)
    assert status is not None
    assert status["seeding_duration"] == 3600
    assert status["is_paused"] is True
    handle_mock.pause.assert_called_once()


def test_seeding_duration_timedelta():
    import datetime
    from unittest.mock import MagicMock

    dm = DownloadManager()
    handle_mock = MagicMock()
    handle_mock.is_valid.return_value = True

    status_mock = MagicMock()
    status_mock.state = lt.torrent_status.states.seeding
    status_mock.progress = 1.0
    status_mock.download_rate = 0
    status_mock.upload_rate = 100
    status_mock.total_done = 1000
    status_mock.total_wanted = 1000
    status_mock.total_wanted_done = 1000
    status_mock.all_time_upload = 500
    status_mock.all_time_download = 1000
    status_mock.seeding_duration = datetime.timedelta(seconds=125)
    status_mock.flags = 0
    status_mock.is_seeding = True
    status_mock.is_finished = True
    status_mock.has_metadata = False
    status_mock.save_path = "test"
    status_mock.num_seeds = 1
    status_mock.num_peers = 1
    status_mock.list_seeds = 1
    status_mock.list_peers = 1
    status_mock.error_file = -1
    status_mock.errc = None

    handle_mock.status.return_value = status_mock
    magnet = "magnet:?xt=urn:btih:mock_timedelta_test"
    dm.torrents = {magnet: handle_mock}

    status = dm.get_torrent_status(magnet)
    assert status is not None
    assert status["seeding_duration"] == 125


def test_get_torrent_peers_and_trackers():
    from unittest.mock import MagicMock

    dm = DownloadManager()
    magnet = "magnet:?xt=urn:btih:mock_peers_trackers"

    # Test when torrent doesn't exist
    assert dm.get_torrent_peers(magnet) == []
    assert dm.get_torrent_trackers(magnet) == []
    assert dm.get_torrent_files_progress(magnet) is None

    handle_mock = MagicMock()
    handle_mock.is_valid.return_value = True

    # Mock peer
    peer_mock = MagicMock()
    peer_mock.ip = ("192.168.1.50", 6881)
    peer_mock.client = "qBittorrent/4.6.0"
    peer_mock.down_speed = 500000.0
    peer_mock.up_speed = 100000.0
    peer_mock.progress = 0.75
    peer_mock.interesting = True
    peer_mock.choked = False
    peer_mock.remote_interested = False
    peer_mock.remote_choked = False
    peer_mock.optimistic_unchoke = False
    peer_mock.snubbed = False
    peer_mock.local_connection = False
    peer_mock.seed = False

    # Mock peer 2 (empty client string, identified via peer ID)
    peer_mock2 = MagicMock()
    peer_mock2.ip = ("10.0.0.1", 51413)
    peer_mock2.client = b""
    pid_mock = MagicMock()
    pid_mock.to_bytes.return_value = b"-TR4050-123456789012"
    peer_mock2.pid = pid_mock
    peer_mock2.down_speed = 0.0
    peer_mock2.up_speed = 0.0
    peer_mock2.progress = 1.0
    peer_mock2.interesting = False
    peer_mock2.choked = True
    peer_mock2.remote_interested = False
    peer_mock2.remote_choked = True
    peer_mock2.optimistic_unchoke = False
    peer_mock2.snubbed = False
    peer_mock2.local_connection = False
    peer_mock2.seed = True

    handle_mock.get_peer_info.return_value = [peer_mock, peer_mock2]

    # Mock tracker
    tracker_mock = MagicMock()
    tracker_mock.url = "http://tracker.example.com/announce"
    tracker_mock.tier = 1
    tracker_mock.updating = False
    tracker_mock.fails = 0
    tracker_mock.is_working.return_value = True
    tracker_mock.scrape_complete = 50
    tracker_mock.scrape_incomplete = 10
    tracker_mock.message = "OK"
    handle_mock.trackers.return_value = [tracker_mock]

    # Mock files & metadata
    handle_mock.status.return_value.has_metadata = True
    info_mock = MagicMock()
    files_mock = MagicMock()
    files_mock.num_files.return_value = 1
    files_mock.file_flags.return_value = 0
    files_mock.file_path.return_value = "movie.mp4"
    files_mock.file_size.return_value = 1000000
    info_mock.files.return_value = files_mock
    handle_mock.torrent_file.return_value = info_mock
    handle_mock.file_progress.return_value = [500000]
    handle_mock.get_file_priorities.return_value = [1]

    dm.torrents = {magnet: handle_mock}

    # Test peers
    peers = dm.get_torrent_peers(magnet)
    assert len(peers) == 2
    assert peers[0]["ip"] == "192.168.1.50:6881"
    assert peers[0]["client"] == "qBittorrent/4.6.0"
    assert peers[0]["down_speed"] == 500000.0
    assert peers[0]["up_speed"] == 100000.0
    assert peers[0]["progress"] == 75.0
    assert peers[0]["flags"] == "I"

    assert peers[1]["ip"] == "10.0.0.1:51413"
    assert peers[1]["client"] == "Transmission 4.0.5"
    assert peers[1]["progress"] == 100.0
    assert "s" in peers[1]["flags"]

    # Test trackers
    trackers = dm.get_torrent_trackers(magnet)
    assert len(trackers) == 1
    assert trackers[0]["url"] == "http://tracker.example.com/announce"
    assert trackers[0]["status"] == "Working"
    assert trackers[0]["seeds"] == 50
    assert trackers[0]["peers"] == 10
    assert trackers[0]["message"] == "OK"

    # Test files progress
    files = dm.get_torrent_files_progress(magnet)
    assert files is not None
    assert len(files) == 1
    assert files[0]["path"] == "movie.mp4"
    assert files[0]["size"] == 1000000
    assert files[0]["done"] == 500000
    assert files[0]["progress"] == 50.0
    assert files[0]["priority_label"] == "Normal"

    # Test force reannounce
    dm.force_reannounce_torrent(magnet)
    handle_mock.force_reannounce.assert_called_once()
    handle_mock.force_dht_announce.assert_called_once()
