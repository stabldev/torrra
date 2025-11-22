import sqlite3

from torrra._types import Torrent, TorrentRecord
from torrra.core.db import get_db_connection, init_db


class TorrentManager:
    def __init__(self) -> None:
        init_db()

    def add_torrent(self, torrent: Torrent) -> None:
        if not torrent.magnet_uri:
            return

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO torrents (magnet_uri, title, size, source)
                VALUES (?, ?, ?, ?)
                """,
                (torrent.magnet_uri, torrent.title, torrent.size, torrent.source),
            )
            conn.commit()

    def get_all_torrents(self) -> list[TorrentRecord]:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT magnet_uri, title, size, source FROM torrents")
            rows = cursor.fetchall()

            return [
                TorrentRecord(
                    magnet_uri=row["magnet_uri"],
                    title=row["title"],
                    size=row["size"],
                    source=row["source"],
                )  # iterterate overrr
                for row in rows
            ]
