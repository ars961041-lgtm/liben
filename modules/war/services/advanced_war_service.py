"""
نظام الحرب المتقدم — منطق الأعمال
"""
import random
import time
import threading

from database.connection import get_db_conn
from database.db_queries.advanced_war_queries import (
    create_country_battle, get_battle_by_id,
    set_battle_in_battle, finish_battle, finish_fake_battle,
    get_total_support_power, get_spy_units, ensure_spy_units,
    add_spy_operation, get_pending_support_requests,
    update_support_request_status, create_support_request,
    update_reputation, get_active_battles_for_country,
    add_supporter, is_country_frozen,
    get_visibility, ensure_visibility, add_discovered_country,
    can_send_support_request, create_support_request_targeted,
)
from database.db_queries.war_queries import update_city_resources
from database.db_queries.countries_queries import (
    get_country_by_owner, get_all_cities_of_country_by_country_id,
)
from database.db_queries.alliances_queries import get_alliance_by_user
from modules.war.power_calculator import (
    get_country_power, aggregate_country_forces, calc_raw_power
)
from modules.war.war_simulator import simulate_battle
from utils.helpers import get_lines, format_remaining_time
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

TRAVEL_TIME  = 20 * 60
BATTLE_TIME  = 5  * 60
SUDDEN_TRAVEL = 5 * 60
HIDDEN_COST  = 200   # Bito يومياً للإخفاء


# ══════════════════════════════════════════
# 👁️ نظام الرؤية
# ══════════════════════════════════════════

def set_country_visibility(user_id, mode):
    """
    mode: 'hidden' أو 'public'
    يرجع (True, msg) أو (False, msg)
    """
    country = get_country_by_owner(user_id)
    if not country:
        return False, "❌ لا تملك دولة!"
    country = dict(country)
    cid = country["id"]

    if mode == "hidden":
        from database.db_queries.bank_queries import get_user_balance, deduct_user_balance
        bal = get_user_balance(user_id)
        if bal < HIDDEN_COST:
            return False, f"❌ تحتاج {HIDDEN_COST} {CURRENCY_ARABIC_NAME} لتفعيل الإخفاء."
        deduct_user_balance(user_id, HIDDEN_COST)
        from database.db_queries.advanced_war_queries import set_visibility_mode
        set_visibility_mode(cid, "hidden")
        return True, f"🌑 دولتك الآن مخفية! تكلفة: {HIDDEN_COST} {CURRENCY_ARABIC_NAME}\nكود هجومك اليومي: {get_visibility(cid)['daily_attack_code']}"
    else:
        from database.db_queries.advanced_war_queries import set_visibility_mode
        set_visibility_mode(cid, "public")
        return True, "☀️ دولتك الآن ظاهرة للجميع."


def get_attackable_targets(attacker_user_id):
    """
    يرجع قائمة الدول التي يمكن مهاجمتها:
    - الدول العامة
    - الدول المكتشفة (من تجسس ناجح)
    """
    country = get_country_by_owner(attacker_user_id)
    if not country:
        return []
    country = dict(country)
    cid = country["id"]

    from database.db_queries.advanced_war_queries import get_discovered_countries
    from database.db_queries.countries_queries import get_all_countries

    all_countries = [dict(c) for c in get_all_countries() if c["id"] != cid]
    discovered_ids = {d["target_country_id"] for d in get_discovered_countries(cid)}

    result = []
    for c in all_countries:
        vis = get_visibility(c["id"])
        if not vis or vis["visibility_mode"] == "public":
            result.append({**c, "visibility": "public", "discovered": True})
        elif c["id"] in discovered_ids:
            result.append({**c, "visibility": "hidden", "discovered": True})
        # الدول المخفية غير المكتشفة لا تظهر

    return result


def verify_hidden_attack(attacker_user_id, target_country_id, code):
    """
    يتحقق من كود الهجوم على دولة مخفية.
    يرجع (True, msg) أو (False, msg)
    """
    from database.db_queries.advanced_war_queries import verify_attack_code
    if verify_attack_code(target_country_id, code):
        # إضافة للمكتشفات
        country = get_country_by_owner(attacker_user_id)
        if country:
            add_discovered_country(dict(country)["id"], target_country_id)
        return True, "✅ الكود صحيح! يمكنك الهجوم."
    return False, "❌ الكود خاطئ!"


# ══════════════════════════════════════════
# 🚀 إطلاق هجوم
# ══════════════════════════════════════════

