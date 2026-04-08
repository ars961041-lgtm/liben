"""
استعلامات توقيت المستخدم
"""
from database.connection import get_db_conn


def get_user_tz(user_id: int) -> int | None:
    """يرجع tz_offset بالدقائق، أو None إذا لم يُحدَّد بعد."""
    cur = get_db_conn().cursor()
    cur.execute("SELECT tz_offset FROM user_timezone WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    return row[0] if row else None


def set_user_tz(user_id: int, tz_offset: int):
    """يحفظ أو يحدّث توقيت المستخدم (بالدقائق)."""
    conn = get_db_conn()
    conn.execute("""
        INSERT INTO user_timezone (user_id, tz_offset, updated_at)
        VALUES (?, ?, strftime('%s','now'))
        ON CONFLICT(user_id) DO UPDATE SET
            tz_offset  = excluded.tz_offset,
            updated_at = excluded.updated_at
    """, (user_id, tz_offset))
    conn.commit()
