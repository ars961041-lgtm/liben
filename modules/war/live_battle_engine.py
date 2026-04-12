"""
محرك المعركة الحية — يدير دورة القتال كل 10 ثوانٍ
"""
import time
import threading
import random

from database.connection import get_db_conn
from database.db_queries.advanced_war_queries import (
    get_battle_by_id, finish_battle,
    get_total_support_power, add_supporter,
    update_reputation, get_pending_support_requests,
    update_support_request_status,
)
from database.db_queries.war_queries import update_city_resources
from database.db_queries.countries_queries import get_all_cities_of_country_by_country_id
from modules.war.power_calculator import get_country_power, aggregate_country_forces
from utils.helpers import get_lines

TICK_INTERVAL   = 10    # ثانية بين كل دورة
BATTLE_DURATION = 300   # 5 دقائق
ATK_LOSS_RATE   = 0.02  # نسبة خسارة المهاجم لكل دورة (من قوة المدافع)
DEF_LOSS_RATE   = 0.03  # نسبة خسارة المدافع لكل دورة (من قوة المهاجم)
SUPPORT_ATK_MOD = 0.60  # 60% من قوة الداعم للمهاجم
SUPPORT_DEF_MOD = 0.80  # 80% من قوة الداعم للمدافع
SHIFT_THRESHOLD = 0.20  # نسبة تغيير القوة لإرسال تنبيه

# ─── قاموس الخيوط النشطة ───
_active_battles: dict[int, threading.Thread] = {}
_lock = threading.Lock()


# ══════════════════════════════════════════
# 🚀 بدء محرك المعركة
# ══════════════════════════════════════════

def start_live_battle(battle_id: int):
    """يُطلق خيط المعركة الحية لمعركة معينة"""
    with _lock:
        if battle_id in _active_battles:
            return  # مشغول بالفعل
        t = threading.Thread(target=_battle_loop, args=(battle_id,), daemon=True)
        _active_battles[battle_id] = t
        t.start()


def stop_live_battle(battle_id: int):
    with _lock:
        _active_battles.pop(battle_id, None)


# ══════════════════════════════════════════
# 🔄 حلقة المعركة الرئيسية
# ══════════════════════════════════════════

def _battle_loop(battle_id: int):
    """تعمل كل TICK_INTERVAL ثانية طوال مدة المعركة"""
    try:
        battle = get_battle_by_id(battle_id)
        if not battle:
            return

        attacker_cid = battle["attacker_country_id"]
        defender_cid = battle["defender_country_id"]

        # تهيئة حالة المعركة
        atk_power = get_country_power(attacker_cid)
        def_power = get_country_power(defender_cid)

        if battle["battle_type"] == "sudden":
            atk_power *= 0.70

        # ─── تطبيق تعب الجيش ───
        from modules.war.war_balance import apply_fatigue_to_power, apply_defender_advantage
        atk_power = apply_fatigue_to_power(atk_power, attacker_cid)
        def_power = apply_fatigue_to_power(def_power, defender_cid)

        # ─── مزايا الدفاع (+15% + تضاريس) ───
        def_power = apply_defender_advantage(def_power)

        # ─── تطبيق ميزة النفوذ ───
        try:
            from modules.progression.influence import get_war_advantage
            atk_adv = get_war_advantage(attacker_cid)
            def_adv = get_war_advantage(defender_cid)
            atk_power = max(0, atk_power * (1 + atk_adv))
            def_power = max(0, def_power * (1 + def_adv))
        except Exception:
            pass

        # ─── تطبيق تأثيرات الأحداث العالمية ───
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

        _init_battle_state(battle_id, atk_power, def_power)
        _log_event(battle_id, "start",
                   f"بدأت المعركة | مهاجم: {atk_power:.0f} | مدافع: {def_power:.0f}",
                   atk_power, def_power)

        end_time = battle.get("battle_end_time") or (int(time.time()) + BATTLE_DURATION)
        prev_atk, prev_def = atk_power, def_power

        while True:
            time.sleep(TICK_INTERVAL)

            # إعادة جلب حالة المعركة
            battle = get_battle_by_id(battle_id)
            if not battle or battle["status"] != "in_battle":
                break

            now = int(time.time())
            if now >= end_time:
                break

            # جلب الحالة الحالية
            state = _get_battle_state(battle_id)
            if not state:
                break
            atk_power = state["atk_power"]
            def_power = state["def_power"]

            # ─── إضافة قوة الداعمين الجدد ───
            atk_support = get_total_support_power(battle_id, "attacker")
            def_support = get_total_support_power(battle_id, "defender")
            atk_power = max(0, atk_power + atk_support * SUPPORT_ATK_MOD)
            def_power = max(0, def_power + def_support * SUPPORT_DEF_MOD)

            # ─── تطبيق التأثيرات المؤقتة ───
            atk_bonus, def_bonus = _get_active_effects(battle_id, attacker_cid, defender_cid)
            atk_power = max(0, atk_power * (1 + atk_bonus))
            def_power = max(0, def_power * (1 + def_bonus))

            # ─── محاكاة الخسائر التدريجية ───
            atk_loss = def_power * ATK_LOSS_RATE * random.uniform(0.8, 1.2)
            def_loss = atk_power * DEF_LOSS_RATE * random.uniform(0.8, 1.2)

            atk_power = max(0, atk_power - atk_loss)
            def_power = max(0, def_power - def_loss)

            # ─── تحديث الحالة ───
            _update_battle_state(battle_id, atk_power, def_power)

            # ─── تنبيهات تغيير الكفة ───
            _check_power_shift(battle, atk_power, def_power, prev_atk, prev_def)
            prev_atk, prev_def = atk_power, def_power

            # ─── إذا انهارت قوة أحد الطرفين ───
            if atk_power <= 0 or def_power <= 0:
                _log_event(battle_id, "collapse",
                           f"انهيار القوة | مهاجم: {atk_power:.0f} | مدافع: {def_power:.0f}",
                           atk_power, def_power)
                break

        # ─── حل نهائي ───
        _finalize_battle(battle_id)

    except Exception as e:
        print(f"[LiveBattle] خطأ في معركة #{battle_id}: {e}")
    finally:
        stop_live_battle(battle_id)