def launch_attack(attacker_user_id, defender_country_id,
                  battle_type="normal", attacker_cards=None):
    attacker_country = get_country_by_owner(attacker_user_id)
    if not attacker_country:
        return False, "❌ أنت لا تملك دولة!"
    attacker_country = dict(attacker_country)
    attacker_cid = attacker_country["id"]

    if attacker_cid == defender_country_id:
        return False, "❌ لا يمكنك مهاجمة دولتك!"

    frozen, rem = is_country_frozen(attacker_cid)
    if frozen:
        from utils.helpers import format_remaining_time as _fmt
        return False, f"🧊 دولتك مجمدة! متبقي: {_fmt(rem)}"

    frozen_d, _ = is_country_frozen(defender_country_id)
    if frozen_d:
        return False, "🧊 الدولة المستهدفة مجمدة!"

    active = get_active_battles_for_country(attacker_cid)
    if active:
        return False, "⚠️ لديك معركة نشطة بالفعل!"

    # ─── التحقق من فترة التعافي ───
    from modules.war.war_economy import is_country_in_recovery
    in_recovery, rec_rem = is_country_in_recovery(attacker_cid)
    if in_recovery:
        from utils.helpers import format_remaining_time as _fmt
        return False, f"🔄 دولتك في فترة تعافٍ! متبقي: {_fmt(rec_rem)}"

    # ─── فحص دين الصيانة ───
    try:
        from modules.war.maintenance_service import get_maintenance_penalty
        from core.admin import get_const_int
        penalty = get_maintenance_penalty(attacker_cid)
        debt_block = get_const_int("maintenance_debt_block", 200)
        conn2 = get_db_conn()
        cur2  = conn2.cursor()
        cur2.execute("SELECT debt FROM army_maintenance WHERE country_id = ?", (attacker_cid,))
        row2 = cur2.fetchone()
        if row2 and row2[0] >= debt_block:
            return False, (
                f"⚠️ <b>دين الصيانة مرتفع جداً!</b>\n"
                f"الدين: {row2[0]:.0f} {CURRENCY_ARABIC_NAME}\n"
                f"ادفع الدين أولاً قبل الهجوم.\n"
                f"اكتب: <code>مدينتي</code> لعرض الصيانة."
            )
    except Exception:
        pass

    # التحقق من القوة
    atk_power = get_country_power(attacker_cid)
    if atk_power == 0:
        return False, "❌ لا يمكنك الهجوم بقوة صفر! اشترِ جنوداً أولاً."

    # ─── تكلفة الهجوم ───
    from modules.war.war_economy import charge_war_cost
    ok, cost_msg = charge_war_cost(attacker_user_id, "attack")
    if not ok:
        return False, cost_msg

    # ─── حماية المبتدئين ───
    from modules.war.war_balance import is_beginner_protected
    if is_beginner_protected(defender_country_id):
        return False, "🛡️ هذه الدولة محمية! مدنها لا تزال في مراحل البناء الأولى."

    # ─── فحص فارق المستوى ───
    from modules.war.country_level import check_attack_level
    ok_lvl, lvl_msg = check_attack_level(attacker_cid, defender_country_id)
    if not ok_lvl:
        return False, lvl_msg

    # التحقق من الرؤية
    vis = get_visibility(defender_country_id)
    if vis and vis["visibility_mode"] == "hidden":
        from database.db_queries.advanced_war_queries import is_country_discovered
        if not is_country_discovered(attacker_cid, defender_country_id):
            return False, "🌑 هذه الدولة مخفية! تجسس عليها أولاً أو أدخل الكود الصحيح."

    # حساب وقت السفر
    travel_seconds = TRAVEL_TIME
    if battle_type == "sudden":
        travel_seconds = SUDDEN_TRAVEL
    elif attacker_cards:
        for card in attacker_cards:
            if card.get("effect_type") == "reduce_travel":
                travel_seconds = max(60, travel_seconds - int(card["effect_value"]))

    # تأثير ترقية التحالف rapid_deployment
    try:
        from database.db_queries.alliances_queries import get_alliance_by_country, get_alliance_effect
        atk_alliance = get_alliance_by_country(attacker_cid)
        if atk_alliance:
            reduce = get_alliance_effect(atk_alliance["id"], "travel_reduce")
            travel_seconds = max(60, travel_seconds - int(reduce))
    except Exception:
        pass

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT owner_id FROM countries WHERE id = ?", (defender_country_id,))
    row = cursor.fetchone()
    if not row:
        return False, "❌ الدولة المستهدفة غير موجودة!"
    defender_user_id = row[0]

    battle_id = create_country_battle(
        attacker_cid, defender_country_id,
        attacker_user_id, defender_user_id,
        travel_seconds=travel_seconds,
        battle_type=battle_type
    )
    _schedule_travel_end(battle_id, travel_seconds)
    return True, battle_id, travel_seconds


# ══════════════════════════════════════════
# ⏱️ جدولة المراحل
# ══════════════════════════════════════════

# ══════════════════════════════════════════
# ⏱️ جدولة المراحل
# ══════════════════════════════════════════

