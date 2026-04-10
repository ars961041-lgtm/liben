
import time

from database.db_queries.assets_queries import calculate_city_effects
from ..connection import get_db_conn
from utils.helpers import send_error

# -------------------------
# الحصول على قيمة أي إحصائية اقتصادية عامة
# -------------------------
def get_economy_stat(name: str, default=0.0):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM economy_stats WHERE name = ?', (name,))
    row = cursor.fetchone()
    if row:
        try:
            return float(row[0])
        except ValueError:
            return row[0]
    return default

# -------------------------
# تعيين أو تحديث قيمة إحصائية اقتصادية عامة
# -------------------------
def set_economy_stat(name: str, value):
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO economy_stats (name, value, last_updated)
            VALUES (?, ?, ?)
            ON CONFLICT(name)
            DO UPDATE SET value=excluded.value, last_updated=excluded.last_updated
        ''', (name, str(value), int(time.time())))
        conn.commit()
    except Exception as e:
        print(send_error("set_economy_stat", e))

# -------------------------
# حساب إجمالي الدخل والصيانة لكل دولة بناءً على المدن والمباني
# -------------------------
def calculate_country_economy(country_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()

    # جمع جميع المدن التابعة للدولة
    cursor.execute('SELECT id FROM cities WHERE country_id = ?', (country_id,))
    cities = cursor.fetchall()

    total_income = 0
    total_maintenance = 0

    for city in cities:
        city_stats = calculate_city_effects(city['id'])
        total_income += city_stats.get("income", 0)
        total_maintenance += city_stats.get("maintenance", 0)

    return {
        "income": total_income,
        "maintenance": total_maintenance,
        "net_budget": total_income - total_maintenance
    }

# -------------------------
# تحديث الميزانية العامة للدولة وتوزيعها على المدن
# -------------------------
def update_country_budget(country_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    economy = calculate_country_economy(country_id)
    net_budget = economy["net_budget"]

    cursor.execute('SELECT id FROM cities WHERE country_id = ?', (country_id,))
    cities = cursor.fetchall()
    if not cities:
        return False

    per_city_budget = net_budget / len(cities) if len(cities) > 0 else 0
    income_per_city = economy["income"] / len(cities) if len(cities) > 0 else 0
    expense_per_city = economy["maintenance"] / len(cities) if len(cities) > 0 else 0

    for city in cities:
        cursor.execute('''
            UPDATE city_budget
            SET current_budget = ?,
                income_per_hour = ?,
                expense_per_hour = ?,
                last_update_time = strftime('%s','now')
            WHERE city_id = ?
        ''', (per_city_budget, income_per_city, expense_per_city, city['id']))

    conn.commit()
    return True