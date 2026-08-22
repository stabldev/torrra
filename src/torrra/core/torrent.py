import json
import sqlite3
from functools import lru_cache

from torrra._types import Torrent, TorrentRecord
from torrra.core.db import get_db_connection, init_db


@lru_cache
def get_torrent_manager() -> "TorrentManager":
    init_db()
    return TorrentManager()


class TorrentManager:
    def __init__(self) -> None:
        init_db()

    def add_torrent(
        self, torrent: Torrent, file_priorities: list[int] | None = None
    ) -> None:
        prios = (
            file_priorities if file_priorities is not None else torrent.file_priorities
        )
        priorities_json = json.dumps(prios) if prios is not None else None
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO torrents (magnet_uri, title, size, source, file_priorities)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    torrent.magnet_uri,
                    torrent.title,
                    torrent.size,
                    torrent.source,
                    priorities_json,
                ),
            )
            if priorities_json is not None:
                cursor.execute(
                    "UPDATE torrents SET file_priorities = ? WHERE magnet_uri = ?",
                    (priorities_json, torrent.magnet_uri),
                )
            conn.commit()

    def remove_torrent(self, magnet_uri: str) -> None:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM torrents WHERE magnet_uri = ?", (magnet_uri,))
            conn.commit()

    def update_torrent_paused_state(self, magnet_uri: str, is_paused: bool) -> None:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE torrents SET is_paused = ? WHERE magnet_uri = ?",
                (int(is_paused), magnet_uri),
            )
            conn.commit()

    def update_torrent_is_notified(self, magnet_uri: str) -> None:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE torrents SET is_notified = 1 WHERE magnet_uri = ?",
                (magnet_uri,),
            )
            conn.commit()

    def update_torrent_metadata(self, magnet_uri: str, title: str, size: int) -> None:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE torrents SET title = ?, size = ? WHERE magnet_uri = ?",
                (title, size, magnet_uri),
            )
            conn.commit()

    def update_torrent_file_priorities(
        self, magnet_uri: str, file_priorities: list[int] | None
    ) -> None:
        priorities_json = (
            json.dumps(file_priorities) if file_priorities is not None else None
        )
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE torrents SET file_priorities = ? WHERE magnet_uri = ?",
                (priorities_json, magnet_uri),
            )
            conn.commit()

    def update_torrent_limits(
        self, magnet_uri: str, upload_limit: int | None, download_limit: int | None
    ) -> None:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE torrents SET upload_limit = ?, download_limit = ? "
                "WHERE magnet_uri = ?",
                (upload_limit, download_limit, magnet_uri),
            )
            conn.commit()

    def get_torrent(self, magnet_uri: str) -> TorrentRecord | None:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM torrents WHERE magnet_uri = ?", (magnet_uri,))
            row = cursor.fetchone()
            if not row:
                return None
            prio_raw = dict(row).get("file_priorities")
            file_priorities = json.loads(prio_raw) if prio_raw else None
            return TorrentRecord(
                magnet_uri=row["magnet_uri"],
                title=row["title"],
                size=row["size"],
                source=row["source"],
                is_paused=bool(row["is_paused"]),
                is_notified=bool(row["is_notified"]),
                file_priorities=file_priorities,
                upload_limit=row["upload_limit"],
                download_limit=row["download_limit"],
            )

    def get_all_torrents(self) -> list[TorrentRecord]:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM torrents")
            rows = cursor.fetchall()

            result = []
            for row in rows:
                prio_raw = dict(row).get("file_priorities")
                file_priorities = json.loads(prio_raw) if prio_raw else None
                result.append(
                    TorrentRecord(
                        magnet_uri=row["magnet_uri"],
                        title=row["title"],
                        size=row["size"],
                        source=row["source"],
                        is_paused=bool(row["is_paused"]),
                        is_notified=bool(row["is_notified"]),
                        file_priorities=file_priorities,
                        upload_limit=row["upload_limit"],
                        download_limit=row["download_limit"],
                    )
                )
            return result