# ══════════════════════════════════════════
# 🏁 الحل النهائي
# ══════════════════════════════════════════

def _finalize_battle(battle_id: int):
    battle = get_battle_by_id(battle_id)
    if not battle or battle["status"] != "in_battle":
        return

    state = _get_battle_state(battle_id)
    atk_final = max(0, state["atk_power"] if state else 0)
    def_final = max(0, state["def_power"] if state else 0)
    atk_initial = max(0, state["atk_initial"] if state else atk_final)
    def_initial = max(0, state["def_initial"] if state else def_final)

    attacker_cid = battle["attacker_country_id"]
    defender_cid = battle["defender_country_id"]

    winner_cid = attacker_cid if atk_final >= def_final else defender_cid
    if atk_final == 0 and def_final == 0:
        winner_cid = None
    loser_cid = defender_cid if winner_cid == attacker_cid else attacker_cid

    # ─── الخسائر الحقيقية مع حماية الحد الأقصى ───
    from modules.war.war_economy import (
        apply_proportional_losses, calculate_advanced_loot,
        set_country_recovery, build_loss_report_text, RECOVERY_MINUTES
    )
    from modules.war.war_balance import (
        clamp_loss_pct, add_fatigue, damage_defender_assets,
        record_battle_history, complete_ready_repairs
    )

    # حساب نسب الخسارة الخام
    raw_atk_loss = max(0.0, (atk_initial - atk_final) / max(1, atk_initial))
    raw_def_loss = max(0.0, (def_initial - def_final) / max(1, def_initial))

    # تطبيق الحد الأقصى 60% (مع حماية المدافع الضعيف)
    clamped_atk = clamp_loss_pct(raw_atk_loss, atk_initial, def_initial, is_defender=False)
    clamped_def = clamp_loss_pct(raw_def_loss, atk_initial, def_initial, is_defender=True)

    # تطبيق الخسائر الفعلية بالنسبة المقيّدة
    atk_report = apply_proportional_losses(attacker_cid,
                                           atk_initial,
                                           atk_initial * (1 - clamped_atk))
    def_report = apply_proportional_losses(defender_cid,
                                           def_initial,
                                           def_initial * (1 - clamped_def))

    # ─── تضرر مباني المدافع ───
    damaged_assets = damage_defender_assets(defender_cid)

    # ─── إضافة تعب الجيش لكلا الطرفين ───
    add_fatigue(attacker_cid)
    add_fatigue(defender_cid)

    # ─── إكمال الإصلاحات الجاهزة ───
    complete_ready_repairs(attacker_cid)
    complete_ready_repairs(defender_cid)

    # ─── معالجة الصيانة بعد المعركة ───
    try:
        from modules.war.maintenance_service import process_maintenance
        conn2 = get_db_conn()
        cur2  = conn2.cursor()
        cur2.execute("SELECT owner_id FROM countries WHERE id = ?", (attacker_cid,))
        r = cur2.fetchone()
        if r:
            process_maintenance(attacker_cid, r[0])
        cur2.execute("SELECT owner_id FROM countries WHERE id = ?", (defender_cid,))
        r = cur2.fetchone()
        if r:
            process_maintenance(defender_cid, r[0])
    except Exception:
        pass

    # ─── الغنائم المتقدمة ───
    loot = calculate_advanced_loot(
        winner_cid, loser_cid,
        atk_initial, def_initial,
        atk_final, def_final,
        no_retreat=True
    ) if winner_cid else 0

    if loot > 0:
        cap = _get_capital_city_id(winner_cid)
        if cap:
            update_city_resources(cap, loot)

    finish_battle(battle_id, winner_cid, loot, atk_final, def_final)

    _log_event(battle_id, "end",
               f"انتهت | فائز: {winner_cid} | غنائم: {loot:.0f}",
               atk_final, def_final)

    # ─── فترة التعافي لكلا الطرفين ───
    set_country_recovery(attacker_cid, RECOVERY_MINUTES)
    set_country_recovery(defender_cid, RECOVERY_MINUTES)

    # ─── تسجيل في سجل الحروب ───
    duration = int(time.time()) - (battle.get("battle_end_time", int(time.time())) - BATTLE_DURATION)
    record_battle_history(
        battle_id, attacker_cid, defender_cid, winner_cid,
        clamped_atk * 100, clamped_def * 100,
        loot, battle.get("battle_type", "normal"), max(0, duration)
    )

    # ─── تحديث النفوذ ───
    try:
        from modules.progression.influence import on_battle_won, on_defense_won
        if winner_cid == attacker_cid:
            on_battle_won(attacker_cid, defender_cid)
        else:
            on_battle_won(defender_cid, attacker_cid)
            on_defense_won(defender_cid)
    except Exception:
        pass

    # ─── فحص الإنجازات ───
    try:
        from modules.progression.achievements import trigger_achievement_check
        trigger_achievement_check(battle["attacker_user_id"],
                                  "battle_won" if winner_cid == attacker_cid else "battle_defended")
        trigger_achievement_check(battle["defender_user_id"],
                                  "battle_defended" if winner_cid == defender_cid else "battle_won")
    except Exception:
        pass

    # ─── XP awards after battle ───
    try:
        from database.db_queries.countries_queries import get_all_cities_of_country_by_country_id
        from modules.city.city_stats import award_battle_xp
        atk_loss = atk_report.get("loss_pct", 0)
        def_loss = def_report.get("loss_pct", 0)
        for city in get_all_cities_of_country_by_country_id(attacker_cid):
            cid = city["id"] if isinstance(city, dict) else city[0]
            award_battle_xp(cid, won=(winner_cid == attacker_cid), loss_pct=atk_loss)
        for city in get_all_cities_of_country_by_country_id(defender_cid):
            cid = city["id"] if isinstance(city, dict) else city[0]
            award_battle_xp(cid, won=(winner_cid == defender_cid), loss_pct=def_loss)
    except Exception:
        pass

    # ─── التقرير النهائي ───
    from database.db_queries.advanced_war_queries import get_supporters
    supporters = get_supporters(battle_id)
    _send_final_report(battle, winner_cid, loot, atk_final, def_final,
                       atk_report, def_report, supporters, battle_id,
                       damaged_assets)

    _update_reputations(battle, winner_cid, battle_id)


