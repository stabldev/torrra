from unittest.mock import MagicMock

from torrra._types import TorrentFile
from torrra.core.download import DownloadManager, build_priorities


def test_build_priorities_selects_only_selected():
    assert build_priorities(5, {0, 3}) == [1, 0, 0, 1, 0]


def test_build_priorities_empty_selection():
    assert build_priorities(3, set()) == [0, 0, 0]


def test_build_priorities_all_selected():
    assert build_priorities(4, {0, 1, 2, 3}) == [1, 1, 1, 1]


def _make_torrent_info(
    file_specs: list[tuple[str, int]], name: str = "torrent", total_size: int = 30
) -> MagicMock:
    info = MagicMock()
    info.name.return_value = name
    info.total_size.return_value = total_size
    storage = MagicMock()
    storage.num_files.return_value = len(file_specs)
    storage.file_path.side_effect = [spec[0] for spec in file_specs]
    storage.file_size.side_effect = [spec[1] for spec in file_specs]
    info.files.return_value = storage
    return info


def _make_handle(has_metadata: bool | None = None) -> MagicMock:
    handle = MagicMock()
    handle.is_valid.return_value = True
    if has_metadata is not None:
        handle.has_metadata.return_value = has_metadata
    return handle


def _make_manager(handle: MagicMock) -> DownloadManager:
    manager = DownloadManager.__new__(DownloadManager)
    manager.session = MagicMock()
    manager.torrents = {"uri": handle}
    manager._metadata_updated = set()
    return manager


def _make_status(**kwargs) -> MagicMock:
    status = MagicMock()
    for key, value in kwargs.items():
        setattr(status, key, value)
    return status


def test_get_torrent_status_reports_zero_download_when_finished():
    from torrra.core import download as download_module

    handle = _make_handle()
    handle.status.return_value = _make_status(
        is_seeding=False,
        is_finished=True,
        state=download_module.lt.torrent_status.states.finished,
        total_wanted=100,
        total_wanted_done=100,
        download_rate=6000.0,
        upload_rate=185.0,
        progress=1.0,
        num_seeds=5,
        num_peers=3,
        flags=0,
    )
    manager = _make_manager(handle)

    result = manager.get_torrent_status("uri")

    assert result["down_speed"] == 0.0
    assert result["up_speed"] == 185.0
    assert result["is_seeding"] is True
    assert result["eta"] is None


def test_get_torrent_status_reports_download_speed_while_downloading():
    from torrra.core import download as download_module

    handle = _make_handle()
    handle.status.return_value = _make_status(
        is_seeding=False,
        is_finished=False,
        state=download_module.lt.torrent_status.states.downloading,
        total_wanted=1000,
        total_wanted_done=500,
        download_rate=6000.0,
        upload_rate=0.0,
        progress=0.5,
        num_seeds=2,
        num_peers=4,
        flags=0,
    )
    manager = _make_manager(handle)

    result = manager.get_torrent_status("uri")

    assert result["down_speed"] == 6000.0
    assert result["eta"] == 500 / 6000.0
    assert result["is_seeding"] is False


def test_get_files_returns_none_without_metadata():
    handle = _make_handle(has_metadata=False)
    manager = _make_manager(handle)

    assert manager.get_files("uri") is None


def test_get_files_returns_file_list_with_metadata():
    handle = _make_handle(has_metadata=True)
    handle.torrent_file.return_value = _make_torrent_info(
        [("a.txt", 10), ("sub/b.bin", 20)]
    )
    manager = _make_manager(handle)

    assert manager.get_files("uri") == [
        TorrentFile(index=0, path="a.txt", size=10),
        TorrentFile(index=1, path="sub/b.bin", size=20),
    ]


def test_get_file_details_returns_progress_and_priorities():
    handle = _make_handle(has_metadata=True)
    handle.torrent_file.return_value = _make_torrent_info(
        [("a.txt", 10), ("b.bin", 20)], total_size=30
    )
    handle.file_progress.return_value = [10, 5]
    handle.file_priorities.return_value = [1, 0]
    manager = _make_manager(handle)

    details = manager.get_file_details("uri")

    assert details is not None
    assert len(details) == 2
    assert details[0].index == 0
    assert details[0].path == "a.txt"
    assert details[0].size == 10
    assert details[0].downloaded == 10
    assert details[0].priority == 1
    assert details[1].downloaded == 5
    assert details[1].priority == 0


def test_get_file_details_falls_back_when_progress_fails():
    handle = _make_handle(has_metadata=True)
    handle.torrent_file.return_value = _make_torrent_info(
        [("a.txt", 10)], total_size=10
    )
    handle.file_progress.side_effect = RuntimeError
    handle.file_priorities.side_effect = RuntimeError
    manager = _make_manager(handle)

    details = manager.get_file_details("uri")

    assert details is not None
    assert details[0].downloaded == 0
    assert details[0].priority == 0


def test_get_file_details_returns_none_without_metadata():
    handle = _make_handle(has_metadata=False)
    manager = _make_manager(handle)

    assert manager.get_file_details("uri") is None
    handle.file_progress.assert_not_called()


def test_get_metadata_returns_name_and_total_size():
    handle = _make_handle(has_metadata=True)
    handle.torrent_file.return_value = _make_torrent_info(
        [("a.txt", 10)], name="my-torrent", total_size=10
    )
    manager = _make_manager(handle)

    assert manager.get_metadata("uri") == ("my-torrent", 10)


