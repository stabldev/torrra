import sqlite3
from functools import lru_cache

from torrra._types import Torrent, TorrentRecord
from torrra.core.db import get_db_connection, init_db


@lru_cache
def get_torrent_manager() -> "TorrentManager":
    init_db()
    return TorrentManager()


class TorrentManager:
    def add_torrent(self, torrent: Torrent) -> None:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO torrents (magnet_uri, title, size, source)
                VALUES (?, ?, ?, ?)
                """,
                (
                    torrent.magnet_uri,
                    torrent.title,
                    torrent.size,
                    torrent.source,
                ),
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

    def get_all_torrents(self) -> list[TorrentRecord]:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM torrents")
            rows = cursor.fetchall()

            return [
                TorrentRecord(
                    magnet_uri=row["magnet_uri"],
                    title=row["title"],
                    size=row["size"],
                    source=row["source"],
                    is_paused=bool(row["is_paused"]),
                    is_notified=bool(row["is_notified"]),
                )
                for row in rows
            ]