def _schedule_travel_end(battle_id, delay):
    """
    ينتظر انتهاء وقت السفر بالاستناد إلى travel_end_time في DB.
    يتحقق كل ثانية — يستجيب فوراً لأي تسريع يُحدّث DB.
    """
    def _run():
        while True:
            time.sleep(1)
            battle = get_battle_by_id(battle_id)
            if not battle or battle["status"] != "traveling":
                return  # انتهت أو تغيرت الحالة
            if int(time.time()) >= (battle.get("travel_end_time") or 0):
                _transition_to_battle(battle_id)
                return
    threading.Thread(target=_run, daemon=True).start()


def _schedule_battle_end(battle_id, delay):
    """
    ينتظر انتهاء وقت المعركة بالاستناد إلى battle_end_time في DB.
    يتحقق كل ثانية — يستجيب فوراً لأي تسريع يُحدّث DB.
    """
    def _run():
        while True:
            time.sleep(1)
            battle = get_battle_by_id(battle_id)
            if not battle or battle["status"] != "in_battle":
                return  # انتهت أو تغيرت الحالة
            if int(time.time()) >= (battle.get("battle_end_time") or 0):
                _resolve_battle(battle_id)
                return
    threading.Thread(target=_run, daemon=True).start()


def _schedule_support_requests(battle_id, interval=60, max_rounds=5):
    def _run():
        for _ in range(max_rounds):
            time.sleep(interval)
            battle = get_battle_by_id(battle_id)
            if not battle or battle["status"] != "in_battle":
                break
            _send_alliance_support_requests(battle_id)
    threading.Thread(target=_run, daemon=True).start()


# ══════════════════════════════════════════
# 🔴 الانتقال إلى القتال
# ══════════════════════════════════════════

def _transition_to_battle(battle_id):
    battle = get_battle_by_id(battle_id)
    if not battle or battle["status"] != "traveling":
        return
    if battle["battle_type"] == "fake":
        _notify_fake_attack_end(battle)
        finish_fake_battle(battle_id)
        return
    print(f"[BATTLE_TRANSITION] id={battle_id} traveling → combat")
    set_battle_in_battle(battle_id, BATTLE_TIME)
    _notify_battle_started(battle)
    # ─── تشغيل محرك المعركة الحية ───
    from modules.war.live_battle_engine import start_live_battle
    start_live_battle(battle_id)
    _schedule_support_requests(battle_id, interval=60)


# ══════════════════════════════════════════
# ⚫ حل المعركة — يستخدم get_country_power
# ══════════════════════════════════════════

def _resolve_battle(battle_id):
    battle = get_battle_by_id(battle_id)
    if not battle or battle["status"] != "in_battle":
        return

    attacker_cid = battle["attacker_country_id"]
    defender_cid = battle["defender_country_id"]

    # القوة الحقيقية عبر الدالة المركزية
    atk_power = get_country_power(attacker_cid)
    def_power = get_country_power(defender_cid)

    # قوة الداعمين
    atk_power += max(0, get_total_support_power(battle_id, "attacker"))
    def_power += max(0, get_total_support_power(battle_id, "defender"))

    if battle["battle_type"] == "sudden":
        sudden_mult = 0.70
        try:
            from modules.progression.global_events import get_event_effect
            sb = get_event_effect("sudden_bonus")
            if sb > 0:
                sudden_mult = min(1.0, sudden_mult + sb)
        except Exception:
            pass
        atk_power = max(0, atk_power * sudden_mult)

    # ─── تأثيرات الأحداث العالمية (atk_bonus / def_bonus) ───
    try:
        from modules.progression.global_events import get_event_effect
        atk_event = get_event_effect("atk_bonus")
        def_event = get_event_effect("def_bonus")
        if atk_event:
            atk_power = max(0, atk_power * (1 + atk_event))
        if def_event:
            def_power = max(0, def_power * (1 + def_event))
    except Exception:
        pass

    # ─── عقوبة فارق الفئة + مضاعف المكافأة ───
    from modules.war.country_level import get_country_tier, get_attack_penalty, get_reward_multiplier
    atk_tier = get_country_tier(attacker_cid)
    def_tier = get_country_tier(defender_cid)
    attack_penalty  = get_attack_penalty(atk_tier, def_tier)
    reward_mult     = get_reward_multiplier(atk_tier, def_tier)
    if attack_penalty < 1.0:
        atk_power = max(0, atk_power * attack_penalty)

    # محاكاة الخسائر
    atk_troops, atk_eq = aggregate_country_forces(attacker_cid)
    def_troops, def_eq = aggregate_country_forces(defender_cid)
    result = simulate_battle(atk_troops or [], def_troops or [], atk_eq or [], def_eq or [])

    winner_cid = attacker_cid if atk_power >= def_power else defender_cid
    loot = max(0, _calculate_loot(winner_cid, attacker_cid, defender_cid))

    # تطبيق مضاعف المكافأة على الغنائم
    loot = round(loot * reward_mult)

    # تطبيق الخسائر — المدافع يتلقى خسائر أثقل ×1.3
    _apply_country_losses(attacker_cid, result["attacker_losses"])
    heavy = [{**l, "lost": max(0, int(l["lost"] * 1.3))} for l in result["defender_losses"]]
    _apply_country_losses(defender_cid, heavy)

    if loot > 0:
        cap = _get_capital_city_id(winner_cid)
        if cap:
            update_city_resources(cap, loot)

    committed = finish_battle(battle_id, winner_cid, loot, max(0, atk_power), max(0, def_power))
    if not committed:
        print(f"[BATTLE_AUTO_RESOLVE] id={battle_id} reason=already_committed_by_other (in _resolve_battle) — skipped")
        return
    print(f"[BATTLE_CLEANUP] id={battle_id} removed_from_active (_resolve_battle)")
    _notify_battle_result(battle, winner_cid, loot, atk_power, def_power, result,
                          attack_penalty=attack_penalty, reward_mult=reward_mult)
    _update_supporter_reputation(battle_id)

    winner_uid = battle["attacker_user_id"] if winner_cid == attacker_cid else battle["defender_user_id"]
    loser_uid  = battle["defender_user_id"] if winner_cid == attacker_cid else battle["attacker_user_id"]
    update_reputation(winner_uid, helped=1)
    update_reputation(loser_uid)


