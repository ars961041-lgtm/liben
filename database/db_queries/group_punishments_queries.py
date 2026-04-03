# database/db_queries/group_members_queries.py

from database.connection import get_db_conn

# الأعمدة المسموحة (للحماية)
ALLOWED_FIELDS = {"is_muted", "is_banned", "is_restricted"}

# ----------------------------------
# تعديل حالة مستخدم (مثال: كتم، حظر، تقييد)
# ----------------------------------
def set_user_status(user_id, group_id, field, value):
    if field not in ALLOWED_FIELDS:
        raise ValueError("حقل غير صالح")

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(f"""
        UPDATE group_members
        SET {field} = ?
        WHERE user_id = ? AND group_id = ?
    """, (value, user_id, group_id))
    conn.commit()

# ----------------------------------
# التحقق من حالة مستخدم معينة
# ----------------------------------
def is_user_status(user_id, group_id, field):
    if field not in ALLOWED_FIELDS:
        raise ValueError("حقل غير صالح")

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT {field}
        FROM group_members
        WHERE user_id = ? AND group_id = ?
    """, (user_id, group_id))
    result = cursor.fetchone()
    return result and result[0] == 1

# ----------------------------------
# الحصول على كل المستخدمين بحالة معينة
# ----------------------------------
def get_users_by_status(group_id, field):
    if field not in ALLOWED_FIELDS:
        raise ValueError("حقل غير صالح")

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT user_id
        FROM group_members
        WHERE group_id = ? AND {field} = 1
    """, (group_id,))
    results = cursor.fetchall()
    return results

# ----------------------------------
# تسجيل عقوبة أو رفعها
# ----------------------------------
def log_punishment(group_id, user_id, action_type, executor_id, reverse=False):
    """
    سجل الحدث في جدول العقوبات.
    إذا reverse=True، سيتم تحويل action_type لرفع العقوبة (action_type + 3)
    """
    if reverse:
        action_type += 3

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO group_punishment_log (group_id, user_id, action_type, executor_id)
        VALUES (?, ?, ?, ?)
    """, (group_id, user_id, action_type, executor_id))
    conn.commit()

# ----------------------------------
# استعلام العقوبات لمستخدم معين
# ----------------------------------
def get_user_punishments(group_id, user_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, action_type, executor_id, timestamp
        FROM group_punishment_log
        WHERE group_id = ? AND user_id = ?
        ORDER BY timestamp DESC
    """, (group_id, user_id))
    results = cursor.fetchall()
    return results

# ----------------------------------
# استعلام العقوبات لمجموعة معينة
# ----------------------------------
def get_group_punishments(group_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, action_type, executor_id, timestamp
        FROM group_punishment_log
        WHERE group_id = ?
        ORDER BY timestamp DESC
    """, (group_id,))
    results = cursor.fetchall()
    return results

# ----------------------------------
# الحصول على آخر حدث لعقوبة معينة لمستخدم
# ----------------------------------
def get_last_punishment(group_id, user_id, action_type):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, action_type, executor_id, timestamp
        FROM group_punishment_log
        WHERE group_id = ? AND user_id = ? AND action_type = ?
        ORDER BY timestamp DESC
        LIMIT 1
    """, (group_id, user_id, action_type))
    result = cursor.fetchone()
    return result

# ----------------------------------
# حذف كل العقوبات الخاصة بقروب
# ----------------------------------
def delete_group_punishments(group_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM group_punishment_log
        WHERE group_id = ?
    """, (group_id,))
    conn.commit()
