"""
قاعدة بيانات مركز المحتوى — ملف منفصل: content_hub.db
"""
import sqlite3
import threading
import os

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
    "شعر":    "poetry",
    "أذكار":  "azkar",
}

# ── أسماء عربية للعرض ──
TYPE_LABELS = {
    "quotes":    "💬 اقتباس",
    "anecdotes": "📔 نادرة",
    "stories":   "📖 قصة",
    "wisdom":    "🌟 حكمة",
    "poetry":    "📜 شعر",
    "azkar":     "📿 ذكر",
}

# ── أنواع المحتوى المستثناة من النشر التلقائي ──
AUTO_POST_EXCLUDED = {"azkar"}


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
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT    NOT NULL UNIQUE
            )
        """)
    # linked_channels: channel_id → content_type mapping
    cur.execute("""
        CREATE TABLE IF NOT EXISTS linked_channels (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id   INTEGER NOT NULL UNIQUE,
            channel_name TEXT    DEFAULT '',
            content_type TEXT    NOT NULL,
            linked_at    INTEGER DEFAULT (strftime('%s','now'))
        )
    """)
    conn.commit()


# ══════════════════════════════════════════
# استعلامات
# ══════════════════════════════════════════

def get_random_row(table: str) -> dict | None:
    """
    يجلب صفاً عشوائياً بكفاءة دون الحاجة لعمود random_key.
    يستخدم OFFSET عشوائي بدلاً من ORDER BY RANDOM().
    """
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute(
        f"SELECT * FROM {table} LIMIT 1 OFFSET ABS(RANDOM()) % MAX(1, (SELECT COUNT(*) FROM {table}))"
    )
    row = cur.fetchone()
    return dict(row) if row else None


def get_random(table: str) -> dict | None:
    """Alias for get_random_row — kept for backward compatibility."""
    return get_random_row(table)


def get_by_id(table: str, row_id: int) -> dict | None:
    cur = _get_conn().cursor()
    cur.execute(f"SELECT * FROM {table} WHERE id=?", (row_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def insert_content(table: str, content: str) -> int:
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute(
        f"INSERT OR IGNORE INTO {table} (content) VALUES (?)",
        (content.strip(),),
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


# ══════════════════════════════════════════
# linked_channels
# ══════════════════════════════════════════

def link_channel(channel_id: int, content_type: str, channel_name: str = "") -> bool:
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO linked_channels (channel_id, content_type, channel_name)
        VALUES (?, ?, ?)
        ON CONFLICT(channel_id) DO UPDATE SET content_type = excluded.content_type,
                                               channel_name = excluded.channel_name
    """, (channel_id, content_type, channel_name))
    conn.commit()
    return True


def unlink_channel(channel_id: int) -> bool:
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute("DELETE FROM linked_channels WHERE channel_id = ?", (channel_id,))
    conn.commit()
    return cur.rowcount > 0


def get_linked_channel(channel_id: int) -> dict | None:
    cur = _get_conn().cursor()
    cur.execute("SELECT * FROM linked_channels WHERE channel_id = ?", (channel_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_all_linked_channels() -> list:
    cur = _get_conn().cursor()
    cur.execute("SELECT * FROM linked_channels ORDER BY linked_at DESC")
    return [dict(r) for r in cur.fetchall()]


def upsert_content_by_text(table: str, old_text: str, new_text: str) -> bool:
    """يُحدّث محتوى موجود بالنص القديم — يُستخدم عند تعديل منشور القناة."""
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute(f"UPDATE {table} SET content = ? WHERE content = ?",
                (new_text.strip(), old_text.strip()))
    conn.commit()
    return cur.rowcount > 0