# ══════════════════════════════════════════
# 📊 إدارة حالة المعركة
# ══════════════════════════════════════════

def _init_battle_state(battle_id, atk_power, def_power):
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        INSERT OR REPLACE INTO battle_state
        (battle_id, atk_power, def_power, atk_initial, def_initial, last_tick, tick_count)
        VALUES (?, ?, ?, ?, ?, ?, 0)
    """, (battle_id, atk_power, def_power, atk_power, def_power, now))
    conn.commit()


def _get_battle_state(battle_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM battle_state WHERE battle_id = ?", (battle_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def _update_battle_state(battle_id, atk_power, def_power):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE battle_state
        SET atk_power = ?, def_power = ?, last_tick = ?, tick_count = tick_count + 1
        WHERE battle_id = ?
    """, (max(0, atk_power), max(0, def_power), int(time.time()), battle_id))
    conn.commit()


def get_live_battle_state(battle_id):
    """واجهة عامة لجلب حالة المعركة الحية"""
    return _get_battle_state(battle_id)


# ══════════════════════════════════════════
# ✨ التأثيرات المؤقتة
# ══════════════════════════════════════════

def add_battle_effect(battle_id, country_id, user_id, effect_type, value, duration, source="card"):
    """يضيف تأثيراً مؤقتاً للمعركة"""
    conn = get_db_conn()
    cursor = conn.cursor()
    expires = int(time.time()) + duration
    cursor.execute("""
        INSERT INTO battle_effects
        (battle_id, country_id, user_id, effect_type, value, expires_at, source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (battle_id, country_id, user_id, effect_type, value, expires, source))
    conn.commit()
    return cursor.lastrowid


def _get_active_effects(battle_id, attacker_cid, defender_cid):
    """يرجع (atk_bonus, def_bonus) من التأثيرات النشطة"""
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        SELECT country_id, effect_type, value FROM battle_effects
        WHERE battle_id = ? AND expires_at > ?
    """, (battle_id, now))
    rows = cursor.fetchall()

    atk_bonus = 0.0
    def_bonus = 0.0
    for row in rows:
        cid, etype, val = row[0], row[1], row[2]
        if etype in ("attack_boost", "hp_boost"):
            if cid == attacker_cid:
                atk_bonus += val
            else:
                def_bonus += val
        elif etype == "defense_boost":
            if cid == defender_cid:
                def_bonus += val
            else:
                atk_bonus += val
        elif etype == "sabotage":
            if cid == attacker_cid:
                def_bonus -= val   # تخريب يقلل قوة العدو
            else:
                atk_bonus -= val

    return atk_bonus, def_bonus


