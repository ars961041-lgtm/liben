"""
قاعدة بيانات قوانين المجموعات.
"""
from database.connection import get_db_conn


def create_rules_table():
    conn = get_db_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS group_rules (
            chat_id     INTEGER PRIMARY KEY,
            rules       TEXT    NOT NULL,
            updated_by  INTEGER NOT NULL,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            auto_send   INTEGER DEFAULT 0
        )
    """)
    conn.commit()


def get_rules(chat_id: int) -> dict | None:
    cur = get_db_conn().cursor()
    cur.execute("SELECT * FROM group_rules WHERE chat_id=?", (chat_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def set_rules(chat_id: int, rules: str, updated_by: int):
    conn = get_db_conn()
    conn.execute(
        """INSERT INTO group_rules (chat_id, rules, updated_by, updated_at)
           VALUES (?,?,?, datetime('now'))
           ON CONFLICT(chat_id) DO UPDATE SET
               rules=excluded.rules,
               updated_by=excluded.updated_by,
               updated_at=excluded.updated_at""",
        (chat_id, rules, updated_by),
    )
    conn.commit()


def delete_rules(chat_id: int):
    conn = get_db_conn()
    conn.execute("DELETE FROM group_rules WHERE chat_id=?", (chat_id,))
    conn.commit()


def set_auto_send(chat_id: int, value: int):
    conn = get_db_conn()
    conn.execute(
        "UPDATE group_rules SET auto_send=? WHERE chat_id=?",
        (value, chat_id),
    )
    conn.commit()
