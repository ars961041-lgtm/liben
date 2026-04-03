"""
اقتصاد الحرب — الخسائر الحقيقية، المصابون، الإصلاح، التعافي، التكاليف
"""
import time
import random

from database.connection import get_db_conn
from database.db_queries.countries_queries import get_all_cities_of_country_by_country_id
from database.db_queries.war_queries import get_city_troops, get_city_equipment
from modules.war.power_calculator import get_country_power, aggregate_country_forces, calc_raw_power

# ─── ثوابت ───
def _c(name, default):
    try:
        from core.admin import get_const_float, get_const_int
        if isinstance(default, float):
            return get_const_float(name, default)
        return get_const_int(name, int(default))
    except Exception:
        return default

ATTACK_COST       = property(lambda self: _c("attack_cost", 500))
SUPPORT_SEND_COST = property(lambda self: _c("support_send_cost", 100))
CARD_USE_COST     = property(lambda self: _c("card_use_cost", 50))
RECOVERY_MINUTES  = property(lambda self: _c("recovery_minutes", 30))
BASE_HEAL_TIME    = 3600
BASE_REPAIR_TIME  = 1800
INJURED_RATIO_MIN = 0.30
INJURED_RATIO_MAX = 0.50
DAMAGED_RATIO     = 0.40
LOOT_MIN_PCT      = property(lambda self: _c("loot_min_pct", 0.05))
LOOT_MAX_PCT      = property(lambda self: _c("loot_max_pct", 0.15))

# ─── دوال مساعدة للوصول للثوابت ───
def _get_attack_cost():
    try:
        from core.admin import get_const_int
        return get_const_int("attack_cost", 500)
    except Exception:
        return 500

def _get_recovery_minutes():
    try:
        from core.admin import get_const_int
        return get_const_int("recovery_minutes", 30)
    except Exception:
        return 30

def _get_loot_pct():
    try:
        from core.admin import get_const_float
        return get_const_float("loot_min_pct", 0.05), get_const_float("loot_max_pct", 0.15)
    except Exception:
        return 0.05, 0.15


# ══════════════════════════════════════════
# 💰 تكاليف الحرب
# ══════════════════════════════════════════

def charge_war_cost(user_id, action, battle_id=None, amount=None):
    from database.db_queries.bank_queries import get_user_balance, deduct_user_balance
    try:
        from core.admin import get_const_int
        costs = {
            "attack":       get_const_int("attack_cost", 500),
            "support_send": get_const_int("support_send_cost", 100),
            "card_use":     get_const_int("card_use_cost", 50),
        }
    except Exception:
        costs = {"attack": 500, "support_send": 100, "card_use": 50}

    cost = amount if amount is not None else costs.get(action, 0)
    if cost <= 0:
        return True, ""

    balance = get_user_balance(user_id)
    if balance < cost:
        return False, f"❌ رصيدك غير كافٍ! تحتاج {cost:.0f} Liben (رصيدك: {balance:.0f})"

    deduct_user_balance(user_id, cost)
    _log_war_cost(user_id, battle_id, action, cost)
    return True, f"💸 تم خصم {cost:.0f} Liben"


