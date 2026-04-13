"""
نظام التجسس العميق — عملاء متخصصون، تطور، تأثيرات على المعركة
منفصل تماماً عن الـ UI — منطق أعمال فقط
"""
import random
import time

from database.connection import get_db_conn
from database.db_queries.advanced_war_queries import (
    get_spy_units, ensure_spy_units, add_spy_operation,
    add_discovered_country, get_spy_cooldown,
)
from database.db_queries.countries_queries import get_country_by_owner
from database.db_queries.bank_queries import get_user_balance, deduct_user_balance
from database.db_queries.advanced_war_queries import update_reputation
from modules.war.power_calculator import get_country_power
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME


# ══════════════════════════════════════════
# ⚙️ ثوابت (تُقرأ من DB)
# ══════════════════════════════════════════

def _c(name: str, default):
    try:
        from core.admin import get_const_int, get_const_float
        if isinstance(default, float):
            return get_const_float(name, default)
        return get_const_int(name, int(default))
    except Exception:
        return default


# ══════════════════════════════════════════
# 🕵️ أنواع العملاء
# ══════════════════════════════════════════

AGENT_TYPES = {
    "scout": {
        "name_ar":    "🕵️ كشاف",
        "cost_key":   "scout_cost",
        "default_cost": 150,
        "effect":     "intel",          # يجمع معلومات
        "base_success": 0.70,
        "xp_reward":  10,
        "description": "يجمع معلومات عن قوة العدو وموقعه",
    },
    "saboteur": {
        "name_ar":    "💣 مخرب",
        "cost_key":   "saboteur_cost",
        "default_cost": 400,
        "effect":     "debuff",         # يُضعف العدو مؤقتاً
        "base_success": 0.50,
        "xp_reward":  25,
        "description": "يُقلل قوة العدو 15% لمدة 30 دقيقة",
    },
    "assassin": {
        "name_ar":    "☠️ قاتل",
        "cost_key":   "assassin_cost",
        "default_cost": 600,
        "effect":     "kill",           # يقتل نسبة من الجنود
        "base_success": 0.35,
        "xp_reward":  40,
        "description": "يقتل 5–10% من جنود العدو",
    },
}


# ══════════════════════════════════════════
# 📊 إدارة العملاء
# ══════════════════════════════════════════

def get_agents(country_id: int) -> list:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM spy_agents WHERE country_id = ? ORDER BY level DESC
    """, (country_id,))
    return [dict(r) for r in cursor.fetchall()]


def get_agent_count(country_id: int, agent_type: str = None) -> int:
    conn = get_db_conn()
    cursor = conn.cursor()
    if agent_type:
        cursor.execute("""
            SELECT COUNT(*) FROM spy_agents
            WHERE country_id = ? AND agent_type = ? AND status = 'active'
        """, (country_id, agent_type))
    else:
        cursor.execute("""
            SELECT COUNT(*) FROM spy_agents
            WHERE country_id = ? AND status = 'active'
        """, (country_id,))
    return cursor.fetchone()[0]


def recruit_agent(country_id: int, user_id: int, agent_type: str) -> tuple:
    """يجنّد عميلاً جديداً مقابل تكلفة"""
    if agent_type not in AGENT_TYPES:
        return False, "❌ نوع العميل غير معروف."

    info = AGENT_TYPES[agent_type]
    cost = _c(info["cost_key"], info["default_cost"])

    # ─── apply active event discount ───
    try:
        from modules.progression.global_events import get_event_effect
        import logging
        _log = logging.getLogger(__name__)
        discount = get_event_effect("troop_cost_discount")
        if discount > 0:
            cost = round(cost * (1 - discount))
            _log.info("[EVENT_APPLIED] type=troop_cost_discount (spy recruit), discount=%.0f%%, final_price=%s",
                      discount * 100, cost)
        else:
            _log.debug("[EVENT_SKIP] troop_cost_discount — no active event for spy recruit")
    except Exception:
        pass

    balance = get_user_balance(user_id)
    if balance < cost:
        return False, f"❌ رصيدك غير كافٍ! تحتاج {cost} {CURRENCY_ARABIC_NAME} (رصيدك: {balance:.0f})"

    deduct_user_balance(user_id, cost)

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO spy_agents (country_id, agent_type, level, experience, status)
        VALUES (?, ?, 1, 0, 'active')
    """, (country_id, agent_type))
    conn.commit()

    return True, f"✅ تم تجنيد {info['name_ar']} بتكلفة {cost} {CURRENCY_ARABIC_NAME}"


