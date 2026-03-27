from utils.helpers import send_error

from ..connection import get_db_conn

def get_all_countries():
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, owner_id FROM countries ORDER BY id ASC")
        return cursor.fetchall()

def assign_country_to_user(country_id, user_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE countries SET owner_id = ? WHERE id = ?", (user_id, country_id))
    conn.commit()

def get_country_stats(country_id):
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM country_stats WHERE country_id = ?', (country_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)
    
def update_country_stats(country_id, economy, health, education, military, infrastructure):
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE country_stats 
            SET economy_score = ?, health_level = ?, education_level = ?, military_power = ?, infrastructure_level = ?
            WHERE country_id = ?
        ''', (economy, health, education, military, infrastructure, country_id))
        conn.commit()
        
def get_country_budget(country_id):
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT SUM(current_budget) FROM city_budget WHERE country_id = ?', (country_id,))
        row = cursor.fetchone()
        return float(row[0]) if row else 0.0

def get_user_country(user_id):
    try:
        conn = get_db_conn()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, name FROM countries WHERE owner_id = ?",
            (user_id,)
        )

        return cursor.fetchone()

    except Exception as e:
        print(send_error("get_user_country", e))
        return None
    
def get_user_country_details(user_id):
    try:
            conn = get_db_conn()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    name,
                    level,
                    population,
                    area,
                    development,
                    stability,
                    happiness,
                    max_cities
                FROM countries
                WHERE owner_id = ?
            """, (user_id,))

            row = cursor.fetchone()

            if not row:
                return None

            return {
                "اسم الدولة": f"<b>الدولة:</b> {row['name']}",
                "المستوى": f"<b>المستوى:</b> {row['level']}",
                "عدد السكان": f"<b>السكان:</b> {row['population']}",
                "المساحة": f"<b>المساحة:</b> {row['area']}",
                "التطوير": f"<b>التطوير:</b> {row['development']}",
                "الاستقرار": f"<b>الاستقرار:</b> {row['stability']}",
                "السعادة": f"<b>السعادة:</b> {row['happiness']}",
                "عدد المدن": f"<b>المدن المسموحة:</b> {row['max_cities']}"
            }

    except Exception as e:
        print(send_error("get_user_country_details", e))
        return None
    
def get_user_country_name(user_id):
    try:
            conn = get_db_conn()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT name FROM countries WHERE owner_id = ?",
                (user_id,)
            )

            row = cursor.fetchone()

            return row["name"] if row else None

    except Exception as e:
        print(send_error("get_user_country_name", e))
        return None
    
def create_country(name, owner_id):

        conn = get_db_conn()
        cursor = conn.cursor()

        cursor.execute(
            '''
            INSERT INTO countries (name, owner_id)
            VALUES (?, ?)
            ''',
            (name, owner_id)
        )

        conn.commit()

        return cursor.lastrowid
    
def country_exists(name):

        conn = get_db_conn()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM countries WHERE name = ?",
            (name,)
        )

        return cursor.fetchone() is not None
    
