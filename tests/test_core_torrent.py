import pytest

from torrra._types import Torrent
from torrra.core.download import selection_priorities
from torrra.core.torrent import TorrentManager


@pytest.fixture
def tm(tmp_path, monkeypatch):
    from torrra.core import db as db_module
    from torrra.core.db import init_db

    monkeypatch.setattr(db_module, "DB_DIR", tmp_path)
    monkeypatch.setattr(db_module, "DB_FILE", tmp_path / "torrra.db")
    init_db()
    return TorrentManager()


def _torrent(uri="magnet:?xt=urn:btih:abc", selected_files=None) -> Torrent:
    return Torrent(
        magnet_uri=uri,
        title="Example",
        size=123.0,
        seeders=0,
        leechers=0,
        source="test",
        selected_files=selected_files,
    )


def test_add_and_load_selected_files(tm):
    tm.add_torrent(_torrent(selected_files=[0, 2]))

    records = tm.get_all_torrents()
    assert len(records) == 1
    assert records[0]["selected_files"] == [0, 2]


def test_add_and_load_without_selection(tm):
    tm.add_torrent(_torrent(selected_files=None))

    records = tm.get_all_torrents()
    assert records[0]["selected_files"] is None


def test_load_malformed_selection_is_none(tm):
    tm.add_torrent(_torrent(selected_files=[1]))

    from torrra.core.db import get_db_connection

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE torrents SET selected_files = 'not-json' WHERE magnet_uri = ?",
            ("magnet:?xt=urn:btih:abc",),
        )
        conn.commit()

    records = tm.get_all_torrents()
    assert records[0]["selected_files"] is None


def test_selection_priorities_builds_partial_vector():
    assert selection_priorities([0, 2]) == [1, 0, 1]
    assert selection_priorities([4]) == [0, 0, 0, 0, 1]


def test_selection_priorities_none_or_empty():
    assert selection_priorities(None) is None
    assert selection_priorities([]) is None


def test_update_selected_files_persists(tm):
    tm.add_torrent(_torrent(selected_files=[0, 2]))

    tm.update_torrent_selected_files("magnet:?xt=urn:btih:abc", [1])

    records = tm.get_all_torrents()
    assert records[0]["selected_files"] == [1]


def test_update_selected_files_clears_selection(tm):
    tm.add_torrent(_torrent(selected_files=[0, 2]))

    tm.update_torrent_selected_files("magnet:?xt=urn:btih:abc", None)

    records = tm.get_all_torrents()
    assert records[0]["selected_files"] is None
