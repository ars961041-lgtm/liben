# database/db_queries/cities_queries.py

import sqlite3
from ..connection import get_db_conn
from utils.helpers import send_error

# -------------------------
# التحقق من وجود مدينة بالاسم
# -------------------------
def city_exists(city_name: str) -> bool:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM cities WHERE name = ?', (city_name.strip(),))
    exists = bool(cursor.fetchone())
    return exists

# -------------------------
# إنشاء مدينة جديدة
# -------------------------
def create_city(name: str, owner_id: int, country_id: int = None) -> int:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO cities (name, owner_id, country_id, last_collect_time) "
        "VALUES (?, ?, ?, strftime('%s','now'))",
        (name.strip(), owner_id, country_id)
    )
    city_id = cursor.lastrowid

    # Seed related tables so they always exist for every city
    cursor.execute(
        "INSERT OR IGNORE INTO city_budget (city_id) VALUES (?)", (city_id,)
    )
    cursor.execute(
        "INSERT OR IGNORE INTO city_spending (city_id) VALUES (?)", (city_id,)
    )

    conn.commit()
    return city_id

# -------------------------
# الحصول على المدينة الخاصة بالمستخدم
# -------------------------
def get_user_city(user_id: int):
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, name, country_id FROM cities WHERE owner_id = ?',
            (user_id,)
        )
        city = cursor.fetchone()
        return city
    except Exception as e:
        print(send_error("get_user_city", e))
        return None

# -------------------------
# الحصول على تفاصيل المدينة للمستخدم
# -------------------------
def get_user_city_details(user_id: int):
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, name, level, population, area, country_id, last_collect_time FROM cities WHERE owner_id = ?',
            (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "city_id": row['id'],
            "اسم المدينة": f"<b>مدينتك:</b> {row['name']}",
            "المستوى": f"<b>المستوى:</b> {row['level']}",
            "عدد السكان": f"<b>عدد السكان:</b> {row['population']}",
            "المساحة": f"<b>المساحة:</b> {row['area']}",
            "الدولة_id": row['country_id'],
            "last_collect_time": row['last_collect_time'],
        }
    except Exception as e:
        print(send_error("get_user_city_details", e))
        return None

# -------------------------
# تحديث بيانات المدينة (مثلاً مستوى أو عدد السكان أو المساحة)
# -------------------------
def update_city(city_id: int, level: int = None, population: int = None, area: float = None):
    conn = get_db_conn()
    cursor = conn.cursor()
    updates = []
    params = []

    if level is not None:
        updates.append("level=?")
        params.append(level)
    if population is not None:
        updates.append("population=?")
        params.append(population)
    if area is not None:
        updates.append("area=?")
        params.append(area)

    if not updates:
        return False  # لا تحديثات

    params.append(city_id)
    sql = f"UPDATE cities SET {', '.join(updates)} WHERE id=?"
    cursor.execute(sql, params)
    conn.commit()
    return True

# -------------------------
# حذف مدينة (مع حذف المباني لاحقًا من الخدمة)
# -------------------------
def delete_city(city_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cities WHERE id=?', (city_id,))
    conn.commit()
    return True

# -------------------------
# الحصول على كل المدن في دولة معينة
# -------------------------
def get_cities_by_country(country_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, name, level, population, area FROM cities WHERE country_id=?',
        (country_id,)
    )
    rows = cursor.fetchall()
    return rows

# -------------------------
# أفضل المدن حسب ميزانية المدينة
# -------------------------
def get_top_cities(limit=10):
    conn = get_db_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT 
            c.id,
            c.name,
            COALESCE(cb.current_budget, 0) AS value
        FROM cities c
        LEFT JOIN city_budget cb ON c.id = cb.city_id
        ORDER BY value DESC
        LIMIT ?
        ''',
        (limit,)
    )
    result = [dict(row) for row in cursor.fetchall()]
    return result

# -------------------------
# الحصول على المستخدمين المنتمين لمدينة معينة
# -------------------------
def get_city_users(city_id: int):
    """
    ترجع المستخدم المالك للمدينة المحددة.
    cities.owner_id → users.user_id (Telegram ID)
    """
    conn = get_db_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.user_id, COALESCE(NULLIF(u.name, ''), 'Unknown') AS name
        FROM cities c
        JOIN users u ON u.user_id = c.owner_id
        WHERE c.id = ?
    """, (city_id,))

    rows = cursor.fetchall()
    return [dict(row) for row in rows]