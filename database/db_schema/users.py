from ..connection import get_db_conn

def create_users_table():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # TABLE: users
    # PURPOSE: Central identity table. Every Telegram user who
    #          interacts with the bot gets exactly one row here.
    #          All other tables reference users via user_id (FK).
    #
    # COLUMNS:
    #   id       — Internal autoincrement PK. Used for internal joins.
    #   user_id  — Telegram user ID. The external unique identifier.
    #   name     — User's display name (first + last). Updated on every message.
    #   username — Telegram @username. NULL if the user has none set.
    # ─────────────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id  INTEGER NOT NULL UNIQUE,
        name     TEXT    NOT NULL DEFAULT '',
        username TEXT    DEFAULT NULL
    );
    ''')

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
    """)

    conn.commit()