def test_prioritize_files_applies_selected_priorities():
    handle = _make_handle(has_metadata=True)
    handle.torrent_file.return_value = _make_torrent_info(
        [("a.txt", 10), ("b.bin", 20), ("c.iso", 30)]
    )
    manager = _make_manager(handle)

    assert manager.prioritize_files("uri", {0, 2}) is True
    handle.prioritize_files.assert_called_once_with([1, 0, 1])


def test_prioritize_files_returns_false_without_metadata():
    handle = _make_handle(has_metadata=False)
    manager = _make_manager(handle)

    assert manager.prioritize_files("uri", {0}) is False
    handle.prioritize_files.assert_not_called()


def test_resume_torrent():
    handle = _make_handle()
    manager = _make_manager(handle)

    assert manager.resume_torrent("uri") is True
    handle.unset_flags.assert_called_once_with(0x800002)
    handle.set_flags.assert_called_once_with(0x20)
    handle.resume.assert_called_once()


async def test_wait_for_metadata_polls_until_available(fast_sleep):
    calls = {"n": 0}
    handle = _make_handle()

    def fake_has_metadata() -> bool:
        calls["n"] += 1
        return calls["n"] >= 3

    handle.has_metadata.side_effect = fake_has_metadata
    handle.torrent_file.return_value = _make_torrent_info(
        [("a.txt", 10), ("b.bin", 20)]
    )
    manager = _make_manager(handle)

    result = await manager.wait_for_metadata("uri", timeout=5)

    assert result == [
        TorrentFile(index=0, path="a.txt", size=10),
        TorrentFile(index=1, path="b.bin", size=20),
    ]
    assert calls["n"] >= 3


async def test_wait_for_metadata_times_out(fast_sleep):
    handle = _make_handle(has_metadata=False)
    manager = _make_manager(handle)

    result = await manager.wait_for_metadata("uri", timeout=0.01)

    assert result is None


def test_add_torrent_sets_torrent_info(monkeypatch):
    from torrra.core import download as download_module

    atp = MagicMock()
    parse_magnet = MagicMock(return_value=atp)
    handle = MagicMock()
    handle.is_valid.return_value = False

    class FakeFlags:
        paused = 0x10
        auto_managed = 0x20
        upload_mode = 0x2
        default_dont_download = 0x800000

    class FakeSession:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def add_torrent(self, params):
            return handle

    class FakeLt:
        parse_magnet_uri = staticmethod(parse_magnet)
        torrent_flags = FakeFlags
        session = FakeSession

    monkeypatch.setattr(download_module, "lt", FakeLt)

    manager = download_module.DownloadManager()
    torrent_info = MagicMock()

    manager.add_torrent("magnet:?xt=urn:btih:abc", torrent_info=torrent_info)

    assert manager.torrents["magnet:?xt=urn:btih:abc"] is handle
    assert atp.ti is torrent_info


def test_add_torrent_metadata_only_sets_flags(monkeypatch):
    from torrra.core import download as download_module

    atp = MagicMock()
    atp.flags = 0x20  # default_flags: auto_managed set, paused cleared
    parse_magnet = MagicMock(return_value=atp)
    handle = MagicMock()
    handle.is_valid.return_value = False

    class FakeFlags:
        paused = 0x10
        auto_managed = 0x20
        upload_mode = 0x2
        default_dont_download = 0x800000

    class FakeSession:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def add_torrent(self, params):
            return handle

    class FakeLt:
        parse_magnet_uri = staticmethod(parse_magnet)
        torrent_flags = FakeFlags
        session = FakeSession

    monkeypatch.setattr(download_module, "lt", FakeLt)

    manager = download_module.DownloadManager()

    manager.add_torrent("magnet:?xt=urn:btih:abc", metadata_only=True)

    assert manager.torrents["magnet:?xt=urn:btih:abc"] is handle
    assert atp.flags == 0x800022
    assert atp.flags & 0x10 == 0
    assert atp.flags & 0x20 != 0


def test_add_torrent_sets_file_priorities(monkeypatch):
    from torrra.core import download as download_module

    atp = MagicMock()
    atp.flags = 0x0
    parse_magnet = MagicMock(return_value=atp)
    handle = MagicMock()
    handle.is_valid.return_value = False

    class FakeFlags:
        paused = 0x10
        auto_managed = 0x20
        upload_mode = 0x2
        default_dont_download = 0x800000

    class FakeSession:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def add_torrent(self, params):
            return handle

    class FakeLt:
        parse_magnet_uri = staticmethod(parse_magnet)
        torrent_flags = FakeFlags
        session = FakeSession

    monkeypatch.setattr(download_module, "lt", FakeLt)

    manager = download_module.DownloadManager()

    manager.add_torrent(
        "magnet:?xt=urn:btih:abc",
        file_priorities=[1, 0, 1],
    )

    assert atp.file_priorities == [1, 0, 1]
    assert atp.flags & 0x800000 != 0


def test_add_torrent_without_file_priorities_leaves_vector_empty(monkeypatch):
    from torrra.core import download as download_module

    atp = MagicMock()
    atp.flags = 0x20
    parse_magnet = MagicMock(return_value=atp)
    handle = MagicMock()
    handle.is_valid.return_value = False

    class FakeFlags:
        paused = 0x10
        auto_managed = 0x20
        upload_mode = 0x2
        default_dont_download = 0x800000

    class FakeSession:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def add_torrent(self, params):
            return handle

    class FakeLt:
        parse_magnet_uri = staticmethod(parse_magnet)
        torrent_flags = FakeFlags
        session = FakeSession

    monkeypatch.setattr(download_module, "lt", FakeLt)

    manager = download_module.DownloadManager()

    manager.add_torrent("magnet:?xt=urn:btih:abc")

    assert "file_priorities" not in atp.__dict__
    assert atp.flags & 0x800000 == 0
