from ..connection import get_db_conn
import time

def send_error(fun_name, error):
    return f"Error in {fun_name}: {str(error)}"

def get_user_info(user_id):
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT id, user_id FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()
    except Exception as e:
        print(send_error("get_user_info", e))
        return None

def get_user_gender(user_id):
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT gender FROM users WHERE user_id = ?', (user_id,))
        gender = cursor.fetchone()
        return None if not gender or gender[0] == "غير محدد" else gender[0]
    except Exception as e:
        print(send_error("get_user_gender", e))
        return None
    
def get_user_msgs (user_id, group_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT message_count FROM group_members WHERE user_id = ? AND group_id = ?', (user_id, group_id))
    result = cursor.fetchone()
    return result[0] if result else 0