def _add_agent_xp(agent_id: int, xp: int):
    """يُضيف XP للعميل ويرقيه إذا لزم"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT level, experience FROM spy_agents WHERE id = ?", (agent_id,))
    row = cursor.fetchone()
    if not row:
        return

    level, exp = row[0], row[1]
    new_exp = exp + xp
    level_up_xp = _c("spy_level_up_xp", 100)

    if new_exp >= level_up_xp and level < 10:
        new_level = level + 1
        new_exp   = new_exp - level_up_xp
        cursor.execute("""
            UPDATE spy_agents SET level = ?, experience = ? WHERE id = ?
        """, (new_level, new_exp, agent_id))
    else:
        cursor.execute("UPDATE spy_agents SET experience = ? WHERE id = ?", (new_exp, agent_id))

    conn.commit()


def _kill_agent(agent_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE spy_agents SET status = 'dead' WHERE id = ?", (agent_id,))
    conn.commit()


# ══════════════════════════════════════════
# 🎯 تنفيذ مهمة التجسس
# ══════════════════════════════════════════

def execute_spy_mission(attacker_user_id: int, target_country_id: int,
                        agent_type: str = "scout") -> tuple:
    """
    ينفذ مهمة تجسس متقدمة.
    يرجع (result_type: str, message: str, effects: dict)
    effects: تأثيرات على المعركة القادمة
    """
    attacker_country = get_country_by_owner(attacker_user_id)
    if not attacker_country:
        return "failed", "❌ لا تملك دولة!", {}
    attacker_country = dict(attacker_country)
    attacker_cid = attacker_country["id"]

    ensure_spy_units(attacker_cid)
    ensure_spy_units(target_country_id)

    # ─── فحص الكولداون ───
    can_spy, remaining, cached = get_spy_cooldown(attacker_cid, target_country_id)
    if not can_spy and cached:
        from utils.helpers import format_remaining_time
        icon = {"success": "🎯", "partial": "⚠️", "failed": "❌",
                "fake": "💀", "detected": "🚨"}.get(cached["result"], "❓")
        return cached["result"], (
            f"⏳ <b>كولداون التجسس</b> — متبقي: {format_remaining_time(remaining)}\n\n"
            f"{icon} <b>آخر نتيجة:</b>\n{cached['info']}"
        ), {}

    # ─── التحقق من وجود عميل ───
    if agent_type not in AGENT_TYPES:
        agent_type = "scout"

    info = AGENT_TYPES[agent_type]
    cost = _c(info["cost_key"], info["default_cost"])

    balance = get_user_balance(attacker_user_id)
    if balance < cost:
        return "failed", f"❌ رصيدك غير كافٍ! تحتاج {cost} {CURRENCY_ARABIC_NAME}", {}

    deduct_user_balance(attacker_user_id, cost)

    # ─── جلب أفضل عميل متاح ───
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, level FROM spy_agents
        WHERE country_id = ? AND agent_type = ? AND status = 'active'
        ORDER BY level DESC LIMIT 1
    """, (attacker_cid, agent_type))
    agent_row = cursor.fetchone()
    agent_id    = agent_row[0] if agent_row else None
    agent_level = agent_row[1] if agent_row else 1

    # ─── حساب احتمال النجاح ───
    atk_spy = get_spy_units(attacker_cid)
    def_spy = get_spy_units(target_country_id)

    spy_lvl  = atk_spy["spy_level"] + agent_level
    def_lvl  = def_spy["defense_level"]
    camo_lvl = def_spy["camouflage_level"]

    base_success = info["base_success"]
    level_bonus  = (spy_lvl - def_lvl) * 0.08
    success_rate = max(0.05, min(0.95, base_success + level_bonus))

    roll = random.random()

    # ─── فحص الاستخبارات المضادة ───
    detect_chance = max(0.0, min(0.7, (def_lvl - spy_lvl) * 0.12 + camo_lvl * 0.05))
    if random.random() < detect_chance:
        # اكتشاف العميل
        if agent_id:
            _kill_agent(agent_id)
        update_reputation(attacker_user_id, ignored=1)
        msg = (
            f"🚨 <b>تم اكتشاف عميلك وتصفيته!</b>\n"
            f"نوع العميل: {info['name_ar']}\n"
            f"💸 خسرت {cost} {CURRENCY_ARABIC_NAME}\n"
            f"📉 خصم نقاط سمعة"
        )
        add_spy_operation(attacker_cid, target_country_id, "detected", msg)
        return "detected", msg, {}

    # ─── تنفيذ التأثير حسب نوع العميل ───
    effects = {}

    if roll <= success_rate:
        # نجاح
        result, msg, effects = _apply_agent_effect(
            agent_type, attacker_cid, target_country_id, camo_lvl, cost, agent_level
        )
        if agent_id:
            _add_agent_xp(agent_id, _c("spy_xp_per_mission", 10))
        if result in ("success", "partial"):
            add_discovered_country(attacker_cid, target_country_id)
    else:
        # فشل
        result = "failed"
        msg    = f"❌ <b>فشلت المهمة!</b>\n💸 خسرت {cost} {CURRENCY_ARABIC_NAME}"

    add_spy_operation(attacker_cid, target_country_id, result, msg)
    return result, msg, effects


