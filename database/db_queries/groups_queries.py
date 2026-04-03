# database/db_queries/group_members_stats.py

from ..connection import get_db_conn
import sqlite3

# ----------------------------------
# إضافة عضو للقروب أو تحديث بياناته (اسم المستخدم وعدد الرسائل)
# ----------------------------------
def upsert_group_member(group_id, user_id, full_name, group_name):
    conn = get_db_conn()
    cursor = conn.cursor()

    group_name = group_name or "Unknown"
    full_name = full_name or "Unknown"

    # إضافة القروب إذا لم يكن موجودًا
    cursor.execute(
        "INSERT OR IGNORE INTO groups (id, name) VALUES (?, ?)",
        (group_id, group_name)
    )

    # إضافة أو تحديث اسم المستخدم
    cursor.execute(
        """
        INSERT INTO users_name (user_id, name)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET name = excluded.name
        """,
        (user_id, full_name)
    )

    # إضافة العضو للقروب أو زيادة عدد الرسائل
    cursor.execute(
        """
        INSERT INTO group_members (user_id, group_id, messages_count)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, group_id)
        DO UPDATE SET messages_count = messages_count + 1
        """,
        (user_id, group_id)
    )

    conn.commit()


# ----------------------------------
# الحصول على إجمالي عدد الرسائل في القروب
# ----------------------------------
def get_group_total_messages(group_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT SUM(messages_count) FROM group_members WHERE group_id = ?', 
        (group_id,)
    )
    total = cursor.fetchone()[0] or 0
    return total


# ----------------------------------
# إحصائيات العضو في القروب: عدد الرسائل والمرتبة
# ----------------------------------
def get_group_stats(user_id, group_id):
    conn = get_db_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # عدد الرسائل
    cursor.execute(
        '''
        SELECT messages_count
        FROM group_members
        WHERE user_id = ? AND group_id = ?
        ''',
        (user_id, group_id)
    )
    row = cursor.fetchone()
    messages_count = row["messages_count"] if row else 0

    # حساب المرتبة
    cursor.execute(
        '''
        SELECT COUNT(*) + 1 AS rank
        FROM group_members
        WHERE group_id = ? AND messages_count > (
            SELECT messages_count
            FROM group_members
            WHERE user_id = ? AND group_id = ?
        )
        ''',
        (group_id, user_id, group_id)
    )
    row = cursor.fetchone()
    rank = row["rank"] if row else 1

    return {
        "messages_count": messages_count,
        "rank": rank
    }