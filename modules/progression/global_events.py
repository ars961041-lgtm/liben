"""
نظام الأحداث العالمية — أحداث عشوائية تؤثر على جميع اللاعبين
"""
import random
import time
import threading

from database.connection import get_db_conn


def _c(name, default):
    try:
        from core.admin import get_const_int, get_const_float
        if isinstance(default, float):
            return get_const_float(name, default)
        return get_const_int(name, int(default))
    except Exception:
        return default


# ══════════════════════════════════════════
# 📋 تعريف الأحداث المتاحة
# ══════════════════════════════════════════

EVENT_POOL = [
    # ─── حرب ───
    {
        "name": "war_bonus", "name_ar": "موجة الحرب", "emoji": "⚔️",
        "event_type": "war", "effect_key": "atk_bonus", "effect_value": 0.15,
        "duration_hours": 6,
        "description_ar": "جميع الهجمات أقوى بـ 15% لمدة 6 ساعات!",
    },
    {
        "name": "defense_boost", "name_ar": "تحصينات عامة", "emoji": "🛡",
        "event_type": "war", "effect_key": "def_bonus", "effect_value": 0.20,
        "duration_hours": 8,
        "description_ar": "جميع المدافعين أقوى بـ 20% لمدة 8 ساعات!",
    },
    {
        "name": "blitz_war", "name_ar": "حرب الخاطفة", "emoji": "⚡",
        "event_type": "war", "effect_key": "sudden_bonus", "effect_value": 0.25,
        "duration_hours": 4,
        "description_ar": "قوة الهجوم المباغت أعلى بـ 25% لمدة 4 ساعات!",
    },
    {
        "name": "truce", "name_ar": "هدنة مؤقتة", "emoji": "🕊️",
        "event_type": "war", "effect_key": "recovery_bonus", "effect_value": 0.50,
        "duration_hours": 6,
        "description_ar": "سرعة التعافي بعد المعارك أعلى بـ 50% لمدة 6 ساعات!",
    },
    # ─── اقتصاد ───
    {
        "name": "economic_boom", "name_ar": "ازدهار اقتصادي", "emoji": "💰",
        "event_type": "economy", "effect_key": "income_bonus", "effect_value": 0.25,
        "duration_hours": 12,
        "description_ar": "دخل جميع المدن أعلى بـ 25% لمدة 12 ساعة!",
    },
    {
        "name": "loot_festival", "name_ar": "مهرجان الغنائم", "emoji": "💎",
        "event_type": "economy", "effect_key": "loot_bonus", "effect_value": 0.40,
        "duration_hours": 6,
        "description_ar": "الغنائم أعلى بـ 40% لمدة 6 ساعات!",
    },
    {
        "name": "salary_boost", "name_ar": "يوم الرواتب المضاعفة", "emoji": "💵",
        "event_type": "economy", "effect_key": "salary_bonus", "effect_value": 0.50,
        "duration_hours": 8,
        "description_ar": "الرواتب والمكافآت اليومية أعلى بـ 50% لمدة 8 ساعات!",
    },
    {
        "name": "market_crash", "name_ar": "انهيار السوق", "emoji": "📉",
        "event_type": "economy", "effect_key": "income_penalty", "effect_value": 0.30,
        "duration_hours": 4,
        "description_ar": "دخل المدن أقل بـ 30% لمدة 4 ساعات — احذر!",
    },
    {
        "name": "trade_festival", "name_ar": "مهرجان التجارة", "emoji": "🏪",
        "event_type": "economy", "effect_key": "transfer_fee_discount", "effect_value": 0.50,
        "duration_hours": 6,
        "description_ar": "رسوم التحويل البنكي أقل بـ 50% لمدة 6 ساعات!",
    },
    # ─── تجسس ───
    {
        "name": "spy_bonus", "name_ar": "موسم الجواسيس", "emoji": "🕵️",
        "event_type": "spy", "effect_key": "spy_success_bonus", "effect_value": 0.20,
        "duration_hours": 8,
        "description_ar": "احتمال نجاح التجسس أعلى بـ 20% لمدة 8 ساعات!",
    },
    {
        "name": "counter_intel", "name_ar": "مكافحة التجسس", "emoji": "🔒",
        "event_type": "spy", "effect_key": "counter_intel_bonus", "effect_value": 0.30,
        "duration_hours": 6,
        "description_ar": "احتمال كشف الجواسيس أعلى بـ 30% لمدة 6 ساعات!",
    },
    # ─── تحالفات ───
    {
        "name": "alliance_rally", "name_ar": "تجمع التحالفات", "emoji": "🏰",
        "event_type": "alliance", "effect_key": "support_bonus", "effect_value": 0.30,
        "duration_hours": 6,
        "description_ar": "قوة الدعم في التحالفات أعلى بـ 30% لمدة 6 ساعات!",
    },
    {
        "name": "alliance_xp", "name_ar": "أسبوع التحالفات", "emoji": "🤝",
        "event_type": "alliance", "effect_key": "alliance_xp_bonus", "effect_value": 0.40,
        "duration_hours": 12,
        "description_ar": "نقاط خبرة التحالفات أعلى بـ 40% لمدة 12 ساعة!",
    },
    # ─── كوارث ───
    {
        "name": "natural_disaster", "name_ar": "كارثة طبيعية", "emoji": "🌪️",
        "event_type": "disaster", "effect_key": "maintenance_increase", "effect_value": 0.50,
        "duration_hours": 4,
        "description_ar": "تكاليف الصيانة أعلى بـ 50% لمدة 4 ساعات!",
    },
    {
        "name": "plague", "name_ar": "وباء", "emoji": "🦠",
        "event_type": "disaster", "effect_key": "troop_recovery_penalty", "effect_value": 0.40,
        "duration_hours": 6,
        "description_ar": "سرعة شفاء الجنود أقل بـ 40% لمدة 6 ساعات!",
    },
    # ─── تقدم ───
    {
        "name": "golden_age", "name_ar": "العصر الذهبي", "emoji": "🌟",
        "event_type": "progress", "effect_key": "xp_bonus", "effect_value": 0.30,
        "duration_hours": 10,
        "description_ar": "نقاط الخبرة والنفوذ أعلى بـ 30% لمدة 10 ساعات!",
    },
    {
        "name": "recruitment_drive", "name_ar": "حملة التجنيد", "emoji": "🪖",
        "event_type": "progress", "effect_key": "troop_cost_discount", "effect_value": 0.20,
        "duration_hours": 8,
        "description_ar": "تكلفة شراء الجنود أقل بـ 20% لمدة 8 ساعات!",
    },
]