def _log_war_cost(user_id, battle_id, action, amount):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO war_costs_log (user_id, battle_id, action, amount)
        VALUES (?, ?, ?, ?)
    """, (user_id, battle_id, action, amount))
    conn.commit()


# ══════════════════════════════════════════
# 💀 الخسائر الحقيقية بالنسبة المئوية
# ══════════════════════════════════════════

def apply_proportional_losses(country_id, initial_power, final_power):
    """
    يحسب نسبة الخسارة ويطبقها على الجنود والمعدات الفعلية.
    يرجع dict مع تفاصيل الخسائر والمصابين والتالف.
    """
    if initial_power <= 0:
        return _empty_loss_report()

    loss_pct = max(0.0, min(1.0, (initial_power - final_power) / initial_power))
    if loss_pct < 0.01:
        return _empty_loss_report()

    cities = get_all_cities_of_country_by_country_id(country_id)
    if not cities:
        return _empty_loss_report()

    total_killed = 0
    total_injured = 0
    total_eq_destroyed = 0
    total_eq_damaged = 0

    for city in cities:
        city_id = city["id"] if isinstance(city, dict) else city[0]
        k, inj = _apply_troop_losses_proportional(city_id, loss_pct)
        d, dmg = _apply_equipment_losses_proportional(city_id, loss_pct)
        total_killed   += k
        total_injured  += inj
        total_eq_destroyed += d
        total_eq_damaged   += dmg

    return {
        "loss_pct":       round(loss_pct * 100, 1),
        "killed":         total_killed,
        "injured":        total_injured,
        "eq_destroyed":   total_eq_destroyed,
        "eq_damaged":     total_eq_damaged,
    }


def _apply_troop_losses_proportional(city_id, loss_pct):
    """يطبق الخسائر على جنود مدينة واحدة، يرجع (killed, injured)"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT troop_type_id, quantity FROM city_troops WHERE city_id = ?
    """, (city_id,))
    rows = cursor.fetchall()

    total_killed = 0
    total_injured = 0

    for row in rows:
        tid, qty = row[0], row[1]
        if qty <= 0:
            continue

        total_loss = max(0, int(qty * loss_pct))
        if total_loss == 0:
            continue

        injured_ratio = random.uniform(INJURED_RATIO_MIN, INJURED_RATIO_MAX)
        injured = max(0, int(total_loss * injured_ratio))
        killed  = max(0, total_loss - injured)

        new_qty = max(0, qty - total_loss)
        cursor.execute("""
            UPDATE city_troops SET quantity = ? WHERE city_id = ? AND troop_type_id = ?
        """, (new_qty, city_id, tid))

        if injured > 0:
            heal_time = int(time.time()) + BASE_HEAL_TIME
            cursor.execute("""
                INSERT INTO injured_troops (city_id, troop_type_id, quantity, heal_time)
                VALUES (?, ?, ?, ?)
            """, (city_id, tid, injured, heal_time))

        total_killed  += killed
        total_injured += injured

    conn.commit()
    return total_killed, total_injured


def _apply_equipment_losses_proportional(city_id, loss_pct):
    """يطبق الخسائر على معدات مدينة واحدة، يرجع (destroyed, damaged)"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ce.equipment_type_id, ce.quantity, et.base_cost
        FROM city_equipment ce
        JOIN equipment_types et ON ce.equipment_type_id = et.id
        WHERE ce.city_id = ?
    """, (city_id,))
    rows = cursor.fetchall()

    total_destroyed = 0
    total_damaged   = 0

    for row in rows:
        eid, qty, base_cost = row[0], row[1], row[2]
        if qty <= 0:
            continue

        total_loss = max(0, int(qty * loss_pct))
        if total_loss == 0:
            continue

        damaged   = max(0, int(total_loss * DAMAGED_RATIO))
        destroyed = max(0, total_loss - damaged)

        new_qty = max(0, qty - total_loss)
        cursor.execute("""
            UPDATE city_equipment SET quantity = ? WHERE city_id = ? AND equipment_type_id = ?
        """, (new_qty, city_id, eid))

        if damaged > 0:
            repair_cost = round(damaged * (base_cost or 50) * 0.3, 2)
            repair_time = int(time.time()) + BASE_REPAIR_TIME
            cursor.execute("""
                INSERT INTO damaged_equipment
                (city_id, equipment_type_id, quantity, repair_cost, repair_time)
                VALUES (?, ?, ?, ?, ?)
            """, (city_id, eid, damaged, repair_cost, repair_time))

        total_destroyed += destroyed
        total_damaged   += damaged

    conn.commit()
    return total_destroyed, total_damaged


def _empty_loss_report():
    return {"loss_pct": 0, "killed": 0, "injured": 0, "eq_destroyed": 0, "eq_damaged": 0}


# ══════════════════════════════════════════
# 🏥 نظام الشفاء
# ══════════════════════════════════════════

def get_injured_troops(country_id):
    """يرجع كل الجنود المصابين في دولة"""
    cities = get_all_cities_of_country_by_country_id(country_id)
    if not cities:
        return []
    conn = get_db_conn()
    cursor = conn.cursor()
    result = []
    for city in cities:
        cid = city["id"] if isinstance(city, dict) else city[0]
        cursor.execute("""
            SELECT it.id, it.quantity, it.heal_time, tt.name_ar, tt.emoji
            FROM injured_troops it
            JOIN troop_types tt ON it.troop_type_id = tt.id
            WHERE it.city_id = ?
            ORDER BY it.heal_time ASC
        """, (cid,))
        result.extend([dict(r) for r in cursor.fetchall()])
    return result


def heal_ready_troops(country_id):
    """يُعيد الجنود المصابين الجاهزين للشفاء إلى الخدمة"""
    cities = get_all_cities_of_country_by_country_id(country_id)
    if not cities:
        return 0
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    total_healed = 0

    for city in cities:
        cid = city["id"] if isinstance(city, dict) else city[0]
        cursor.execute("""
            SELECT id, troop_type_id, quantity FROM injured_troops
            WHERE city_id = ? AND heal_time <= ?
        """, (cid, now))
        ready = cursor.fetchall()
        for row in ready:
            iid, tid, qty = row[0], row[1], row[2]
            # إعادة للخدمة
            cursor.execute("""
                INSERT INTO city_troops (city_id, troop_type_id, quantity)
                VALUES (?, ?, ?)
                ON CONFLICT(city_id, troop_type_id) DO UPDATE SET quantity = quantity + ?
            """, (cid, tid, qty, qty))
            cursor.execute("DELETE FROM injured_troops WHERE id = ?", (iid,))
            total_healed += qty

    conn.commit()
    return total_healed


def get_heal_time_reduction(country_id):
    """يحسب تخفيض وقت الشفاء من المستشفيات وترقيات التحالف"""
    reduction = 0
    try:
        # مستشفيات المدينة
        from database.db_queries.assets_queries import get_city_assets
        cities = get_all_cities_of_country_by_country_id(country_id)
        for city in cities:
            cid = city["id"] if isinstance(city, dict) else city[0]
            assets = get_city_assets(cid)
            for a in assets:
                if a.get("name", "").lower() in ("hospital", "clinic"):
                    reduction += a.get("quantity", 0) * a.get("level", 1) * 300
    except Exception:
        pass

    try:
        from database.db_queries.alliances_queries import get_alliance_by_country, get_alliance_effect
        alliance = get_alliance_by_country(country_id)
        if alliance:
            hp_bonus = get_alliance_effect(alliance["id"], "hp_bonus")
            reduction += int(hp_bonus * BASE_HEAL_TIME)
    except Exception:
        pass

    return min(reduction, BASE_HEAL_TIME - 300)  # لا يقل عن 5 دقائق


# ══════════════════════════════════════════
# 🔧 نظام الإصلاح
# ══════════════════════════════════════════

def get_damaged_equipment(country_id):
    """يرجع كل المعدات التالفة في دولة"""
    cities = get_all_cities_of_country_by_country_id(country_id)
    if not cities:
        return []
    conn = get_db_conn()
    cursor = conn.cursor()
    result = []
    for city in cities:
        cid = city["id"] if isinstance(city, dict) else city[0]
        cursor.execute("""
            SELECT de.id, de.quantity, de.repair_cost, de.repair_time,
                   et.name_ar, et.emoji
            FROM damaged_equipment de
            JOIN equipment_types et ON de.equipment_type_id = et.id
            WHERE de.city_id = ?
            ORDER BY de.repair_time ASC
        """, (cid,))
        result.extend([dict(r) for r in cursor.fetchall()])
    return result


def repair_equipment(user_id, country_id, damage_id=None):
    """
    يُصلح معدة تالفة (أو كل التالفة إذا damage_id=None).
    يرجع (True, msg, total_cost) أو (False, msg, 0)
    """
    from database.db_queries.bank_queries import get_user_balance, deduct_user_balance

    conn = get_db_conn()
    cursor = conn.cursor()

    if damage_id:
        cursor.execute("SELECT * FROM damaged_equipment WHERE id = ?", (damage_id,))
        rows = [cursor.fetchone()]
        rows = [r for r in rows if r]
    else:
        cities = get_all_cities_of_country_by_country_id(country_id)
        rows = []
        for city in cities:
            cid = city["id"] if isinstance(city, dict) else city[0]
            cursor.execute("SELECT * FROM damaged_equipment WHERE city_id = ?", (cid,))
            rows.extend(cursor.fetchall())

    if not rows:
        return False, "❌ لا توجد معدات تحتاج إصلاح.", 0

    total_cost = sum(r["repair_cost"] for r in rows)
    balance = get_user_balance(user_id)
    if balance < total_cost:
        return False, f"❌ تحتاج {total_cost:.0f} Liben للإصلاح (رصيدك: {balance:.0f})", 0

    deduct_user_balance(user_id, total_cost)

    for row in rows:
        row = dict(row)
        # إعادة المعدات
        cursor.execute("""
            INSERT INTO city_equipment (city_id, equipment_type_id, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(city_id, equipment_type_id) DO UPDATE SET quantity = quantity + ?
        """, (row["city_id"], row["equipment_type_id"], row["quantity"], row["quantity"]))
        cursor.execute("DELETE FROM damaged_equipment WHERE id = ?", (row["id"],))

    conn.commit()
    _log_war_cost(user_id, None, "repair", total_cost)
    return True, f"🔧 تم إصلاح {len(rows)} نوع معدات بتكلفة {total_cost:.0f} Liben", total_cost


# ══════════════════════════════════════════
# 🏃 نظام الانسحاب
# ══════════════════════════════════════════

def execute_retreat(user_id, battle_id):
    """
    ينسحب المستخدم من المعركة.
    يرجع (True, msg) أو (False, msg)
    """
    from database.db_queries.advanced_war_queries import (
        get_battle_by_id, finish_battle, update_reputation
    )
    from modules.war.live_battle_engine import (
        _get_battle_state, stop_live_battle, _log_event
    )

    battle = get_battle_by_id(battle_id)
    if not battle or battle["status"] != "in_battle":
        return False, "❌ لا توجد معركة نشطة للانسحاب منها."

    country = _get_country_by_user(user_id)
    if not country:
        return False, "❌ لا تملك دولة!"

    cid = country["id"]
    is_attacker = battle["attacker_country_id"] == cid
    if cid not in (battle["attacker_country_id"], battle["defender_country_id"]):
        return False, "❌ لست طرفاً في هذه المعركة!"

    state = _get_battle_state(battle_id)
    atk_p = state["atk_power"] if state else 0
    def_p = state["def_power"] if state else 0
    atk_init = state["atk_initial"] if state else atk_p
    def_init = state["def_initial"] if state else def_p

    # الانسحاب يقلل الخسائر 50%
    if is_attacker:
        final_atk = max(0, atk_p * 0.5)
        final_def = def_p
        winner_cid = battle["defender_country_id"]
        retreater_init = atk_init
        retreater_final = final_atk
        retreater_cid = battle["attacker_country_id"]
    else:
        final_atk = atk_p
        final_def = max(0, def_p * 0.5)
        winner_cid = battle["attacker_country_id"]
        retreater_init = def_init
        retreater_final = final_def
        retreater_cid = battle["defender_country_id"]

    # تطبيق الخسائر المخففة
    loss_report = apply_proportional_losses(retreater_cid, retreater_init, retreater_final)

    # مكافأة صغيرة للمدافع إذا انسحب المهاجم
    loot = 0
    if is_attacker:
        cap = _get_capital_city_id(battle["defender_country_id"])
        if cap:
            from database.db_queries.war_queries import update_city_resources
            update_city_resources(cap, 200)
            loot = 200

    finish_battle(battle_id, winner_cid, loot, max(0, final_atk), max(0, final_def))
    stop_live_battle(battle_id)
    _log_event(battle_id, "retreat", f"انسحاب من {'المهاجم' if is_attacker else 'المدافع'}", final_atk, final_def)

    # عقوبة السمعة للمنسحب
    update_reputation(user_id, ignored=1)

    # فترة تعافٍ
    set_country_recovery(retreater_cid, minutes=RECOVERY_MINUTES // 2)

    msg = (
        f"🏃 <b>انسحبت من المعركة!</b>\n\n"
        f"💀 خسرت {loss_report['loss_pct']}% من قواتك\n"
        f"🏥 {loss_report['injured']} جندي في المستشفى\n"
        f"📉 خصم نقاط سمعة"
    )
    return True, msg


# ══════════════════════════════════════════
# 🔄 فترة التعافي
# ══════════════════════════════════════════

def set_country_recovery(country_id, minutes=RECOVERY_MINUTES):
    conn = get_db_conn()
    cursor = conn.cursor()
    recovery_until = int(time.time()) + minutes * 60
    cursor.execute("""
        INSERT INTO country_recovery (country_id, recovery_until)
        VALUES (?, ?)
        ON CONFLICT(country_id) DO UPDATE SET recovery_until = ?
    """, (country_id, recovery_until, recovery_until))
    conn.commit()


def is_country_in_recovery(country_id):
    """يرجع (True, remaining_seconds) أو (False, 0)"""
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        SELECT recovery_until FROM country_recovery
        WHERE country_id = ? AND recovery_until > ?
    """, (country_id, now))
    row = cursor.fetchone()
    if row:
        return True, row[0] - now
    return False, 0


