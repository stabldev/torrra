import sqlite3
from pathlib import Path

import pytest

from torrra._types import Torrent
from torrra.core import db as db_module
from torrra.core.db import get_db_connection
from torrra.core.torrent import TorrentManager


def _torrent() -> Torrent:
    return Torrent(
        magnet_uri="magnet:?xt=urn:btih:persisted",
        title="Persisted Torrent",
        size=1024,
        seeders=1,
        leechers=0,
        source="Test",
    )


def test_torrent_manager_persists_custom_save_path(tmp_path: Path):
    manager = TorrentManager()
    save_path = tmp_path / "custom"

    manager.add_torrent(_torrent(), save_path=str(save_path))

    record = manager.get_torrent(_torrent().magnet_uri)
    assert record is not None
    assert record["save_path"] == str(save_path)


def test_torrent_manager_persists_global_fallback_as_null():
    manager = TorrentManager()

    manager.add_torrent(_torrent())

    record = manager.get_torrent(_torrent().magnet_uri)
    assert record is not None
    assert record["save_path"] is None


def test_init_db_migrates_existing_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    legacy_db = tmp_path / "legacy.db"
    monkeypatch.setattr(db_module, "DB_DIR", tmp_path)
    monkeypatch.setattr(db_module, "DB_FILE", legacy_db)

    with sqlite3.connect(legacy_db) as connection:
        connection.execute(
            """
            CREATE TABLE torrents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                magnet_uri TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                size REAL,
                source TEXT,
                is_paused BOOLEAN DEFAULT 0,
                is_notified BOOLEAN DEFAULT 0,
                file_priorities TEXT DEFAULT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO torrents (magnet_uri, title, size, source)
            VALUES ('magnet:?xt=urn:btih:legacy', 'Legacy', 1, 'Test')
            """
        )

    db_module.init_db()

    with get_db_connection() as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(torrents)")}
    record = TorrentManager().get_torrent("magnet:?xt=urn:btih:legacy")

    assert "save_path" in columns
    assert "max_ratio" in columns
    assert "max_seeding_time" in columns
    assert "sequential_download" in columns
    assert record is not None
    assert record["save_path"] is None
    assert record["max_ratio"] is None
    assert record["max_seeding_time"] is None
    assert record["sequential_download"] is False


def test_torrent_manager_update_options():
    manager = TorrentManager()
    t = _torrent()
    manager.add_torrent(t)

    manager.update_torrent_options(
        t.magnet_uri,
        upload_limit=512000,
        download_limit=1048576,
        max_ratio=1.5,
        max_seeding_time=120,
        sequential_download=True,
    )

    record = manager.get_torrent(t.magnet_uri)
    assert record is not None
    assert record["upload_limit"] == 512000
    assert record["download_limit"] == 1048576
    assert record["max_ratio"] == 1.5
    assert record["max_seeding_time"] == 120
    assert record["sequential_download"] is True
