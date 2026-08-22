import libtorrent as lt

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


def test_state_text_checking_and_allocating():
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

    alloc_status: TorrentStatus = {
        "state": lt.torrent_status.states.allocating,
        "progress": 0.0,
        "down_speed": 0.0,
        "up_speed": 0.0,
        "seeders": 0,
        "leechers": 0,
        "is_paused": False,
        "eta": None,
        "is_seeding": False,
    }
    assert dm.get_torrent_state_text(alloc_status) == "Allocating"
    assert dm.get_torrent_state_text(alloc_status, short=True) == "ALOC"


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
    up, down = dm.get_torrent_limits(magnet)
    assert up == 1024 * 1024
    assert down == 2 * 1024**2

    # unlimited
    dm.set_torrent_limits(magnet, -1, -1)
    up, down = dm.get_torrent_limits(magnet)
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
    up, down = dm.get_torrent_limits(magnet)
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
