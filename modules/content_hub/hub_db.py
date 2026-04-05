"""
قاعدة بيانات مركز المحتوى — ملف منفصل: content_hub.db
"""
import sqlite3
import threading
import os
import uuid

from core.config import DB_CONTENT


_local   = threading.local()

# ── الفاصل بين المحتويات المتعددة ──
CONTENT_SEPARATOR = "---"

# ── أنواع المحتوى المدعومة ──
CONTENT_TYPES = {
    "اقتباس":  "quotes",
    "نوادر":   "anecdotes",
    "قصص":    "stories",
    "حكمة":   "wisdom",
}

# ── أسماء عربية للعرض ──
TYPE_LABELS = {
    "quotes":    "💬 اقتباس",
    "anecdotes": "😄 نادرة",
    "stories":   "📖 قصة",
    "wisdom":    "🌟 حكمة",
}


def _get_conn() -> sqlite3.Connection:
    if getattr(_local, "conn", None) is None:
        conn = sqlite3.connect(DB_CONTENT, check_same_thread=False, timeout=10)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return _local.conn


def create_tables():
    conn = _get_conn()
    cur  = conn.cursor()
    for table in CONTENT_TYPES.values():
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                content    TEXT    NOT NULL,
                random_key TEXT    NOT NULL DEFAULT (lower(hex(randomblob(8))))
            )
        """)
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{table}_rk ON {table}(random_key)"
        )
    conn.commit()


# ══════════════════════════════════════════
# استعلامات
# ══════════════════════════════════════════

def get_random(table: str) -> dict | None:
    """
    يجلب صفاً عشوائياً بكفاءة عبر random_key بدلاً من ORDER BY RANDOM().
    """
    conn = _get_conn()
    cur  = conn.cursor()
    # نختار random_key عشوائياً ثم نأخذ أقرب صف أكبر منه
    rk = uuid.uuid4().hex[:16]
    cur.execute(
        f"SELECT * FROM {table} WHERE random_key >= ? ORDER BY random_key LIMIT 1",
        (rk,),
    )
    row = cur.fetchone()
    if not row:
        # إذا لم يوجد صف أكبر — نأخذ الأول
        cur.execute(f"SELECT * FROM {table} ORDER BY random_key LIMIT 1")
        row = cur.fetchone()
    return dict(row) if row else None


def get_by_id(table: str, row_id: int) -> dict | None:
    cur = _get_conn().cursor()
    cur.execute(f"SELECT * FROM {table} WHERE id=?", (row_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def insert_content(table: str, content: str) -> int:
    conn = _get_conn()
    cur  = conn.cursor()
    rk   = uuid.uuid4().hex[:16]
    cur.execute(
        f"INSERT INTO {table} (content, random_key) VALUES (?,?)",
        (content.strip(), rk),
    )
    conn.commit()
    return cur.lastrowid


def update_content(table: str, row_id: int, content: str) -> bool:
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute(f"UPDATE {table} SET content=? WHERE id=?", (content.strip(), row_id))
    conn.commit()
    return cur.rowcount > 0


def delete_content(table: str, row_id: int) -> bool:
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute(f"DELETE FROM {table} WHERE id=?", (row_id,))
    conn.commit()
    return cur.rowcount > 0


def count_rows(table: str) -> int:
    cur = _get_conn().cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return cur.fetchone()[0]
