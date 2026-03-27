from ..connection import get_db_conn

from .users_queries import get_or_create_user_id

def upsert_group_member(group_id, user_id, full_name, group_name):

        conn = get_db_conn()
        cursor = conn.cursor()

        db_user_id = get_or_create_user_id(user_id)

        cursor.execute(
            "INSERT OR IGNORE INTO groups (id, name) VALUES (?, ?)",
            (group_id, group_name)
        )

        cursor.execute(
            """
            INSERT INTO users_name (user_id, name)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET name=excluded.name
            """,
            (user_id, full_name)
        )

        cursor.execute(
            """
            INSERT INTO group_members (user_id, group_id, message_count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, group_id)
            DO UPDATE SET message_count = message_count + 1
            """,
            (db_user_id, group_id)
        )

        conn.commit()
        
def get_top_group_members(group_id, limit=10):
        conn = get_db_conn()
        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT u.user_id, gm.message_count, un.name
            FROM group_members gm
            JOIN users u ON gm.user_id = u.id
            LEFT JOIN users_name un ON u.user_id = un.user_id
            WHERE gm.group_id = ?
            ORDER BY gm.message_count DESC
            LIMIT ?
            ''',
            (group_id, limit)
        )

        return cursor.fetchall()
def get_group_total_messages(group_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(message_count) FROM group_members WHERE group_id = ?', (group_id,))
    return cursor.fetchone()[0] or 0