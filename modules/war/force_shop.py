"""
متجر القوات — شراء جنود ومعدات مباشرة من قائمة الحرب
"""
from database.connection import get_db_conn
from database.db_queries.war_queries import (
    get_all_troop_types, get_all_equipment_types,
    add_city_troops, add_city_equipment,
    get_city_troop, get_city_equipment_item,
)
from database.db_queries.countries_queries import get_all_cities_of_country_by_country_id
from database.db_queries.bank_queries import get_user_balance, deduct_user_balance
from utils.helpers import get_lines


# ══════════════════════════════════════════
# 🪖 جلب الجنود المتاحة
# ══════════════════════════════════════════

def get_available_troops() -> list:
    """يرجع كل أنواع الجنود مع أسعارها"""
    troops = get_all_troop_types()
    return [dict(t) for t in troops]


def get_available_equipment() -> list:
    """يرجع كل أنواع المعدات مع أسعارها"""
    eq = get_all_equipment_types()
    return [dict(e) for e in eq]


# ══════════════════════════════════════════
# 🛒 شراء جنود
# ══════════════════════════════════════════

def buy_troops(user_id: int, country_id: int, troop_type_id: int,
               quantity: int) -> tuple:
    """
    يشتري جنوداً ويضيفهم لعاصمة الدولة.
    يرجع (True, msg) أو (False, msg)
    """
    if quantity <= 0:
        return False, "❌ الكمية يجب أن تكون أكبر من صفر."

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM troop_types WHERE id = ?", (troop_type_id,))
    troop = cursor.fetchone()
    if not troop:
        return False, "❌ نوع الجندي غير موجود."
    troop = dict(troop)

    total_cost = troop["base_cost"] * quantity
    balance = get_user_balance(user_id)
    if balance < total_cost:
        return False, f"❌ رصيدك غير كافٍ! تحتاج {total_cost:.0f} Liben (رصيدك: {balance:.0f})"

    # إضافة للعاصمة (أول مدينة)
    city_id = _get_capital_city(country_id)
    if not city_id:
        return False, "❌ لا توجد مدينة في دولتك!"

    deduct_user_balance(user_id, total_cost)
    add_city_troops(city_id, troop_type_id, quantity)

    return True, (
        f"✅ تم شراء {quantity} × {troop['emoji']} {troop['name_ar']}\n"
        f"💰 التكلفة: {total_cost:.0f} Liben"
    )


# ══════════════════════════════════════════
# 🛒 شراء معدات
# ══════════════════════════════════════════

def buy_equipment(user_id: int, country_id: int, eq_type_id: int,
                  quantity: int) -> tuple:
    """
    يشتري معدات ويضيفها لعاصمة الدولة.
    يرجع (True, msg) أو (False, msg)
    """
    if quantity <= 0:
        return False, "❌ الكمية يجب أن تكون أكبر من صفر."

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM equipment_types WHERE id = ?", (eq_type_id,))
    eq = cursor.fetchone()
    if not eq:
        return False, "❌ نوع المعدة غير موجود."
    eq = dict(eq)

    total_cost = eq["base_cost"] * quantity
    balance = get_user_balance(user_id)
    if balance < total_cost:
        return False, f"❌ رصيدك غير كافٍ! تحتاج {total_cost:.0f} Liben (رصيدك: {balance:.0f})"

    city_id = _get_capital_city(country_id)
    if not city_id:
        return False, "❌ لا توجد مدينة في دولتك!"

    deduct_user_balance(user_id, total_cost)
    add_city_equipment(city_id, eq_type_id, quantity)

    return True, (
        f"✅ تم شراء {quantity} × {eq['emoji']} {eq['name_ar']}\n"
        f"💰 التكلفة: {total_cost:.0f} Liben"
    )


# ══════════════════════════════════════════
# 📊 عرض قوات المدينة
# ══════════════════════════════════════════

def get_city_forces_display(country_id: int) -> str:
    """يبني نص عرض كامل لقوات الدولة"""
    from database.db_queries.war_queries import get_city_troops, get_city_equipment
    from modules.war.power_calculator import get_country_power

    cities = get_all_cities_of_country_by_country_id(country_id)
    if not cities:
        return "❌ لا توجد مدن في دولتك."

    total_power = get_country_power(country_id)
    text = f"🪖 <b>قوات دولتك</b>\n💪 القوة الكاملة: {total_power:.0f}\n{get_lines()}\n\n"

    for city in cities:
        cid  = city["id"] if isinstance(city, dict) else city[0]
        cname = city["name"] if isinstance(city, dict) else "مدينة"
        troops = get_city_troops(cid)
        equip  = get_city_equipment(cid)

        if not troops and not equip:
            continue

        text += f"🏙 <b>{cname}</b>\n"
        if troops:
            text += "  🪖 الجنود:\n"
            for t in troops:
                t = dict(t)
                text += f"    {t.get('emoji','⚔️')} {t['name_ar']}: {t['quantity']}\n"
        if equip:
            text += "  🛡 المعدات:\n"
            for e in equip:
                e = dict(e)
                text += f"    {e.get('emoji','🔫')} {e['name_ar']}: {e['quantity']}\n"
        text += "\n"

    return text


# ══════════════════════════════════════════
# 🔧 مساعدات
# ══════════════════════════════════════════

def _get_capital_city(country_id: int):
    cities = get_all_cities_of_country_by_country_id(country_id)
    if not cities:
        return None
    city = cities[0]
    return city["id"] if isinstance(city, dict) else city[0]
