from ..connection import get_db_conn
import time

# ----------------------------------
# طباعة خطأ مع اسم الدالة
# ----------------------------------
def send_error(fun_name, error):
    return f"Error in {fun_name}: {str(error)}"

# ----------------------------------
# الحصول على معلومات المستخدم
# ----------------------------------
def get_user_info(user_id):
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT id, user_id FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        return row
    except Exception as e:
        print(send_error("get_user_info", e))
        return None


def get_user_id_by_username(username: str):
    """
    يبحث عن user_id بناءً على @username (بدون أو مع @).
    يرجع (user_id, name) أو (None, None) إذا لم يُوجد.
    """
    try:
        uname = username.lstrip("@").lower()
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT user_id, name FROM users WHERE LOWER(username) = ?',
            (uname,)
        )
        row = cursor.fetchone()
        if row:
            return row[0], row[1]
        return None, None
    except Exception as e:
        print(send_error("get_user_id_by_username", e))
        return None, None

# ----------------------------------
# الحصول على عدد الرسائل لمستخدم في مجموعة معينة
# ----------------------------------
def get_user_msgs(user_id, group_id):
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT messages_count FROM group_members WHERE user_id = ? AND group_id = ?',
            (user_id, group_id)
        )
        row = cursor.fetchone()
        return row[0] if row else 0
    except Exception as e:
        print(send_error("get_user_msgs", e))
        return 0