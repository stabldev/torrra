import sqlite3
from contextlib import contextmanager, suppress
from pathlib import Path

from platformdirs import user_data_dir

DB_DIR = Path(user_data_dir("torrra"))
DB_FILE = DB_DIR / "torrra.db"


@contextmanager
def get_db_connection():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS torrents (
                magnet_uri TEXT PRIMARY KEY,
                title TEXT,
                size REAL,
                source TEXT,
                is_paused BOOLEAN DEFAULT 0,
                is_notified BOOLEAN DEFAULT 0,
                file_priorities TEXT DEFAULT NULL,
                upload_limit INTEGER DEFAULT NULL,
                download_limit INTEGER DEFAULT NULL,
                save_path TEXT DEFAULT NULL,
                max_ratio REAL DEFAULT NULL,
                max_seeding_time INTEGER DEFAULT NULL,
                sequential_download BOOLEAN DEFAULT 0
            )
            """
        )
        # migration code
        with suppress(sqlite3.OperationalError):
            cursor.execute(
                "ALTER TABLE torrents ADD COLUMN is_notified BOOLEAN DEFAULT 0"
            )
        with suppress(sqlite3.OperationalError):
            cursor.execute(
                "ALTER TABLE torrents ADD COLUMN file_priorities TEXT DEFAULT NULL"
            )
        columns = {
            row[1] for row in cursor.execute("PRAGMA table_info(torrents)").fetchall()
        }
        if "upload_limit" not in columns:
            cursor.execute(
                "ALTER TABLE torrents ADD COLUMN upload_limit INTEGER DEFAULT NULL"
            )
        if "download_limit" not in columns:
            cursor.execute(
                "ALTER TABLE torrents ADD COLUMN download_limit INTEGER DEFAULT NULL"
            )
        if "save_path" not in columns:
            cursor.execute(
                "ALTER TABLE torrents ADD COLUMN save_path TEXT DEFAULT NULL"
            )
        if "max_ratio" not in columns:
            cursor.execute(
                "ALTER TABLE torrents ADD COLUMN max_ratio REAL DEFAULT NULL"
            )
        if "max_seeding_time" not in columns:
            cursor.execute(
                "ALTER TABLE torrents ADD COLUMN max_seeding_time INTEGER DEFAULT NULL"
            )
        if "sequential_download" not in columns:
            cursor.execute(
                "ALTER TABLE torrents ADD COLUMN sequential_download BOOLEAN DEFAULT 0"
            )
        conn.commit()