# ══════════════════════════════════════════
# 🕵️ الجواسيس — تكلفة + كولداون + نتائج مخزنة
# ══════════════════════════════════════════

def send_spies(attacker_user_id, target_country_id, extra_card=False):
    """
    يرسل جواسيس مع:
    - خصم تكلفة Bito
    - كولداون لكل هدف (120 ثانية افتراضياً)
    - نتائج مخزنة — لا إعادة توليد مجانية
    يرجع (result_type, message)
    """
    attacker_country = get_country_by_owner(attacker_user_id)
    if not attacker_country:
        return "failed", "❌ لا تملك دولة!"
    attacker_country = dict(attacker_country)
    attacker_cid = attacker_country["id"]

    ensure_spy_units(attacker_cid)
    ensure_spy_units(target_country_id)

    # ─── فحص الكولداون وإرجاع النتيجة المخزنة ───
    from database.db_queries.advanced_war_queries import get_spy_cooldown
    can_spy, remaining, cached = get_spy_cooldown(attacker_cid, target_country_id)

    if not can_spy and cached:
        from utils.helpers import format_remaining_time
        cached_icon = {"success": "🎯", "partial": "⚠️", "failed": "❌",
                       "fake": "💀", "detected": "🚨"}.get(cached["result"], "❓")
        return cached["result"], (
            f"⏳ <b>كولداون التجسس</b>\n"
            f"متبقي: {format_remaining_time(remaining)}\n\n"
            f"{cached_icon} <b>آخر نتيجة مخزنة:</b>\n"
            f"{cached['info']}"
        )

    # ─── خصم تكلفة التجسس ───
    try:
        from core.admin import get_const_int
        spy_cost = get_const_int("spy_cost", 150)
    except Exception:
        spy_cost = 150

    from database.db_queries.bank_queries import get_user_balance, deduct_user_balance
    balance = get_user_balance(attacker_user_id)
    if balance < spy_cost:
        return "failed", f"❌ رصيدك غير كافٍ للتجسس!\nالتكلفة: {spy_cost} {CURRENCY_ARABIC_NAME} (رصيدك: {balance:.0f})"

    deduct_user_balance(attacker_user_id, spy_cost)

    # ─── فحص الاستخبارات المضادة ───
    from modules.war.war_balance import counter_intelligence_check, generate_fake_intel
    ci = counter_intelligence_check(attacker_cid, target_country_id)

    if ci["detected"]:
        if ci["spy_killed"]:
            update_reputation(attacker_user_id, ignored=1)
            msg = (
                "💀 <b>تم اكتشاف جاسوسك وتصفيته!</b>\n"
                "📉 خصم نقاط سمعة\n"
                f"💸 خسرت {spy_cost} {CURRENCY_ARABIC_NAME}"
            )
            add_spy_operation(attacker_cid, target_country_id, "detected", msg)
            # ─── فحص إنجاز الاكتشاف ───
            try:
                from modules.progression.achievements import trigger_achievement_check
                trigger_achievement_check(attacker_user_id, "spy_detected")
            except Exception:
                pass
            return "detected", msg
        elif ci["fake_intel"]:
            fake_msg = generate_fake_intel(target_country_id)
            add_spy_operation(attacker_cid, target_country_id, "fake", fake_msg)
            return "fake", fake_msg

    # ─── حساب نتيجة التجسس ───
    atk_spy = get_spy_units(attacker_cid)
    def_spy = get_spy_units(target_country_id)

    spy_lvl  = atk_spy["spy_level"] + (2 if extra_card else 0)
    def_lvl  = def_spy["defense_level"]
    camo_lvl = def_spy["camouflage_level"]

    diff = spy_lvl - def_lvl
    roll = random.random()

    # ─── تطبيق مكافأة حدث التجسس العالمي ───
    try:
        from modules.progression.global_events import get_event_effect
        spy_event_bonus = get_event_effect("spy_success_bonus")
        if spy_event_bonus > 0:
            roll = max(0.0, roll - spy_event_bonus)
    except Exception:
        pass

    if diff >= 2:
        result = "success"
    elif diff >= 0:
        result = "partial" if roll > 0.4 else "failed"
    elif diff >= -2:
        result = "failed" if roll > 0.3 else "fake"
    else:
        result = "fake"

    if result in ("success", "partial"):
        add_discovered_country(attacker_cid, target_country_id)

    info = _build_spy_report(target_country_id, result, camo_lvl, spy_cost)
    add_spy_operation(attacker_cid, target_country_id, result, info)

    # ─── فحص إنجازات التجسس ───
    if result in ("success", "partial"):
        try:
            from modules.progression.achievements import trigger_achievement_check
            trigger_achievement_check(attacker_user_id, "spy_success")
        except Exception:
            pass

    return result, info