def _apply_agent_effect(agent_type: str, attacker_cid: int, target_cid: int,
                        camo_lvl: int, cost: int, agent_level: int) -> tuple:
    """يُطبّق تأثير العميل ويرجع (result, message, effects_dict)"""
    real_power = get_country_power(target_cid)
    effects    = {}

    if agent_type == "scout":
        # كشاف — معلومات استخباراتية
        from database.db_queries.advanced_war_queries import get_visibility
        vis = get_visibility(target_cid)
        code_hint = ""
        if vis and vis["visibility_mode"] == "hidden":
            code_hint = f"\n🔑 كود الهجوم: <code>{vis['daily_attack_code']}</code>"

        # دقة المعلومات تعتمد على مستوى العميل
        if agent_level >= 3:
            result = "success"
            msg = (
                f"🎯 <b>معلومات دقيقة (كشاف مستوى {agent_level}):</b>\n"
                f"القوة العسكرية: {real_power:.0f}{code_hint}\n"
                f"💸 تكلفة: {cost} {CURRENCY_ARABIC_NAME}"
            )
            effects["intel_accuracy"] = 1.0
        else:
            shown = real_power * random.uniform(0.85, 1.15)
            result = "partial"
            msg = (
                f"⚠️ <b>معلومات جزئية (كشاف مستوى {agent_level}):</b>\n"
                f"القوة التقريبية: {shown:.0f}{code_hint}\n"
                f"💸 تكلفة: {cost} {CURRENCY_ARABIC_NAME}"
            )
            effects["intel_accuracy"] = 0.7

    elif agent_type == "saboteur":
        # مخرب — يُضعف العدو مؤقتاً
        debuff_pct = 0.10 + agent_level * 0.02  # 12–30% حسب المستوى
        duration   = 1800  # 30 دقيقة

        # تطبيق التأثير عبر battle_effects إذا كانت هناك معركة نشطة
        _apply_saboteur_debuff(target_cid, debuff_pct, duration)

        result = "success"
        msg = (
            f"💣 <b>نجح المخرب (مستوى {agent_level})!</b>\n"
            f"قوة العدو انخفضت {int(debuff_pct*100)}% لمدة 30 دقيقة\n"
            f"💸 تكلفة: {cost} {CURRENCY_ARABIC_NAME}"
        )
        effects["sabotage_pct"] = debuff_pct
        effects["sabotage_duration"] = duration

    elif agent_type == "assassin":
        # قاتل — يقتل نسبة من الجنود
        kill_pct = 0.03 + agent_level * 0.01  # 4–13% حسب المستوى
        killed   = _apply_assassination(target_cid, kill_pct)

        result = "success"
        msg = (
            f"☠️ <b>نجح القاتل (مستوى {agent_level})!</b>\n"
            f"تم تصفية {killed} جندي من قوات العدو\n"
            f"💸 تكلفة: {cost} {CURRENCY_ARABIC_NAME}"
        )
        effects["troops_killed"] = killed

    else:
        result = "partial"
        msg    = f"⚠️ تأثير غير معروف للعميل\n💸 تكلفة: {cost} {CURRENCY_ARABIC_NAME}"

    return result, msg, effects


