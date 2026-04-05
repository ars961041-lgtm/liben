"""
اتصال قاعدة البيانات الرئيسية — thread-local مع WAL وtimeout
"""
import sqlite3
import threading
from core.config import DB_NAME

_local = threading.local()

# تتبع جميع الاتصالات النشطة عبر كل الـ threads
_CONNECTIONS_LOCK = threading.Lock()
ACTIVE_CONNECTIONS: set = set()


def get_db_conn() -> sqlite3.Connection:
    """
    يرجع اتصالاً thread-local.
    WAL + foreign_keys + row_factory مُفعَّلة دائماً.
    """
    if getattr(_local, "conn", None) is None:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False, timeout=10)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
        with _CONNECTIONS_LOCK:
            ACTIVE_CONNECTIONS.add(conn)
    return _local.conn


def close_db_conn():
    """يغلق الاتصال الحالي للـ thread."""
    conn = getattr(_local, "conn", None)
    if conn:
        try:
            conn.close()
        except Exception:
            pass
        with _CONNECTIONS_LOCK:
            ACTIVE_CONNECTIONS.discard(conn)
        _local.conn = None


def close_all_connections():
    """
    يُغلق جميع الاتصالات النشطة عبر كل الـ threads.
    استدعِه قبل حذف ملف DB.
    """
    # أغلق اتصال الـ thread الحالي أولاً
    close_db_conn()
    # ثم أغلق كل الاتصالات المسجّلة
    with _CONNECTIONS_LOCK:
        conns = list(ACTIVE_CONNECTIONS)
        ACTIVE_CONNECTIONS.clear()
    for conn in conns:
        try:
            conn.close()
        except Exception:
            pass