def get_active_effects_for_display(battle_id):
    """للعرض في الواجهة"""
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        SELECT be.*, c.name as country_name
        FROM battle_effects be
        LEFT JOIN countries c ON be.country_id = c.id
        WHERE be.battle_id = ? AND be.expires_at > ?
        ORDER BY be.created_at DESC
    """, (battle_id, now))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# ⏱️ كولداون الأفعال
# ══════════════════════════════════════════

def check_action_cooldown(battle_id, user_id, action, cooldown_sec):
    """يرجع (can_use, remaining_seconds)"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT last_used FROM battle_action_cooldowns
        WHERE battle_id = ? AND user_id = ? AND action = ?
    """, (battle_id, user_id, action))
    row = cursor.fetchone()
    if not row:
        return True, 0
    elapsed = int(time.time()) - row[0]
    if elapsed >= cooldown_sec:
        return True, 0
    return False, cooldown_sec - elapsed


def set_action_cooldown(battle_id, user_id, action):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO battle_action_cooldowns (battle_id, user_id, action, last_used)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(battle_id, user_id, action) DO UPDATE SET last_used = ?
    """, (battle_id, user_id, action, int(time.time()), int(time.time())))
    conn.commit()


# ══════════════════════════════════════════
# 📝 سجل الأحداث
# ══════════════════════════════════════════

def _log_event(battle_id, event_type, description, atk_snap=0, def_snap=0):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO battle_events
        (battle_id, event_type, description, atk_power_snapshot, def_power_snapshot)
        VALUES (?, ?, ?, ?, ?)
    """, (battle_id, event_type, description, max(0, atk_snap), max(0, def_snap)))
    conn.commit()


def get_battle_events(battle_id, limit=20):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM battle_events WHERE battle_id = ?
        ORDER BY created_at DESC LIMIT ?
    """, (battle_id, limit))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# 🔔 الإشعارات
# ══════════════════════════════════════════

def _check_power_shift(battle, atk_power, def_power, prev_atk, prev_def):
    """يرسل تنبيهاً إذا تغيرت الكفة بشكل ملحوظ"""
    if prev_atk <= 0 or prev_def <= 0:
        return

    atk_change = abs(atk_power - prev_atk) / max(1, prev_atk)
    def_change = abs(def_power - prev_def) / max(1, prev_def)

    if atk_change < SHIFT_THRESHOLD and def_change < SHIFT_THRESHOLD:
        return

    from core.bot import bot

    if atk_power > def_power * 1.3:
        msg = "⚠️ كفة المعركة تميل لصالح <b>المهاجم</b>!"
    elif def_power > atk_power * 1.3:
        msg = "⚠️ كفة المعركة تميل لصالح <b>المدافع</b>!"
    else:
        return

    _safe_send(bot, battle["attacker_user_id"], msg)
    _safe_send(bot, battle["defender_user_id"], msg)


def notify_support_arrived(battle, supporter_name, side, power):
    """يُرسل إشعار وصول التعزيزات"""
    from core.bot import bot
    side_ar = "المهاجم" if side == "attacker" else "المدافع"
    msg = f"🚀 <b>وصلت تعزيزات من {supporter_name}!</b>\nانضمت لجانب {side_ar} بقوة {power:.0f}"
    _safe_send(bot, battle["attacker_user_id"], msg)
    _safe_send(bot, battle["defender_user_id"], msg)


