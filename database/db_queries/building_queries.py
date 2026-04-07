# database/db_queries/buildings_queries.py

import sqlite3
from database.connection import get_db_conn
from modules.country.services.building_config import get_building_info
from database.db_queries.bank_queries import deduct_user_balance

# -----------------------------
# شراء مبنى جديد للمدينة مع خصم الرصيد
# -----------------------------
def buy_building(user_id: int, city_id: int, building_type: str, quantity: int):
    config = get_building_info(building_type)
    if not config:
        return False, "❌ مبنى غير معروف"

    total_cost = config["base_cost"] * quantity
    if not deduct_user_balance(user_id, total_cost):
        return False, "❌ رصيدك لا يكفي"

    conn = get_db_conn()
    cursor = conn.cursor()

    # تحقق من وجود المبنى مسبقًا
    cursor.execute(
        'SELECT id, quantity, level FROM buildings WHERE city_id=? AND building_type=?',
        (city_id, building_type)
    )
    row = cursor.fetchone()

    if row:
        new_qty = row['quantity'] + quantity
        cursor.execute(
            'UPDATE buildings SET quantity=? WHERE id=?',
            (new_qty, row['id'])
        )
    else:
        cursor.execute(
            'INSERT INTO buildings (city_id, building_type, quantity, level) VALUES (?, ?, ?, 1)',
            (city_id, building_type, quantity)
        )

    # تسجيل الإنفاق بالسعر الأصلي (قبل أي خصومات أو أحداث)
    original_cost = config["base_cost"] * quantity
    record_city_spending(city_id, original_cost, cursor)

    conn.commit()
    return True, f"✅ تم شراء {quantity} {config['emoji']} {config['name_ar']}"


def record_city_spending(city_id: int, amount: float, cursor=None):
    """يسجل الإنفاق بالسعر الأصلي في city_spending."""
    _own_cursor = cursor is None
    if _own_cursor:
        conn = get_db_conn()
        cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO city_spending (city_id, total_spent)
            VALUES (?, ?)
            ON CONFLICT(city_id) DO UPDATE SET total_spent = total_spent + excluded.total_spent
        """, (city_id, amount))
        if _own_cursor:
            cursor.connection.commit()
    except Exception:
        pass

# -----------------------------
# ترقية مبنى معين بالمدينة
# -----------------------------
def upgrade_building(user_id: int, city_id: int, building_type: str, quantity: int = 1):
    config = get_building_info(building_type)
    if not config:
        return False, "❌ مبنى غير معروف"

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, quantity, level FROM buildings WHERE city_id=? AND building_type=?',
        (city_id, building_type)
    )
    row = cursor.fetchone()

    if not row:
            return False, "❌ لا يوجد هذا المبنى في المدينة"

    if row['quantity'] < quantity:
            return False, f"❌ لديك {row['quantity']} فقط من هذا المبنى"

    current_level = row['level']
    if current_level >= 10:
            return False, "❌ وصلت لأقصى مستوى"

    # حساب تكلفة الترقية لكل مبنى
    total_cost = 0
    for i in range(quantity):
        total_cost += config["base_cost"] * (config["cost_scale"] * (current_level - 1))

    if not deduct_user_balance(user_id, total_cost):
            return False, "❌ رصيدك لا يكفي"

    # ترقية المباني
    new_level = current_level + 1
    cursor.execute(
        'UPDATE buildings SET level=? WHERE id=?',
        (new_level, row['id'])
    )
    conn.commit()
    return True, f"⬆️ تم تطوير {config['name_ar']} إلى مستوى {new_level}"

# -----------------------------
# حساب إحصائيات المدينة من المباني
# -----------------------------
def calculate_city_stats(city_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT building_type, quantity, level FROM buildings WHERE city_id=?',
        (city_id,)
    )
    buildings = cursor.fetchall()

    stats = {
        "economy_score": 0,
        "health_level": 0,
        "education_level": 0,
        "military_power": 0,
        "infrastructure_level": 0
    }

    for b in buildings:
        config = get_building_info(b['building_type'])
        if not config:
            continue

        for stat, value in config.get("stat_impact", {}).items():
            # تأثير diminishing return
            effect = (b['quantity'] * b['level']) ** 0.8
            stats[stat] += effect * value

    return stats

# -----------------------------
# حساب الدخل والصيانة للمدينة
# -----------------------------
def calculate_city_economy(city_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT building_type, quantity, level FROM buildings WHERE city_id=?',
        (city_id,)
    )
    buildings = cursor.fetchall()
    total_income = 0
    total_maintenance = 0
    for b in buildings:
        config = get_building_info(b['building_type'])
        if not config:
            continue
        total_income += config.get("income", 0) * b['quantity']
        total_maintenance += config.get("maintenance_cost", 0) * b['quantity'] * b['level']

    # ─── تطبيق مكافأة النفوذ على الدخل ───
    try:
        cursor.execute("SELECT country_id FROM cities WHERE id = ?", (city_id,))
        row = cursor.fetchone()
        if row:
            from modules.progression.influence import get_income_bonus
            bonus = get_income_bonus(row[0])
            if bonus > 0:
                total_income = total_income * (1 + bonus)
    except Exception:
        pass

    # ─── تطبيق أحداث الاقتصاد العالمية ───
    try:
        from modules.progression.global_events import get_event_effect
        income_event = get_event_effect("income_bonus")
        if income_event > 0:
            total_income = total_income * (1 + income_event)
        income_penalty = get_event_effect("income_penalty")
        if income_penalty > 0:
            total_income = total_income * (1 - income_penalty)
        maintenance_event = get_event_effect("maintenance_increase")
        if maintenance_event > 0:
            total_maintenance = total_maintenance * (1 + maintenance_event)
    except Exception:
        pass

    return {
        "income": total_income,
        "maintenance": total_maintenance
    }

# -----------------------------
# حذف جميع المباني في المدينة (لأغراض الاختبار)
# -----------------------------
def delete_all_buildings(city_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM buildings WHERE city_id=?', (city_id,))
    conn.commit()
    return True