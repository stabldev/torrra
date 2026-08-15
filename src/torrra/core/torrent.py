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
    def add_torrent(self, torrent: Torrent) -> None:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO torrents
                    (magnet_uri, title, size, source, selected_files)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    torrent.magnet_uri,
                    torrent.title,
                    torrent.size,
                    torrent.source,
                    _dumps_selection(torrent.selected_files),
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

    def update_torrent_selected_files(
        self, magnet_uri: str, selected_files: list[int] | None
    ) -> None:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE torrents SET selected_files = ? WHERE magnet_uri = ?",
                (_dumps_selection(selected_files), magnet_uri),
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
                    selected_files=_loads_selection(row["selected_files"]),
                )
                for row in rows
            ]


def _dumps_selection(selected_files: list[int] | None) -> str | None:
    return json.dumps(selected_files) if selected_files is not None else None


def _loads_selection(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None
