# import sqlite3
# import threading
# from core.config import DB_NAME

# _local = threading.local()

# def get_db_conn():
#     if not hasattr(_local, "conn") or _local.conn is None:
#         _local.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
#         _local.conn.execute("PRAGMA foreign_keys = ON")
#         _local.conn.execute("PRAGMA journal_mode = WAL")
#         _local.conn.execute("PRAGMA synchronous = NORMAL")
#         _local.conn.row_factory = sqlite3.Row
#     return _local.conn

# def close_db_conn():
#     if hasattr(_local, "conn") and _local.conn:
#         _local.conn.close()
#         _local.conn = None

import sqlite3
import threading
from core.config import DB_NAME

# لكل Thread اتصال منفصل
_local = threading.local()

def get_db_conn():
    """
    Returns a thread-local SQLite connection.
    Ensures foreign keys, WAL mode, and row_factory (dict-like access) are set.
    """
    if getattr(_local, "conn", None) is None:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.row_factory = sqlite3.Row  # هذا يسمح بالوصول للقيم كـ dict
        _local.conn = conn
    return _local.conn

def close_db_conn():
    """
    Closes the thread-local connection if it exists.
    """
    conn = getattr(_local, "conn", None)
    if conn:
        conn.close()
        _local.conn = None
