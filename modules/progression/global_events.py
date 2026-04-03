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
    {
        "name":        "war_bonus",
        "name_ar":     "موجة الحرب",
        "emoji":       "⚔️",
        "event_type":  "war",
        "effect_key":  "atk_bonus",
        "effect_value": 0.15,
        "duration_hours": 6,
        "description_ar": "جميع الهجمات أقوى بـ 15% لمدة 6 ساعات!",
    },
    {
        "name":        "spy_bonus",
        "name_ar":     "موسم الجواسيس",
        "emoji":       "🕵️",
        "event_type":  "spy",
        "effect_key":  "spy_success_bonus",
        "effect_value": 0.20,
        "duration_hours": 8,
        "description_ar": "احتمال نجاح التجسس أعلى بـ 20% لمدة 8 ساعات!",
    },
    {
        "name":        "economic_boom",
        "name_ar":     "ازدهار اقتصادي",
        "emoji":       "💰",
        "event_type":  "economy",
        "effect_key":  "income_bonus",
        "effect_value": 0.25,
        "duration_hours": 12,
        "description_ar": "دخل جميع المدن أعلى بـ 25% لمدة 12 ساعة!",
    },
    {
        "name":        "natural_disaster",
        "name_ar":     "كارثة طبيعية",
        "emoji":       "🌪️",
        "event_type":  "disaster",
        "effect_key":  "maintenance_increase",
        "effect_value": 0.50,
        "duration_hours": 4,
        "description_ar": "تكاليف الصيانة أعلى بـ 50% لمدة 4 ساعات!",
    },
    {
        "name":        "alliance_rally",
        "name_ar":     "تجمع التحالفات",
        "emoji":       "🏰",
        "event_type":  "alliance",
        "effect_key":  "support_bonus",
        "effect_value": 0.30,
        "duration_hours": 6,
        "description_ar": "قوة الدعم في التحالفات أعلى بـ 30% لمدة 6 ساعات!",
    },
    {
        "name":        "defense_boost",
        "name_ar":     "تحصينات عامة",
        "emoji":       "🛡",
        "event_type":  "war",
        "effect_key":  "def_bonus",
        "effect_value": 0.20,
        "duration_hours": 8,
        "description_ar": "جميع المدافعين أقوى بـ 20% لمدة 8 ساعات!",
    },
    {
        "name":        "loot_festival",
        "name_ar":     "مهرجان الغنائم",
        "emoji":       "💎",
        "event_type":  "economy",
        "effect_key":  "loot_bonus",
        "effect_value": 0.40,
        "duration_hours": 6,
        "description_ar": "الغنائم أعلى بـ 40% لمدة 6 ساعات!",
    },
]


# ══════════════════════════════════════════
# 🎲 تشغيل حدث عشوائي
# ══════════════════════════════════════════

def trigger_random_event() -> dict | None:
    """يُطلق حدثاً عالمياً عشوائياً"""
    # فحص إذا كان هناك حدث نشط بالفعل
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
        from core.bot import bot
        from core.admin import get_const
        group_id = int(get_const("dev_group_id", "-1"))
        if group_id == -1:
            return
        remaining = event["duration_hours"]
        msg = (
            f"{event['emoji']} <b>حدث عالمي جديد!</b>\n\n"
            f"<b>{event['name_ar']}</b>\n"
            f"📝 {event['description_ar']}\n"
            f"⏱️ المدة: {remaining} ساعة"
        )
        bot.send_message(group_id, msg, parse_mode="HTML")
    except Exception:
        pass


def _notify_event_end(event: dict):
    try:
        from core.bot import bot
        from core.admin import get_const
        group_id = int(get_const("dev_group_id", "-1"))
        if group_id == -1:
            return
        msg = f"{event['emoji']} <b>انتهى الحدث: {event['name_ar']}</b>"
        bot.send_message(group_id, msg, parse_mode="HTML")
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
    """يرجع قيمة تأثير الحدث النشط (0.0 إذا لم يكن هناك حدث)"""
    event = get_active_event()
    if not event or event["effect_key"] != effect_key:
        return 0.0
    return float(event["effect_value"])


def get_event_display() -> str:
    """نص عرض الحدث النشط"""
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
                # 30% فرصة لحدث جديد كل ساعة
                if random.random() < 0.30:
                    trigger_random_event()
            except Exception as e:
                print(f"[GlobalEvents] {e}")

    threading.Thread(target=_loop, daemon=True).start()
