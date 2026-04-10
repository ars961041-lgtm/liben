"""
جدول توقيت المستخدم — يُخزَّن مرة واحدة ويُستخدم في كل التذكيرات
"""
from database.connection import get_db_conn


def create_user_timezone_table():
    conn = get_db_conn()

    # ─────────────────────────────────────────────────────────────
    # TABLE: user_timezone
    # PURPOSE: Stores each user's UTC offset so reminders and
    #          scheduled messages fire at the correct local time.
    #          One row per user. Timezone is never duplicated in
    #          other tables — always fetched from here.
    #
    # COLUMNS:
    #   id         — Internal autoincrement PK.
    #   user_id    — References users.user_id. One row per user.
    #   tz_offset  — UTC offset in MINUTES (e.g. UTC+3 = 180).
    #   updated_at — Unix timestamp of the last update.
    # ─────────────────────────────────────────────────────────────
    conn.execute("""
    CREATE TABLE IF NOT EXISTS user_timezone (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL UNIQUE,
        tz_offset  INTEGER NOT NULL DEFAULT 0,
        updated_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)
    conn.commit()