def _build_spy_report(target_country_id, result, camo_lvl, spy_cost=0):
    real_power = get_country_power(target_country_id)
    cost_note  = f"\n💸 تكلفة العملية: {spy_cost} {CURRENCY_ARABIC_NAME}" if spy_cost else ""

    if result == "success":
        vis = get_visibility(target_country_id)
        code_hint = f"\n🔑 كود الهجوم: {vis['daily_attack_code']}" if vis and vis["visibility_mode"] == "hidden" else ""
        return f"🎯 <b>معلومات دقيقة:</b>\nالقوة العسكرية: {real_power:.0f}{code_hint}{cost_note}"
    elif result == "partial":
        shown = real_power * random.uniform(0.75, 1.25)
        return f"⚠️ <b>معلومات جزئية:</b>\nالقوة التقريبية: {shown:.0f}{cost_note}"
    elif result == "failed":
        return f"❌ <b>فشلت عملية التجسس!</b>{cost_note}"
    else:
        fake_power = real_power * random.uniform(0.3, 1.8) * (1 + camo_lvl * 0.15)
        return f"💀 <b>معلومات مزيفة (تحذير!):</b>\nالقوة المُبلَّغة: {fake_power:.0f}{cost_note}"


# ══════════════════════════════════════════
# 🤝 طلبات الدعم
# ══════════════════════════════════════════

def send_support_request_all(battle_id, requester_user_id, side):
    """يرسل طلب دعم لكل أعضاء التحالف مع كولداون 60 ثانية"""
    country = get_country_by_owner(requester_user_id)
    if not country:
        return False, "❌ لا تملك دولة!"
    country = dict(country)
    cid = country["id"]

    if not can_send_support_request(battle_id, cid):
        return False, "⏳ انتظر 60 ثانية قبل إرسال طلب دعم جديد."

    alliance = get_alliance_by_user(requester_user_id)
    if not alliance:
        return False, "❌ لست في أي تحالف!"

    from database.db_queries.alliances_queries import get_alliance_by_id
    alliance_data = get_alliance_by_id(alliance["id"])
    if not alliance_data:
        return False, "❌ خطأ في بيانات التحالف."

    sent = 0
    for member in alliance_data["members"]:
        member_uid = member["user_id"] if isinstance(member, dict) else member[0]
        if member_uid == requester_user_id:
            continue
        req_id = create_support_request_targeted(battle_id, cid, None, member_uid, side)
        _notify_support_request(member_uid, battle_id, req_id, side, cid)
        sent += 1

    return True, f"📣 تم إرسال طلب الدعم لـ {sent} حليف!"


def send_support_request_targeted(battle_id, requester_user_id, target_country_id, side):
    """يرسل طلب دعم لدولة محددة"""
    country = get_country_by_owner(requester_user_id)
    if not country:
        return False, "❌ لا تملك دولة!"
    country = dict(country)
    cid = country["id"]

    if not can_send_support_request(battle_id, cid):
        return False, "⏳ انتظر 60 ثانية قبل إرسال طلب دعم جديد."

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT owner_id FROM countries WHERE id = ?", (target_country_id,))
    row = cursor.fetchone()
    if not row:
        return False, "❌ الدولة غير موجودة."
    target_uid = row[0]

    req_id = create_support_request_targeted(battle_id, cid, target_country_id, target_uid, side)
    _notify_support_request(target_uid, battle_id, req_id, side, cid)
    return True, "✅ تم إرسال طلب الدعم!"


