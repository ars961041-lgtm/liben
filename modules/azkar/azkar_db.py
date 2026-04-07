"""
عمليات قاعدة بيانات الأذكار — تستخدم قاعدة البيانات الرئيسية.
الجداول: azkar, azkar_progress, azkar_reminders
"""
from database.connection import get_db_conn


# ══════════════════════════════════════════
# أذكار CRUD
# ══════════════════════════════════════════

def get_azkar_list(zikr_type: int) -> list:
    """Returns ordered list of azkar dicts for the given type."""
    cur = get_db_conn().cursor()
    cur.execute(
        "SELECT id, text, repeat_count, zikr_type FROM azkar WHERE zikr_type=? ORDER BY id",
        (zikr_type,),
    )
    return [dict(r) for r in cur.fetchall()]


def get_zikr(zikr_id: int) -> dict | None:
    cur = get_db_conn().cursor()
    cur.execute("SELECT * FROM azkar WHERE id=?", (zikr_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def add_zikr(text: str, repeat_count: int, zikr_type: int) -> int:
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO azkar (text, repeat_count, zikr_type) VALUES (?,?,?)",
        (text.strip(), repeat_count, zikr_type),
    )
    conn.commit()
    return cur.lastrowid


def update_zikr(zikr_id: int, text: str, repeat_count: int) -> bool:
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        "UPDATE azkar SET text=?, repeat_count=? WHERE id=?",
        (text.strip(), repeat_count, zikr_id),
    )
    conn.commit()
    return cur.rowcount > 0


def delete_zikr(zikr_id: int) -> bool:
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute("DELETE FROM azkar WHERE id=?", (zikr_id,))
    conn.commit()
    return cur.rowcount > 0


# ══════════════════════════════════════════
# تقدم المستخدم
# ══════════════════════════════════════════

def get_progress(user_id: int, zikr_type: int) -> dict:
    cur = get_db_conn().cursor()
    cur.execute(
        "SELECT zikr_index, remaining FROM azkar_progress WHERE user_id=? AND zikr_type=?",
        (user_id, zikr_type),
    )
    row = cur.fetchone()
    return {"zikr_index": row["zikr_index"], "remaining": row["remaining"]} if row \
        else {"zikr_index": 0, "remaining": -1}


def save_progress(user_id: int, zikr_type: int, zikr_index: int, remaining: int):
    conn = get_db_conn()
    conn.execute(
        """INSERT INTO azkar_progress (user_id, zikr_type, zikr_index, remaining)
           VALUES (?,?,?,?)
           ON CONFLICT(user_id, zikr_type) DO UPDATE SET
               zikr_index=excluded.zikr_index,
               remaining=excluded.remaining""",
        (user_id, zikr_type, zikr_index, remaining),
    )
    conn.commit()


def reset_progress(user_id: int, zikr_type: int):
    conn = get_db_conn()
    conn.execute(
        "DELETE FROM azkar_progress WHERE user_id=? AND zikr_type=?",
        (user_id, zikr_type),
    )
    conn.commit()


# ══════════════════════════════════════════
# التذكيرات
# ══════════════════════════════════════════

def add_reminder(user_id: int, azkar_type: int, hour: int,
                 minute: int, tz_offset: int = 0) -> int:
    """Inserts a reminder and returns its new id."""
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        """INSERT INTO azkar_reminders (user_id, azkar_type, hour, minute, tz_offset)
           VALUES (?,?,?,?,?)""",
        (user_id, azkar_type, hour, minute, tz_offset),
    )
    conn.commit()
    return cur.lastrowid

def get_user_reminders(user_id: int) -> list:
    """Returns all reminders for a user ordered by hour/minute."""
    cur = get_db_conn().cursor()
    cur.execute(
        """SELECT id, user_id, azkar_type, hour, minute, tz_offset, created_at
           FROM azkar_reminders
           WHERE user_id=?
           ORDER BY hour, minute""",
        (user_id,),
    )
    return [dict(r) for r in cur.fetchall()]


def delete_reminder(reminder_id: int, user_id: int) -> bool:
    """Deletes a reminder — only if it belongs to user_id."""
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        "DELETE FROM azkar_reminders WHERE id=? AND user_id=?",
        (reminder_id, user_id),
    )
    conn.commit()
    return cur.rowcount > 0


def get_due_reminders(utc_hour: int, utc_minute: int) -> list:
    """
    Returns reminders whose local time matches utc_hour:utc_minute.
    Local time = UTC + tz_offset (minutes).
    """
    cur = get_db_conn().cursor()
    cur.execute("SELECT * FROM azkar_reminders")
    due = []
    for r in cur.fetchall():
        r = dict(r)
        local_total = r["hour"] * 60 + r["minute"]
        utc_total   = (local_total - r["tz_offset"]) % (24 * 60)
        if utc_total == utc_hour * 60 + utc_minute:
            due.append(r)
    return due


def count_user_reminders(user_id: int) -> int:
    """Returns the number of active reminders for a user."""
    cur = get_db_conn().cursor()
    cur.execute(
        "SELECT COUNT(*) FROM azkar_reminders WHERE user_id=?",
        (user_id,),
    )
    return cur.fetchone()[0]
