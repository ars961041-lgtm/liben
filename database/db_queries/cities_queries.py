from utils.helpers import send_error

from ..connection import get_db_conn

def city_exists(city_name):
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM cities WHERE name = ?', (city_name.strip(),))
        return bool(cursor.fetchone())

def create_city(name, owner_id, country_id=None):
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO cities (name, owner_id, country_id) VALUES (?, ?, ?)',
                       (name.strip(), owner_id, country_id))
        conn.commit()
        return cursor.lastrowid

def get_user_city(user_id):

    try:
        conn = get_db_conn()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, name FROM cities WHERE owner_id = ?",
            (user_id,)
        )

        return cursor.fetchone()

    except Exception as e:
        print(send_error("get_user_city", e))
        return None
    
def get_user_city_details(user_id):

    try:
            conn = get_db_conn()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT name, level, population, area
                FROM cities
                WHERE owner_id = ?
            """, (user_id,))

            row = cursor.fetchone()

            if not row:
                return None

            return {
                "اسم المدينة": f"<b>مدينتك:</b> {row['name']}",
                "المستوى": f"<b>المستوى:</b> {row['level']}",
                "عدد السكان": f"<b>عدد السكان:</b> {row['population']}",
                "المساحة": f"<b>المساحة:</b> {row['area']}"
            }

    except Exception as e:
        print(send_error("get_user_city_details", e))
        return None