def handle_support_response(user_id, request_id, accepted):
    update_support_request_status(request_id, "accepted" if accepted else "ignored")

    if not accepted:
        update_reputation(user_id, ignored=1)
        return False, "تم تسجيل رفضك."

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM support_requests WHERE id = ?", (request_id,))
    req = cursor.fetchone()
    if not req:
        return False, "❌ الطلب غير موجود."
    req = dict(req)

    battle = get_battle_by_id(req["battle_id"])
    if not battle or battle["status"] == "finished":
        return False, "❌ المعركة انتهت."

    supporter_country = get_country_by_owner(user_id)
    if not supporter_country:
        return False, "❌ لا تملك دولة!"
    supporter_country = dict(supporter_country)

    # ─── مضاعف الدعم من الثوابت ───
    try:
        from core.admin import get_const_float
        side = req.get("side", "defender")
        mod_key = "support_atk_mod" if side == "attacker" else "support_def_mod"
        support_mod = get_const_float(mod_key, 0.60 if side == "attacker" else 0.80)
    except Exception:
        support_mod = 0.30

    power = get_country_power(supporter_country["id"]) * support_mod

    # ─── مكافأة السمعة العالية ───
    from database.db_queries.advanced_war_queries import get_reputation
    rep = get_reputation(user_id)
    if rep and rep.get("loyalty_score", 50) >= 80:
        power *= 1.10  # +10% للداعمين ذوي السمعة العالية

    # ─── تطبيق حدث تجمع التحالفات ───
    try:
        from modules.progression.global_events import get_event_effect
        support_event = get_event_effect("support_bonus")
        if support_event > 0:
            power *= (1 + support_event)
    except Exception:
        pass

    # ─── وقت سفر الدعم ───
    from modules.war.war_economy import schedule_delayed_support, get_support_travel_time
    travel_sec = get_support_travel_time()

    update_reputation(user_id, helped=1)

    # ─── فحص إنجازات الدعم ───
    try:
        from modules.progression.achievements import trigger_achievement_check
        trigger_achievement_check(user_id, "support_given")
    except Exception:
        pass

    # ─── تسجيل إحصائيات الدعم ───
    try:
        from modules.war.maintenance_service import record_alliance_support
        from database.db_queries.alliances_queries import get_alliance_by_user
        alliance = get_alliance_by_user(user_id)
        if alliance:
            record_alliance_support(alliance["id"], user_id, power_contributed=power)
    except Exception:
        pass

    schedule_delayed_support(
        req["battle_id"], supporter_country["id"], user_id,
        req["side"], power, travel_sec
    )
    return True, f"🚛 التعزيزات في الطريق! تصل خلال {travel_sec} ثانية بقوة {power:.0f}"


def _send_alliance_support_requests(battle_id):
    """يرسل طلبات دعم تلقائية كل دقيقة أثناء المعركة"""
    battle = get_battle_by_id(battle_id)
    if not battle:
        return
    for side, user_id in [
        ("attacker", battle["attacker_user_id"]),
        ("defender", battle["defender_user_id"]),
    ]:
        send_support_request_all(battle_id, user_id, side)


# ══════════════════════════════════════════
# 🃏 تطبيق البطاقات
# ══════════════════════════════════════════