def _apply_saboteur_debuff(target_cid: int, debuff_pct: float, duration: int):
    """يُطبّق تأثير التخريب على المعركة النشطة أو يحفظه للمعركة القادمة"""
    from database.db_queries.advanced_war_queries import get_active_battles_for_country
    active = get_active_battles_for_country(target_cid)
    if active:
        battle = active[0]
        try:
            from modules.war.live_battle_engine import add_battle_effect
            add_battle_effect(
                battle["id"], target_cid, 0,
                "sabotage", debuff_pct, duration, source="spy"
            )
        except Exception:
            pass
    else:
        # حفظ التأثير للمعركة القادمة في جدول مؤقت
        conn = get_db_conn()
        cursor = conn.cursor()
        expires = int(time.time()) + duration
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO army_maintenance
                (country_id, hourly_cost, last_paid_at, debt)
                VALUES (?, COALESCE((SELECT hourly_cost FROM army_maintenance WHERE country_id=?), 0),
                        COALESCE((SELECT last_paid_at FROM army_maintenance WHERE country_id=?), strftime('%s','now')),
                        COALESCE((SELECT debt FROM army_maintenance WHERE country_id=?), 0) + ?)
            """, (target_cid, target_cid, target_cid, target_cid, debuff_pct * 1000))
            conn.commit()
        except Exception:
            pass


def _apply_assassination(target_cid: int, kill_pct: float) -> int:
    """يقتل نسبة من جنود الهدف ويرجع عدد القتلى"""
    from database.db_queries.countries_queries import get_all_cities_of_country_by_country_id
    from database.db_queries.war_queries import get_city_troops

    cities = get_all_cities_of_country_by_country_id(target_cid)
    if not cities:
        return 0

    conn = get_db_conn()
    cursor = conn.cursor()
    total_killed = 0

    for city in cities:
        cid = city["id"] if isinstance(city, dict) else city[0]
        troops = get_city_troops(cid)
        for t in troops:
            t = dict(t)
            qty = t.get("quantity", 0)
            if qty <= 0:
                continue
            killed = max(0, int(qty * kill_pct * random.uniform(0.8, 1.2)))
            if killed > 0:
                new_qty = max(0, qty - killed)
                cursor.execute("""
                    UPDATE city_troops SET quantity = ?
                    WHERE city_id = ? AND troop_type_id = ?
                """, (new_qty, cid, t["troop_type_id"]))
                total_killed += killed

    conn.commit()
    return total_killed


# ══════════════════════════════════════════
# 📡 نظام الاستكشاف والرادار
# ══════════════════════════════════════════

def explore_targets(attacker_user_id: int, cost: int) -> tuple:
    """
    يستكشف هدفاً عشوائياً قابلاً للهجوم.
    لا يخصم عملات — الخصم يتم في الطبقة الأعلى (الهاندلر).
    يرجع (True, country_dict) أو (False, error_msg)
    """
    country = get_country_by_owner(attacker_user_id)
    if not country:
        return False, "❌ لا تملك دولة!"
    country = dict(country)
    cid = country["id"]

    from database.db_queries.countries_queries import get_all_countries
    from database.db_queries.advanced_war_queries import get_visibility
    from modules.war.country_level import get_country_tier, ALLOWED_ATTACKS

    my_tier = get_country_tier(cid)
    all_countries = [dict(c) for c in get_all_countries() if c["id"] != cid]

    # فلترة الدول المناسبة للهجوم
    candidates = []
    for c in all_countries:
        target_tier = get_country_tier(c["id"])
        if not ALLOWED_ATTACKS.get((my_tier, target_tier), True):
            continue
        vis = get_visibility(c["id"])
        if not vis or vis["visibility_mode"] == "public":
            candidates.append({**c, "visibility": "public"})
        elif random.random() < 0.3:
            candidates.append({**c, "visibility": "hidden"})

    if not candidates:
        _log_exploration(cid, "failed", None, cost)
        return False, "❌ لم يُعثر على أهداف مناسبة."

    target = random.choice(candidates[:min(5, len(candidates))])

    add_discovered_country(cid, target["id"])
    _log_exploration(cid, "success", target["id"], cost)

    vis_icon = "🌑" if target.get("visibility") == "hidden" else "🏳️"
    from modules.war.power_calculator import get_country_power
    power = get_country_power(target["id"])

    return True, {
        **target,
        "message": (
            f"🔍 <b>اكتشفت هدفاً جديداً!</b>\n\n"
            f"{vis_icon} <b>{target['name']}</b>\n"
            f"💪 القوة: {power:.0f}\n"
            f"💸 تكلفة الاستكشاف: {cost} {CURRENCY_ARABIC_NAME}\n\n"
            f"✅ تمت إضافته لقائمة أهدافك!"
        )
    }


def get_radar_targets(attacker_user_id: int, limit: int = 5) -> list:
    """
    يرجع قائمة دول قريبة في القوة (رادار).
    يعتمد على مستوى الجواسيس.
    """
    country = get_country_by_owner(attacker_user_id)
    if not country:
        return []
    country = dict(country)
    cid = country["id"]

    ensure_spy_units(cid)
    spy_data = get_spy_units(cid)
    spy_lvl  = spy_data["spy_level"]

    from modules.war.power_calculator import get_country_power
    from database.db_queries.countries_queries import get_all_countries
    from modules.war.country_level import get_country_tier, ALLOWED_ATTACKS

    my_power = get_country_power(cid)
    my_tier  = get_country_tier(cid)

    # نطاق الرادار يتوسع مع مستوى الجواسيس
    radar_range = 0.3 + spy_lvl * 0.1  # 40–130% من قوتك

    result = []
    for c in get_all_countries():
        if c["id"] == cid:
            continue
        target_tier = get_country_tier(c["id"])
        if not ALLOWED_ATTACKS.get((my_tier, target_tier), True):
            continue
        t_power = get_country_power(c["id"])
        if my_power > 0:
            ratio = t_power / my_power
            if 1 - radar_range <= ratio <= 1 + radar_range:
                result.append({
                    "id": c["id"], "name": c["name"],
                    "power": t_power, "tier": target_tier
                })

    result.sort(key=lambda x: abs(x["power"] - my_power))
    return result[:limit]


def _log_exploration(country_id: int, result: str, discovered_id, cost: float):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO exploration_log (country_id, result, discovered_country_id, cost)
        VALUES (?, ?, ?, ?)
    """, (country_id, result, discovered_id, cost))
    conn.commit()
