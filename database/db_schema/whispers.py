"""
database/db_schema/whispers.py

جدول الهمسات.

COLUMNS:
  id         — PK تلقائي
  from_user  — مُرسِل الهمسة (FK → users.user_id)
  to_user    — مُستقبِل الهمسة، NULL = همسة عامة (@all)
  group_id   — المجموعة (FK → groups.group_id)
  message    — نص الهمسة (max 200 حرف)
  created_at — Unix timestamp
  is_read    — 0 = لم تُقرأ، 1 = قُرئت
  reply_to   — id الهمسة الأصلية للردود، NULL إذا لم تكن رداً
"""

from ..connection import get_db_conn


def create_whispers_table():
    conn   = get_db_conn()
    cursor = conn.cursor()

    # to_user يقبل NULL للهمسات العامة (@all)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS whispers (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user  INTEGER NOT NULL,
        to_user    INTEGER DEFAULT NULL,
        group_id   INTEGER NOT NULL,
        message    TEXT    NOT NULL,
        created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
        is_read    INTEGER NOT NULL DEFAULT 0,
        reply_to   INTEGER DEFAULT NULL,
        FOREIGN KEY (from_user) REFERENCES users(user_id),
        FOREIGN KEY (to_user)   REFERENCES users(user_id),
        FOREIGN KEY (group_id)  REFERENCES groups(group_id),
        FOREIGN KEY (reply_to)  REFERENCES whispers(id)
    );
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_whispers_to_user
        ON whispers(to_user, is_read);
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_whispers_group
        ON whispers(group_id, created_at);
    """)

    conn.commit()

    # Safe migration for existing databases: make to_user nullable
    # SQLite doesn't support ALTER COLUMN, so we check if migration is needed
    # by inspecting the column info and recreating if necessary.
    try:
        cursor.execute("PRAGMA table_info(whispers)")
        cols = {row["name"]: dict(row) for row in cursor.fetchall()}
        to_user_col = cols.get("to_user", {})
        # If notnull=1, the column is NOT NULL — needs migration
        if to_user_col.get("notnull", 0) == 1:
            cursor.executescript("""
                BEGIN;
                ALTER TABLE whispers RENAME TO whispers_old;
                CREATE TABLE whispers (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_user  INTEGER NOT NULL,
                    to_user    INTEGER DEFAULT NULL,
                    group_id   INTEGER NOT NULL,
                    message    TEXT    NOT NULL,
                    created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                    is_read    INTEGER NOT NULL DEFAULT 0,
                    reply_to   INTEGER DEFAULT NULL,
                    FOREIGN KEY (from_user) REFERENCES users(user_id),
                    FOREIGN KEY (to_user)   REFERENCES users(user_id),
                    FOREIGN KEY (group_id)  REFERENCES groups(group_id),
                    FOREIGN KEY (reply_to)  REFERENCES whispers(id)
                );
                INSERT INTO whispers SELECT * FROM whispers_old;
                DROP TABLE whispers_old;
                COMMIT;
            """)
            print("[whispers] migrated to_user to nullable")
    except Exception as e:
        print(f"[whispers] migration check: {e}")