def apply_card_to_battle(user_id, card_name, battle_id):
    from database.db_queries.advanced_war_queries import get_card_by_name, use_user_card
    card = get_card_by_name(card_name)
    if not card:
        return False, "❌ البطاقة غير موجودة!"
    if not use_user_card(user_id, card["id"]):
        return False, "❌ لا تملك هذه البطاقة!"

    battle = get_battle_by_id(battle_id)
    if not battle:
        return False, "❌ المعركة غير موجودة!"

    effect, val = card["effect_type"], card["effect_value"]
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─── بطاقات السفر (قبل المعركة) ───
    if effect == "delay_travel" and battle["status"] == "traveling":
        cursor.execute("UPDATE country_battles SET travel_end_time = travel_end_time + ? WHERE id = ?",
                       (int(val), battle_id))
        conn.commit()
        return True, f"⏳ تم تأخير الهجوم بـ {format_remaining_time(int(val))}!"

    if effect == "reduce_travel" and battle["status"] == "traveling":
        now = int(time.time())
        cursor.execute("SELECT travel_end_time FROM country_battles WHERE id = ?", (battle_id,))
        row = cursor.fetchone()
        if row:
            new_end = max(now + 10, row[0] - int(val))
            cursor.execute("UPDATE country_battles SET travel_end_time = ? WHERE id = ?",
                           (new_end, battle_id))
            conn.commit()
            print(f"[BATTLE_ACCEL_APPLIED] id={battle_id} new_travel_end_time={new_end}")
            # إذا انتهى وقت السفر فوراً → انتقل للقتال
            if new_end <= now:
                threading.Thread(target=_transition_to_battle, args=(battle_id,), daemon=True).start()
        return True, f"⚡ تم تقليل وقت السفر بـ {format_remaining_time(int(val))}!"

    # ─── بطاقات المعركة الحية ───
    if battle["status"] == "in_battle":
        from modules.war.live_battle_engine import (
            add_battle_effect, check_action_cooldown,
            set_action_cooldown, notify_card_used, _log_event,
            check_and_update_battle_state,
        )

        # تحديد الجانب
        country = get_country_by_owner(user_id)
        if not country:
            return False, "❌ لا تملك دولة!"
        country = dict(country)
        cid = country["id"]
        side = "attacker" if battle["attacker_country_id"] == cid else "defender"

        # كولداون البطاقة
        can_use, remaining = check_action_cooldown(battle_id, user_id, card_name, 60)
        if not can_use:
            return False, f"⏳ انتظر {remaining} ثانية قبل استخدام هذه البطاقة مجدداً."

        # ─── بطاقة تسريع المعركة (reduce_battle) ───
        if effect == "reduce_battle":
            now = int(time.time())
            cursor.execute("SELECT battle_end_time FROM country_battles WHERE id = ?", (battle_id,))
            row = cursor.fetchone()
            if row and row[0]:
                new_end = max(now + 5, row[0] - int(val))
                cursor.execute("UPDATE country_battles SET battle_end_time = ? WHERE id = ?",
                               (new_end, battle_id))
                conn.commit()
                print(f"[BATTLE_ACCEL_APPLIED] id={battle_id} new_battle_end_time={new_end}")
                set_action_cooldown(battle_id, user_id, card_name)
                check_and_update_battle_state(battle_id)
            return True, f"⚡ تم تقليل وقت المعركة بـ {format_remaining_time(int(val))}!"

        EFFECT_MAP = {
            "attack_boost":   ("attack_boost",  val,  20),
            "defense_boost":  ("defense_boost", val,  20),
            "hp_boost":       ("hp_boost",       val,  20),
            "sabotage":       ("sabotage",       val,  30),
            "spy_level_boost":("attack_boost",   0.10, 30),
        }

        if effect in EFFECT_MAP:
            etype, evalue, duration = EFFECT_MAP[effect]
            add_battle_effect(battle_id, cid, user_id, etype, evalue, duration, source="card")
            set_action_cooldown(battle_id, user_id, card_name)
            _log_event(battle_id, "card",
                       f"بطاقة {card['name_ar']} من {side}",
                       0, 0)
            notify_card_used(battle, user_id, card["name_ar"], side)
            return True, f"✅ تم تفعيل {card['name_ar']}! تأثير لـ {duration} ثانية."

        if effect == "reveal_intel":
            real_power = get_country_power(
                battle["defender_country_id"] if side == "attacker" else battle["attacker_country_id"]
            )
            set_action_cooldown(battle_id, user_id, card_name)
            return True, f"📡 قوة العدو الحقيقية: {real_power:.0f}"

    # ─── بطاقة كشف المخفي ───
    if effect == "reveal_hidden":
        country = get_country_by_owner(user_id)
        if country:
            cid = dict(country)["id"]
            from database.db_queries.countries_queries import get_all_countries
            from database.db_queries.advanced_war_queries import get_visibility
            hidden = [dict(c) for c in get_all_countries()
                      if c["id"] != cid and get_visibility(c["id"]) and
                      get_visibility(c["id"])["visibility_mode"] == "hidden"]
            if hidden:
                import random as _r
                target = _r.choice(hidden)
                add_discovered_country(cid, target["id"])
                return True, f"🔍 اكتشفت دولة مخفية: {target['name']}!"
        return True, "🔍 لا توجد دول مخفية حالياً."

    return True, f"✅ تم تفعيل البطاقة: {card['name_ar']}"


# ══════════════════════════════════════════
# 🔔 الإشعارات
# ══════════════════════════════════════════

def _notify_battle_started(battle):
    from core.bot import bot
    from utils.pagination import btn, send_ui
    defender_uid = battle["defender_user_id"]
    battle_id = battle["id"]
    _safe_send(bot, battle["attacker_user_id"],
               "🔴 <b>بدأت المعركة!</b>\n⚔️ جيشك وصل وبدأ القتال!\n⏱️ المعركة تستمر 5 دقائق.")
    try:
        send_ui(defender_uid,
                text="🚨 <b>أنت تُهاجَم الآن!</b>\n⚔️ العدو وصل!\n⏱️ لديك 5 دقائق — اطلب الدعم!",
                buttons=[btn("📣 طلب دعم من التحالف", "war_request_support_now",
                             data={"battle_id": battle_id, "side": "defender"},
                             owner=(defender_uid, None), color="su")],
                layout=[1], owner_id=defender_uid)
    except Exception:
        pass


def _notify_fake_attack_end(battle):
    from core.bot import bot
    _safe_send(bot, battle["defender_user_id"], "😮 <b>تنبيه!</b>\nكان الهجوم وهمياً — لا ضرر حقيقي.")
    _safe_send(bot, battle["attacker_user_id"], "🎭 <b>الهجوم الوهمي نجح!</b>\nأربكت العدو.")


