"""
جدول توقيت المستخدم — يُخزَّن مرة واحدة ويُستخدم في كل التذكيرات
"""
from database.connection import get_db_conn


def create_user_timezone_table():
    conn = get_db_conn()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS user_timezone (
        user_id    INTEGER PRIMARY KEY,
        tz_offset  INTEGER NOT NULL DEFAULT 0,
        updated_at INTEGER DEFAULT (strftime('%s','now'))
    )
    """)
    conn.commit()
