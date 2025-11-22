import sqlite3
from contextlib import contextmanager
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
                is_paused BOOLEAN DEFAULT 0
            )
            """
        )
        conn.commit()