def _notify_battle_result(battle, winner_cid, loot, atk_power, def_power, result,
                          attack_penalty=1.0, reward_mult=1.0):
    from core.bot import bot
    from core.personality import war_win_msg, war_lose_msg, send_with_delay_async
    conn = get_db_conn()
    cursor = conn.cursor()

    def _cname(cid):
        if not cid:
            return "—"
        cursor.execute("SELECT name FROM countries WHERE id = ?", (cid,))
        r = cursor.fetchone()
        return r[0] if r else str(cid)

    attacker_won = winner_cid == battle["attacker_country_id"]
    atk_losses = sum(max(0, l.get("lost", 0)) for l in result.get("attacker_losses", []))
    def_losses = sum(max(0, l.get("lost", 0)) for l in result.get("defender_losses", []))

    # سطر عقوبة الهجوم (إن وجدت)
    penalty_line = ""
    if attack_penalty < 1.0:
        pct = int((1 - attack_penalty) * 100)
        penalty_line = f"\n⚖️ فرق المستوى أثر على قوة الهجوم (-{pct}%)"

    # سطر مضاعف المكافأة (إن كان مختلفاً عن 1.0)
    reward_line = ""
    if reward_mult != 1.0:
        reward_line = f"\n🏆 مكافأة معدلة حسب مستوى الخصم (×{reward_mult})"

    report = (
        f"⚔️ <b>نتيجة المعركة #{battle['id']}</b>\n"
        f"{get_lines()}\n"
        f"{'🏆 المهاجم انتصر!' if attacker_won else ('🛡 المدافع صمد!' if winner_cid else '🤝 تعادل!')}\n"
        f"🏳️ الفائز: <b>{_cname(winner_cid)}</b>\n\n"
        f"📊 القوى:\n"
        f"  ⚔️ المهاجم: {max(0, atk_power):.0f}\n"
        f"  🛡 المدافع: {max(0, def_power):.0f}\n\n"
        f"💀 الخسائر:\n"
        f"  المهاجم: {atk_losses} وحدة\n"
        f"  المدافع: {def_losses} وحدة\n\n"
        f"💰 الغنائم: {max(0, loot):.0f} {CURRENCY_ARABIC_NAME}"
        f"{penalty_line}{reward_line}"
    )

    atk_uid = battle["attacker_user_id"]
    def_uid = battle["defender_user_id"]
    atk_personality = war_win_msg() if attacker_won else war_lose_msg()
    def_personality = war_lose_msg() if attacker_won else war_win_msg()

    send_with_delay_async(atk_uid, f"{atk_personality}\n\n{report}", delay=0.5)
    send_with_delay_async(def_uid, f"{def_personality}\n\n{report}", delay=0.5)


def _notify_support_request(user_id, battle_id, request_id, side, country_id):
    from core.bot import bot
    from utils.pagination import btn, send_ui
    side_ar = "المهاجم" if side == "attacker" else "المدافع"
    try:
        send_ui(user_id,
                text=f"⚔️ <b>حليفك في معركة!</b>\n\nهل تريد دعمه كـ {side_ar}؟",
                buttons=[
                    btn("🔥 أساعد", "support_accept",
                        data={"req_id": request_id, "battle_id": battle_id},
                        owner=(user_id, None), color="su"),
                    btn("❌ لا", "support_reject",
                        data={"req_id": request_id},
                        owner=(user_id, None), color="d"),
                ], layout=[2], owner_id=user_id)
    except Exception:
        pass


def _safe_send(bot, user_id, text):
    try:
        bot.send_message(user_id, text, parse_mode="HTML")
    except Exception:
        pass


# ══════════════════════════════════════════
# 🔧 مساعدات داخلية
# ══════════════════════════════════════════

def _apply_country_losses(country_id, losses):
    from database.db_queries.war_queries import apply_troop_losses, apply_equipment_losses
    cities = get_all_cities_of_country_by_country_id(country_id)
    if not cities:
        return
    for city in cities:
        cid = city["id"] if isinstance(city, dict) else city[0]
        apply_troop_losses(cid, losses)
        apply_equipment_losses(cid, losses)


def _calculate_loot(winner_cid, attacker_cid, defender_cid):
    loser_cid = defender_cid if winner_cid == attacker_cid else attacker_cid
    cities = get_all_cities_of_country_by_country_id(loser_cid)
    return max(0, len(cities) * 200) if cities else 0


def _get_capital_city_id(country_id):
    cities = get_all_cities_of_country_by_country_id(country_id)
    if not cities:
        return None
    city = cities[0]
    return city["id"] if isinstance(city, dict) else city[0]


def _update_supporter_reputation(battle_id):
    pending = get_pending_support_requests(battle_id)
    for req in pending:
        update_reputation(req["target_user_id"], ignored=1)
        update_support_request_status(req["id"], "ignored")