# ══════════════════════════════════════════
# 💰 نظام الغنائم المتقدم
# ══════════════════════════════════════════

def calculate_advanced_loot(winner_cid, loser_cid, atk_initial, def_initial,
                             atk_final, def_final, no_retreat=True):
    """
    يحسب الغنائم بناءً على هامش الانتصار وعوامل إضافية.
    يرجع float
    """
    # جلب موارد الخاسر
    from database.db_queries.war_queries import update_city_resources
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COALESCE(SUM(cb.current_budget), 0)
        FROM city_budget cb
        JOIN cities c ON cb.city_id = c.id
        WHERE c.country_id = ?
    """, (loser_cid,))
    row = cursor.fetchone()
    loser_budget = float(row[0]) if row else 0

    # نسبة الغنيمة بناءً على هامش الانتصار
    total_init = max(1, atk_initial + def_initial)
    winner_init = atk_initial if winner_cid != loser_cid else def_initial
    margin = max(0, (winner_init - (total_init - winner_init)) / total_init)
    loot_pct = LOOT_MIN_PCT + (LOOT_MAX_PCT - LOOT_MIN_PCT) * min(1.0, margin * 2)

    base_loot = loser_budget * loot_pct

    # مكافأة عدم الانسحاب
    if no_retreat:
        base_loot *= 1.1

    # مكافأة الخسائر الأقل
    winner_loss_pct = max(0, (winner_init - (atk_final if winner_cid != loser_cid else def_final)) / max(1, winner_init))
    if winner_loss_pct < 0.2:
        base_loot *= 1.15

    # ─── تطبيق حدث مهرجان الغنائم ───
    try:
        from modules.progression.global_events import get_event_effect
        loot_event = get_event_effect("loot_bonus")
        if loot_event > 0:
            base_loot *= (1 + loot_event)
    except Exception:
        pass

    # خصم من ميزانية الخاسر
    actual_loot = min(base_loot, loser_budget * 0.20)  # لا يتجاوز 20% من الميزانية
    if actual_loot > 0:
        cities = get_all_cities_of_country_by_country_id(loser_cid)
        if cities:
            per_city = actual_loot / len(cities)
            for city in cities:
                cid = city["id"] if isinstance(city, dict) else city[0]
                cursor.execute("""
                    UPDATE city_budget SET current_budget = MAX(0, current_budget - ?)
                    WHERE city_id = ?
                """, (per_city, cid))
            conn.commit()

    return max(0, round(actual_loot, 2))


# ══════════════════════════════════════════
# 🚛 وقت سفر الدعم
# ══════════════════════════════════════════

def schedule_delayed_support(battle_id, supporter_country_id, supporter_user_id,
                              side, power, travel_seconds):
    """
    يُجدول وصول الدعم بعد وقت سفر.
    يُرسل إشعاراً فورياً ثم يضيف القوة بعد الوصول.
    """
    import threading
    from core.bot import bot

    def _arrive():
        time.sleep(travel_seconds)
        from database.db_queries.advanced_war_queries import get_battle_by_id, add_supporter
        battle = get_battle_by_id(battle_id)
        if not battle or battle["status"] == "finished":
            return

        add_supporter(battle_id, supporter_country_id, supporter_user_id, side, power)

        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM countries WHERE id = ?", (supporter_country_id,))
        r = cursor.fetchone()
        sname = r[0] if r else "حليف"

        from modules.war.live_battle_engine import notify_support_arrived
        notify_support_arrived(battle, sname, side, power)

    # إشعار فوري
    try:
        bot.send_message(
            supporter_user_id,
            f"🚛 <b>التعزيزات في الطريق!</b>\n"
            f"تصل خلال {travel_seconds} ثانية...",
            parse_mode="HTML"
        )
    except Exception:
        pass

    threading.Thread(target=_arrive, daemon=True).start()


def get_support_travel_time():
    """يرجع وقت سفر عشوائي بين 10 و60 ثانية"""
    return random.randint(10, 60)


# ══════════════════════════════════════════
# 🔧 مساعدات
# ══════════════════════════════════════════

def _get_country_by_user(user_id):
    from database.db_queries.countries_queries import get_country_by_owner
    c = get_country_by_owner(user_id)
    return dict(c) if c else None


def _get_capital_city_id(country_id):
    cities = get_all_cities_of_country_by_country_id(country_id)
    if not cities:
        return None
    city = cities[0]
    return city["id"] if isinstance(city, dict) else city[0]


def build_loss_report_text(atk_report, def_report, loot, supporters):
    """يبني نص التقرير النهائي المفصل"""
    sup_text = ""
    if supporters:
        sup_text = "\n\n🤝 <b>الداعمون:</b>\n"
        for s in supporters:
            side_ar = "مهاجم" if s["side"] == "attacker" else "مدافع"
            sup_text += f"  • دولة #{s['country_id']} ({side_ar}) — {s['power_contributed']:.0f}\n"

    return (
        f"\n\n💀 <b>الخسائر التفصيلية:</b>\n"
        f"  المهاجم:\n"
        f"    ⚔️ خسر {atk_report['loss_pct']}% من قواته\n"
        f"    💀 قتلى: {atk_report['killed']}\n"
        f"    🏥 مصابون: {atk_report['injured']}\n"
        f"    🔧 معدات تالفة: {atk_report['eq_damaged']}\n"
        f"  المدافع:\n"
        f"    🛡 خسر {def_report['loss_pct']}% من قواته\n"
        f"    💀 قتلى: {def_report['killed']}\n"
        f"    🏥 مصابون: {def_report['injured']}\n"
        f"    🔧 معدات تالفة: {def_report['eq_damaged']}\n"
        f"\n💰 الغنائم: {loot:.0f} Liben"
        f"{sup_text}"
    )
