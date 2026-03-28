import sqlite3
from core.config import DB_NAME

_conn = None

def get_db_conn():
    global _conn

    if _conn is None:
        _conn = sqlite3.connect(
            DB_NAME,
            check_same_thread=False
        )

        _conn.execute("PRAGMA foreign_keys = ON")
        _conn.execute("PRAGMA journal_mode = WAL")
        _conn.execute("PRAGMA synchronous = NORMAL")

        _conn.row_factory = sqlite3.Row

    return _conn