# ══════════════════════════════════════════
# 🎲 تشغيل حدث عشوائي
# ══════════════════════════════════════════

def trigger_random_event() -> dict | None:
    """يُطلق حدثاً عالمياً عشوائياً"""
    active = get_active_event()
    if active:
        return None
    event_def = random.choice(EVENT_POOL)
    return _start_event(event_def)


def _start_event(event_def: dict) -> dict:
    conn = get_db_conn()
    cursor = conn.cursor()
    now     = int(time.time())
    ends_at = now + event_def["duration_hours"] * 3600

    cursor.execute("""
        INSERT INTO global_events
        (name, name_ar, emoji, event_type, effect_key, effect_value,
         duration_hours, started_at, ends_at, status, description_ar)
        VALUES (?,?,?,?,?,?,?,?,?,'active',?)
    """, (
        event_def["name"], event_def["name_ar"], event_def["emoji"],
        event_def["event_type"], event_def["effect_key"], event_def["effect_value"],
        event_def["duration_hours"], now, ends_at, event_def["description_ar"]
    ))
    conn.commit()
    event_id = cursor.lastrowid

    event = {**event_def, "id": event_id, "started_at": now, "ends_at": ends_at}
    _notify_event_start(event)
    _schedule_event_end(event_id, event_def["duration_hours"] * 3600)
    return event


def _schedule_event_end(event_id: int, delay: float):
    def _end():
        time.sleep(delay)
        _end_event(event_id)
    threading.Thread(target=_end, daemon=True).start()


