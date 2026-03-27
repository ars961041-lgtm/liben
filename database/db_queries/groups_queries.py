from ..connection import get_db_conn

def upsert_group_member(group_id, user_id, full_name, group_name):

    conn = get_db_conn()
    cursor = conn.cursor()

    # حماية من القيم الفارغة
    group_name = group_name or "Unknown"
    full_name = full_name or "Unknown"

    # إضافة المجموعة إذا لم تكن موجودة
    cursor.execute(
        "INSERT OR IGNORE INTO groups (id, name) VALUES (?, ?)",
        (group_id, group_name)
    )

    # تحديث اسم المستخدم
    cursor.execute(
        """
        INSERT INTO users_name (user_id, name)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET name = excluded.name
        """,
        (user_id, full_name)
    )

    # إضافة العضو أو زيادة عدد الرسائل
    cursor.execute(
        """
        INSERT INTO group_members (user_id, group_id, message_count)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, group_id)
        DO UPDATE SET message_count = message_count + 1
        """,
        (user_id, group_id)
    )

    conn.commit()

def get_top_group_members(group_id, limit=10):

    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT gm.user_id, gm.message_count, COALESCE(un.name, 'Unknown')
        FROM group_members gm
        LEFT JOIN users_name un ON gm.user_id = un.user_id
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

def get_group_stats(user_id, group_id):
    """
    ترجع إحصائيات المستخدم في المجموعة:
    - عدد الرسائل
    - ترتيب المستخدم حسب عدد الرسائل
    - النسبة المئوية للمساهمات
    """
    conn = get_db_conn()
    cursor = conn.cursor()

    # عدد رسائل المستخدم في المجموعة
    cursor.execute("""
        SELECT message_count
        FROM group_members
        WHERE group_id = ? AND user_id = ?
    """, (group_id, user_id))
    row = cursor.fetchone()
    msg_count = row[0] if row else 0

    # جميع الأعضاء مرتبين حسب عدد الرسائل
    cursor.execute("""
        SELECT user_id, message_count
        FROM group_members
        WHERE group_id = ?
        ORDER BY message_count DESC
    """, (group_id,))
    members = cursor.fetchall()

    # إجمالي الرسائل في المجموعة
    cursor.execute("""
        SELECT SUM(message_count)
        FROM group_members
        WHERE group_id = ?
    """, (group_id,))
    total_msgs = cursor.fetchone()[0] or 0

    # حساب ترتيب المستخدم
    rank = None
    for i, (uid, _) in enumerate(members, 1):
        if uid == user_id:
            rank = i
            break

    # حساب النسبة المئوية بشكل دقيق
    percentage = (msg_count / total_msgs * 100) if total_msgs > 0 else 0

    return {
        "msg_count": msg_count,
        "rank": rank,
        "percentage": round(percentage, 2)
    }