from database.connection import get_db_conn


def create_azkar_tables():
    conn = get_db_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS azkar (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            text         TEXT    NOT NULL,
            repeat_count INTEGER NOT NULL DEFAULT 1,
            zikr_type    INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS azkar_progress (
            user_id    INTEGER NOT NULL,
            zikr_type  INTEGER NOT NULL,
            zikr_index INTEGER NOT NULL DEFAULT 0,
            remaining  INTEGER NOT NULL DEFAULT -1,
            PRIMARY KEY (user_id, zikr_type)
        );

        CREATE TABLE IF NOT EXISTS azkar_reminders (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            azkar_type INTEGER NOT NULL,
            hour       INTEGER NOT NULL,
            minute     INTEGER NOT NULL,
            tz_offset  INTEGER NOT NULL DEFAULT 0,
            created_at TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_azkar_type      ON azkar(zikr_type);
        CREATE INDEX IF NOT EXISTS idx_azkar_rem_user  ON azkar_reminders(user_id);
    """)
    conn.commit()