def _end_event(event_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE global_events SET status = 'ended' WHERE id = ?", (event_id,))
    conn.commit()
    cursor.execute("SELECT * FROM global_events WHERE id = ?", (event_id,))
    row = cursor.fetchone()
    if row:
        _notify_event_end(dict(row))


def _notify_event_start(event: dict):
    try:
        from core.dev_notifier import send_to_dev_group
        msg = (
            f"{event['emoji']} <b>حدث عالمي جديد!</b>\n\n"
            f"<b>{event['name_ar']}</b>\n"
            f"📝 {event['description_ar']}\n"
            f"⏱️ المدة: {event['duration_hours']} ساعة"
        )
        send_to_dev_group(msg)
    except Exception:
        pass


def _notify_event_end(event: dict):
    try:
        from core.dev_notifier import send_to_dev_group
        msg = f"{event['emoji']} <b>انتهى الحدث: {event['name_ar']}</b>"
        send_to_dev_group(msg)
    except Exception:
        pass


# ══════════════════════════════════════════
# 📊 جلب الأحداث
# ══════════════════════════════════════════

def get_active_event() -> dict | None:
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        SELECT * FROM global_events
        WHERE status = 'active' AND ends_at > ?
        ORDER BY started_at DESC LIMIT 1
    """, (now,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_event_effect(effect_key: str) -> float:
    """يرجع قيمة تأثير الحدث النشط (0.0 إذا لم يكن هناك حدث أو مفتاح مختلف)"""
    event = get_active_event()
    if not event or event["effect_key"] != effect_key:
        return 0.0
    return float(event["effect_value"])


def get_event_display() -> str:
    """نص عرض الحدث النشط — مختصر للرسائل"""
    event = get_active_event()
    if not event:
        return ""
    now       = int(time.time())
    remaining = max(0, event["ends_at"] - now)
    hours     = remaining // 3600
    mins      = (remaining % 3600) // 60
    return (
        f"\n\n{event['emoji']} <b>حدث نشط: {event['name_ar']}</b>\n"
        f"📝 {event['description_ar']}\n"
        f"⏱️ ينتهي خلال: {hours}س {mins}د"
    )


def get_events_page() -> str:
    """صفحة الأحداث الكاملة للاعبين — تعرض الحدث النشط + آخر 5 أحداث"""
    from utils.helpers import get_lines
    lines = get_lines()
    event = get_active_event()
    now   = int(time.time())

    if event:
        remaining = max(0, event["ends_at"] - now)
        h = remaining // 3600
        m = (remaining % 3600) // 60
        active_text = (
            f"{event['emoji']} <b>{event['name_ar']}</b>\n"
            f"📝 {event['description_ar']}\n"
            f"⏱️ ينتهي خلال: {h}س {m}د\n"
            f"🔑 التأثير: <code>{event['effect_key']}</code> +{float(event['effect_value'])*100:.0f}%"
        )
    else:
        active_text = "☮️ لا يوجد حدث نشط حالياً."

    recent = get_recent_events(5)
    history = ""
    for e in recent:
        if e.get("status") == "ended":
            history += f"  {e['emoji']} {e['name_ar']} — انتهى\n"

    text = (
        f"🌍 <b>الأحداث العالمية</b>\n{lines}\n\n"
        f"🔴 <b>الحدث النشط:</b>\n{active_text}\n\n"
    )
    if history:
        text += f"📜 <b>آخر الأحداث:</b>\n{history}"

    text += (
        f"\n{lines}\n"
        f"💡 <b>كيف تستفيد؟</b>\n"
        f"• ⚔️ موجة الحرب → هاجم الآن للاستفادة\n"
        f"• 💰 ازدهار اقتصادي → اجمع الدخل\n"
        f"• 💵 رواتب مضاعفة → اكتب <code>راتب</code>\n"
        f"• 💎 مهرجان الغنائم → انتصر في المعارك\n"
        f"• 🕵️ موسم الجواسيس → تجسس الآن"
    )
    return text


def get_recent_events(limit: int = 5) -> list:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM global_events ORDER BY started_at DESC LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# ⏱️ جدولة الأحداث الدورية
# ══════════════════════════════════════════

def schedule_event_checker():
    """يُشغَّل كل ساعة للتحقق من إطلاق حدث جديد"""
    interval = _c("event_check_interval", 3600)

    def _loop():
        while True:
            time.sleep(interval)
            try:
                if random.random() < 0.30:
                    trigger_random_event()
            except Exception as e:
                print(f"[GlobalEvents] {e}")

    threading.Thread(target=_loop, daemon=True).start()