def notify_card_used(battle, user_id, card_name_ar, side):
    """يُرسل إشعار استخدام بطاقة"""
    from core.bot import bot
    side_ar = "المهاجم" if side == "attacker" else "المدافع"
    msg = f"🔥 <b>تم استخدام بطاقة {card_name_ar}!</b>\nمن قِبل {side_ar}"
    _safe_send(bot, battle["attacker_user_id"], msg)
    _safe_send(bot, battle["defender_user_id"], msg)


def _send_final_report(battle, winner_cid, loot, atk_power, def_power,
                       atk_report, def_report, supporters, battle_id,
                       damaged_assets=None):
    from core.bot import bot
    conn = get_db_conn()
    cursor = conn.cursor()

    def _cname(cid):
        if not cid:
            return "—"
        cursor.execute("SELECT name FROM countries WHERE id = ?", (cid,))
        r = cursor.fetchone()
        return r[0] if r else str(cid)

    attacker_won = winner_cid == battle["attacker_country_id"]

    # شريط القوة النهائي
    total = max(1, atk_power + def_power)
    atk_pct = int((atk_power / total) * 10)
    bar = "🔴" * atk_pct + "🔵" * (10 - atk_pct)

    from modules.war.war_economy import build_loss_report_text
    loss_detail = build_loss_report_text(atk_report, def_report, loot, supporters)

    # أبرز الأحداث
    events = get_battle_events(battle_id, limit=5)
    events_text = ""
    if events:
        events_text = "\n\n📋 <b>أبرز الأحداث:</b>\n"
        for ev in reversed(events):
            if ev["event_type"] not in ("start", "end"):
                events_text += f"  • {ev['description']}\n"

    header = (
        f"⚔️ <b>تقرير المعركة #{battle_id}</b>\n"
        f"{get_lines()}\n"
        f"{'🏆 المهاجم انتصر!' if attacker_won else ('🛡 المدافع صمد!' if winner_cid else '🤝 تعادل!')}\n"
        f"🏳️ الفائز: <b>{_cname(winner_cid)}</b>\n\n"
        f"📊 <b>القوى النهائية:</b>\n"
        f"  ⚔️ {atk_power:.0f} {bar} {def_power:.0f} 🛡"
    )

    report = header + loss_detail + events_text

    # رسائل مخصصة لكل طرف
    atk_extra = ""
    def_extra = ""
    if atk_report["injured"] > 0:
        atk_extra = f"\n\n🏥 تم نقل {atk_report['injured']} جندي إلى المستشفى"
    if atk_report["eq_damaged"] > 0:
        atk_extra += f"\n🔧 لديك {atk_report['eq_damaged']} معدة تحتاج إصلاح"
    if def_report["injured"] > 0:
        def_extra = f"\n\n🏥 تم نقل {def_report['injured']} جندي إلى المستشفى"
    if def_report["eq_damaged"] > 0:
        def_extra += f"\n🔧 لديك {def_report['eq_damaged']} معدة تحتاج إصلاح"

    # إشعار تضرر المباني للمدافع
    if damaged_assets:
        def_extra += f"\n🏚️ تضررت {len(damaged_assets)} مبانٍ في مدنك!"

    _safe_send(bot, battle["attacker_user_id"], report + atk_extra)
    _safe_send(bot, battle["defender_user_id"], report + def_extra)


def _safe_send(bot, user_id, text):
    try:
        bot.send_message(user_id, text, parse_mode="HTML")
    except Exception:
        pass


# ══════════════════════════════════════════
# 🔧 مساعدات
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


def _calculate_loot(loser_cid):
    cities = get_all_cities_of_country_by_country_id(loser_cid)
    return max(0, len(cities) * 200) if cities else 0


def _get_capital_city_id(country_id):
    cities = get_all_cities_of_country_by_country_id(country_id)
    if not cities:
        return None
    city = cities[0]
    return city["id"] if isinstance(city, dict) else city[0]


def _update_reputations(battle, winner_cid, battle_id):
    attacker_cid = battle["attacker_country_id"]
    winner_uid = battle["attacker_user_id"] if winner_cid == attacker_cid else battle["defender_user_id"]
    loser_uid  = battle["defender_user_id"] if winner_cid == attacker_cid else battle["attacker_user_id"]
    update_reputation(winner_uid, helped=1)
    update_reputation(loser_uid)

    pending = get_pending_support_requests(battle_id)
    for req in pending:
        update_reputation(req["target_user_id"], ignored=1)
        update_support_request_status(req["id"], "ignored")
