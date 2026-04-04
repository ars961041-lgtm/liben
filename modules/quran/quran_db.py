"""
قاعدة بيانات نظام إنجاز القرآن — content_hub.db (جداول مشتركة)
"""
import sqlite3
import threading
from typing import Optional

from core.config import DB_CONTENT

_local   = threading.local()

# ── فاصل التحرير الجماعي ──
BULK_SEPARATOR = "---"

# ── أنواع التفسير المدعومة ──
TAFSEER_TYPES = {
    "المختصر":  "tafseer_mukhtasar",
    "السعدي":   "tafseer_saadi",
    "ابن كثير": "tafseer_ibn_kathir",
    "الميسر":   "tafseer_muyassar",
}


def _get_conn() -> sqlite3.Connection:
    if getattr(_local, "conn", None) is None:
        conn = sqlite3.connect(DB_CONTENT, check_same_thread=False)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return _local.conn


def create_tables():
    conn = _get_conn()
    cur  = conn.cursor()

    # ── الآيات ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ayat (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        sura_name            TEXT    NOT NULL,
        ayah_number          INTEGER NOT NULL,
        text_with_tashkeel   TEXT    NOT NULL,
        text_without_tashkeel TEXT   NOT NULL,
        tafseer_mukhtasar    TEXT    DEFAULT NULL,
        tafseer_saadi        TEXT    DEFAULT NULL,
        tafseer_ibn_kathir   TEXT    DEFAULT NULL,
        tafseer_muyassar     TEXT    DEFAULT NULL,
        UNIQUE(sura_name, ayah_number)
    )
    """)

    # ── تقدم القراءة ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_quran_progress (
        user_id     INTEGER PRIMARY KEY,
        last_ayah_id INTEGER NOT NULL DEFAULT 1,
        message_id  INTEGER DEFAULT NULL
    )
    """)

    # ── المفضلة ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_favorites (
        user_id  INTEGER NOT NULL,
        ayah_id  INTEGER NOT NULL,
        added_at INTEGER DEFAULT (strftime('%s','now')),
        PRIMARY KEY (user_id, ayah_id),
        FOREIGN KEY (ayah_id) REFERENCES ayat(id)
    )
    """)

    # ── فهارس ──
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ayat_sura ON ayat(sura_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ayat_search ON ayat(text_without_tashkeel)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fav_user ON user_favorites(user_id)")

    conn.commit()


# ══════════════════════════════════════════
# الآيات
# ══════════════════════════════════════════

def get_ayah(ayah_id: int) -> Optional[dict]:
    cur = _get_conn().cursor()
    cur.execute("SELECT * FROM ayat WHERE id=?", (ayah_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_ayah_by_sura_number(sura_name: str, ayah_number: int) -> Optional[dict]:
    cur = _get_conn().cursor()
    cur.execute(
        "SELECT * FROM ayat WHERE sura_name=? AND ayah_number=?",
        (sura_name, ayah_number),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def get_first_ayah() -> Optional[dict]:
    cur = _get_conn().cursor()
    cur.execute("SELECT * FROM ayat ORDER BY id ASC LIMIT 1")
    row = cur.fetchone()
    return dict(row) if row else None


def get_next_ayah(current_id: int) -> Optional[dict]:
    cur = _get_conn().cursor()
    cur.execute("SELECT * FROM ayat WHERE id > ? ORDER BY id ASC LIMIT 1", (current_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_prev_ayah(current_id: int) -> Optional[dict]:
    cur = _get_conn().cursor()
    cur.execute("SELECT * FROM ayat WHERE id < ? ORDER BY id DESC LIMIT 1", (current_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_total_ayat() -> int:
    cur = _get_conn().cursor()
    cur.execute("SELECT COUNT(*) FROM ayat")
    return cur.fetchone()[0]


def search_ayat(normalized_query: str) -> list[dict]:
    """يبحث في النص بدون تشكيل."""
    cur = _get_conn().cursor()
    cur.execute(
        "SELECT * FROM ayat WHERE text_without_tashkeel LIKE ? ORDER BY id ASC LIMIT 50",
        (f"%{normalized_query}%",),
    )
    return [dict(r) for r in cur.fetchall()]


def insert_ayah(sura_name: str, ayah_number: int,
                text_with: str, text_without: str) -> int:
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO ayat (sura_name, ayah_number, text_with_tashkeel, text_without_tashkeel)
        VALUES (?,?,?,?)
    """, (sura_name, ayah_number, text_with.strip(), text_without.strip()))
    conn.commit()
    return cur.lastrowid or 0


def update_ayah_text(ayah_id: int, text_with: str, text_without: str) -> bool:
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute(
        "UPDATE ayat SET text_with_tashkeel=?, text_without_tashkeel=? WHERE id=?",
        (text_with.strip(), text_without.strip(), ayah_id),
    )
    conn.commit()
    return cur.rowcount > 0


def update_tafseer(ayah_id: int, tafseer_col: str, content: str) -> bool:
    if tafseer_col not in TAFSEER_TYPES.values():
        return False
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute(
        f"UPDATE ayat SET {tafseer_col}=? WHERE id=?",
        (content.strip(), ayah_id),
    )
    conn.commit()
    return cur.rowcount > 0


def get_all_suras() -> list[str]:
    cur = _get_conn().cursor()
    cur.execute("SELECT DISTINCT sura_name FROM ayat ORDER BY id ASC")
    return [r[0] for r in cur.fetchall()]


# ══════════════════════════════════════════
# تقدم المستخدم
# ══════════════════════════════════════════

def get_progress(user_id: int) -> Optional[dict]:
    cur = _get_conn().cursor()
    cur.execute("SELECT * FROM user_quran_progress WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def save_progress(user_id: int, ayah_id: int, message_id: int = None):
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO user_quran_progress (user_id, last_ayah_id, message_id)
        VALUES (?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET last_ayah_id=excluded.last_ayah_id,
                                           message_id=excluded.message_id
    """, (user_id, ayah_id, message_id))
    conn.commit()


def reset_progress(user_id: int):
    first = get_first_ayah()
    first_id = first["id"] if first else 1
    save_progress(user_id, first_id, None)


# ══════════════════════════════════════════
# المفضلة
# ══════════════════════════════════════════

def add_favorite(user_id: int, ayah_id: int) -> bool:
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO user_favorites (user_id, ayah_id) VALUES (?,?)",
        (user_id, ayah_id),
    )
    conn.commit()
    return cur.rowcount > 0


def remove_favorite(user_id: int, ayah_id: int) -> bool:
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute(
        "DELETE FROM user_favorites WHERE user_id=? AND ayah_id=?",
        (user_id, ayah_id),
    )
    conn.commit()
    return cur.rowcount > 0


def is_favorite(user_id: int, ayah_id: int) -> bool:
    cur = _get_conn().cursor()
    cur.execute(
        "SELECT 1 FROM user_favorites WHERE user_id=? AND ayah_id=?",
        (user_id, ayah_id),
    )
    return cur.fetchone() is not None


def get_favorites(user_id: int) -> list[dict]:
    cur = _get_conn().cursor()
    cur.execute("""
        SELECT a.* FROM user_favorites f
        JOIN ayat a ON f.ayah_id = a.id
        WHERE f.user_id=?
        ORDER BY f.added_at ASC
    """, (user_id,))
    return [dict(r) for r in cur.fetchall()]
