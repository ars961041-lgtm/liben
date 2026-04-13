"""
اتصال قاعدة البيانات الرئيسية — thread-local مع WAL وtimeout
يُنشئ ملف DB تلقائياً إذا لم يكن موجوداً.
"""
import os
import sqlite3
import threading
import time
from core.config import DB_NAME

_local = threading.local()

# تتبع جميع الاتصالات النشطة عبر كل الـ threads
_CONNECTIONS_LOCK = threading.Lock()
ACTIVE_CONNECTIONS: set = set()

# قفل عالمي للكتابات المتزامنة (يمنع database is locked)
_WRITE_LOCK = threading.Lock()


def _ensure_db_exists(path: str):
    """يُنشئ ملف DB وأي مجلدات مطلوبة إذا لم تكن موجودة."""
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def get_db_conn() -> sqlite3.Connection:
    """
    يرجع اتصالاً thread-local.
    WAL + foreign_keys + row_factory مُفعَّلة دائماً.
    """
    if getattr(_local, "conn", None) is None:
        _ensure_db_exists(DB_NAME)
        conn = sqlite3.connect(DB_NAME, check_same_thread=False, timeout=10)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
        with _CONNECTIONS_LOCK:
            ACTIVE_CONNECTIONS.add(conn)
    return _local.conn


def db_write(func, *args, max_retries: int = 3, retry_delay: float = 0.15, **kwargs):
    """
    ينفّذ دالة كتابة مع إعادة المحاولة عند 'database is locked'.
    يستخدم قفلاً عالمياً لتسلسل الكتابات المتزامنة.

    الاستخدام:
        db_write(lambda: conn.execute("UPDATE ..."))
    """
    with _WRITE_LOCK:
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower():
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    print(f"[db_write] database is locked after {max_retries} attempts")
                raise


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
    close_db_conn()
    with _CONNECTIONS_LOCK:
        conns = list(ACTIVE_CONNECTIONS)
        ACTIVE_CONNECTIONS.clear()
    for conn in conns:
        try:
            conn.close()
        except Exception:
            pass
