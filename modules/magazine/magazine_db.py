"""
قاعدة بيانات المجلة اليومية والهدايا.
"""
import time
from database.connection import get_db_conn


def create_magazine_tables():
    conn = get_db_conn()
    cur  = conn.cursor()

    # منشورات المجلة اليومية
    cur.execute("""
        CREATE TABLE IF NOT EXISTS magazine_posts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            title      TEXT    NOT NULL,
            body       TEXT    NOT NULL,
            author_id  INTEGER NOT NULL,
            created_at INTEGER DEFAULT (strftime('%s','now'))
        )
    """)

    # سجل الهدايا الموزعة
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gift_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            gift_type    TEXT    NOT NULL,   -- money / city_level / troops
            value        TEXT    NOT NULL,   -- JSON أو قيمة نصية
            note         TEXT    DEFAULT '',
            sent_by      INTEGER NOT NULL,
            recipients   INTEGER DEFAULT 0,
            sent_at      INTEGER DEFAULT (strftime('%s','now'))
        )
    """)

    conn.commit()


# ── Magazine CRUD ─────────────────────────────────────────────

def add_post(title: str, body: str, author_id: int) -> int:
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute("INSERT INTO magazine_posts (title, body, author_id) VALUES (?,?,?)",
                (title, body, author_id))
    conn.commit()
    return cur.lastrowid


def get_today_posts() -> list[dict]:
    conn = get_db_conn()
    cur  = conn.cursor()
    # منشورات آخر 24 ساعة
    since = int(time.time()) - 86400
    cur.execute("SELECT * FROM magazine_posts WHERE created_at >= ? ORDER BY created_at DESC",
                (since,))
    return [dict(r) for r in cur.fetchall()]


def get_all_posts(limit=20) -> list[dict]:
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM magazine_posts ORDER BY created_at DESC LIMIT ?", (limit,))
    return [dict(r) for r in cur.fetchall()]


def delete_post(post_id: int) -> bool:
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute("DELETE FROM magazine_posts WHERE id=?", (post_id,))
    conn.commit()
    return cur.rowcount > 0


# ── Gift log ─────────────────────────────────────────────────

def log_gift(gift_type: str, value: str, note: str,
             sent_by: int, recipients: int) -> int:
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO gift_log (gift_type, value, note, sent_by, recipients)
        VALUES (?,?,?,?,?)
    """, (gift_type, value, note, sent_by, recipients))
    conn.commit()
    return cur.lastrowid


def get_gift_log(limit=10) -> list[dict]:
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM gift_log ORDER BY sent_at DESC LIMIT ?", (limit,))
    return [dict(r) for r in cur.fetchall()]


# ── Helpers ───────────────────────────────────────────────────

def get_all_user_ids() -> list[int]:
    """يرجع كل user_id من جدول user_accounts (لاعبون لديهم حسابات)."""
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute("SELECT user_id FROM user_accounts")
    return [r[0] for r in cur.fetchall()]


def get_all_city_ids_with_owner() -> list[dict]:
    """يرجع كل مدينة مع owner_id."""
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute("SELECT id AS city_id, owner_id FROM cities")
    return [dict(r) for r in cur.fetchall()]
