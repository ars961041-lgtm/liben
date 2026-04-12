"""
news_db.py — Extended magazine database for the global news system.

Tables:
  news_posts     — All auto-generated and manual news posts with metadata.
  news_cooldowns — Per-event-type dedup cooldowns (anti-spam).

Importance levels: LOW | MEDIUM | HIGH | CRITICAL
Categories:        war | economy | rankings | alliance | rebellion | event | general
"""
import time
from database.connection import get_db_conn


IMPORTANCE_LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
CATEGORIES = ("war", "economy", "rankings", "alliance", "rebellion", "event", "general")

# Cooldown in seconds per event_type key (anti-spam)
EVENT_COOLDOWNS = {
    "war_start":          300,    # 5 min — one post per war start
    "war_end":            300,
    "war_betrayal":       600,
    "alliance_victory":   300,
    "alliance_collapse":  600,
    "richest_change":     3600,   # 1 hour
    "rankings_weekly":    0,      # no cooldown (scheduled)
    "rankings_monthly":   0,
    "rebellion":          1800,   # 30 min per city
    "global_event":       1800,
    "economy_shock":      3600,
    "treasury_milestone": 1800,
}


def create_news_tables():
    conn = get_db_conn()
    cur  = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS news_posts (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        title       TEXT    NOT NULL,
        body        TEXT    NOT NULL,
        author_id   INTEGER NOT NULL DEFAULT 0,
        importance  TEXT    NOT NULL DEFAULT 'MEDIUM',
        category    TEXT    NOT NULL DEFAULT 'general',
        event_type  TEXT    DEFAULT '',
        event_ref   TEXT    DEFAULT '',
        created_at  INTEGER DEFAULT (strftime('%s','now'))
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS news_cooldowns (
        event_key   TEXT    PRIMARY KEY,
        last_posted INTEGER NOT NULL DEFAULT 0
    )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_news_category   ON news_posts(category)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_news_importance ON news_posts(importance)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_news_created    ON news_posts(created_at DESC)")

    conn.commit()


# ── CRUD ──────────────────────────────────────────────────────────

def add_news_post(title: str, body: str, importance: str = "MEDIUM",
                  category: str = "general", event_type: str = "",
                  event_ref: str = "", author_id: int = 0) -> int:
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO news_posts (title, body, author_id, importance, category, event_type, event_ref)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (title, body, author_id, importance, category, event_type, event_ref))
    conn.commit()
    return cur.lastrowid


def get_latest_posts(limit: int = 10, category: str = None,
                     importance: str = None) -> list[dict]:
    conn = get_db_conn()
    cur  = conn.cursor()
    where, params = [], []
    if category:
        where.append("category = ?")
        params.append(category)
    if importance:
        where.append("importance = ?")
        params.append(importance)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    cur.execute(f"""
        SELECT * FROM news_posts {clause}
        ORDER BY created_at DESC LIMIT ?
    """, params + [limit])
    return [dict(r) for r in cur.fetchall()]


def get_top_posts(limit: int = 10) -> list[dict]:
    """Returns HIGH + CRITICAL posts from the last 7 days."""
    conn = get_db_conn()
    cur  = conn.cursor()
    since = int(time.time()) - 7 * 86400
    cur.execute("""
        SELECT * FROM news_posts
        WHERE importance IN ('HIGH','CRITICAL') AND created_at >= ?
        ORDER BY created_at DESC LIMIT ?
    """, (since, limit))
    return [dict(r) for r in cur.fetchall()]


def get_today_news() -> list[dict]:
    conn = get_db_conn()
    cur  = conn.cursor()
    since = int(time.time()) - 86400
    cur.execute("""
        SELECT * FROM news_posts WHERE created_at >= ?
        ORDER BY created_at DESC
    """, (since,))
    return [dict(r) for r in cur.fetchall()]


def delete_news_post(post_id: int) -> bool:
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute("DELETE FROM news_posts WHERE id = ?", (post_id,))
    conn.commit()
    return cur.rowcount > 0


# ── Cooldown / dedup ──────────────────────────────────────────────

def can_post_event(event_key: str) -> bool:
    """Returns True if enough time has passed since the last post for this key."""
    base_type = event_key.split(":")[0]
    cooldown  = EVENT_COOLDOWNS.get(base_type, 300)
    if cooldown == 0:
        return True
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute("SELECT last_posted FROM news_cooldowns WHERE event_key = ?", (event_key,))
    row = cur.fetchone()
    if not row:
        return True
    return (int(time.time()) - row[0]) >= cooldown


def mark_event_posted(event_key: str):
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO news_cooldowns (event_key, last_posted)
        VALUES (?, ?)
        ON CONFLICT(event_key) DO UPDATE SET last_posted = excluded.last_posted
    """, (event_key, int(time.time())))
    conn.commit()
