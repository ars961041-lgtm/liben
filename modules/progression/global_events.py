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
        "effect_label": "قوة الهجوم +15% لجميع اللاعبين",
    },
    {
        "name": "defense_boost", "name_ar": "تحصينات عامة", "emoji": "🛡",
        "event_type": "war", "effect_key": "def_bonus", "effect_value": 0.20,
        "duration_hours": 8,
        "description_ar": "جميع المدافعين أقوى بـ 20% لمدة 8 ساعات!",
        "effect_label": "قوة الدفاع +20% لجميع اللاعبين",
    },
    {
        "name": "blitz_war", "name_ar": "حرب الخاطفة", "emoji": "⚡",
        "event_type": "war", "effect_key": "sudden_bonus", "effect_value": 0.25,
        "duration_hours": 4,
        "description_ar": "قوة الهجوم المباغت أعلى بـ 25% لمدة 4 ساعات!",
        "effect_label": "قوة الهجوم المباغت +25%",
    },
    {
        "name": "truce", "name_ar": "هدنة مؤقتة", "emoji": "🕊️",
        "event_type": "war", "effect_key": "recovery_bonus", "effect_value": 0.50,
        "duration_hours": 6,
        "description_ar": "سرعة التعافي بعد المعارك أعلى بـ 50% لمدة 6 ساعات!",
        "effect_label": "سرعة التعافي من المعارك +50%",
    },
    # ─── اقتصاد ───
    {
        "name": "economic_boom", "name_ar": "ازدهار اقتصادي", "emoji": "💰",
        "event_type": "economy", "effect_key": "income_bonus", "effect_value": 0.25,
        "duration_hours": 12,
        "description_ar": "دخل جميع المدن أعلى بـ 25% لمدة 12 ساعة!",
        "effect_label": "دخل المدن +25%",
    },
    {
        "name": "loot_festival", "name_ar": "مهرجان الغنائم", "emoji": "💎",
        "event_type": "economy", "effect_key": "loot_bonus", "effect_value": 0.40,
        "duration_hours": 6,
        "description_ar": "الغنائم أعلى بـ 40% لمدة 6 ساعات!",
        "effect_label": "غنائم الانتصار في المعارك +40%",
    },
    {
        "name": "salary_boost", "name_ar": "يوم الرواتب المضاعفة", "emoji": "💵",
        "event_type": "economy", "effect_key": "salary_bonus", "effect_value": 0.50,
        "duration_hours": 8,
        "description_ar": "الرواتب والمكافآت اليومية أعلى بـ 50% لمدة 8 ساعات!",
        "effect_label": "قيمة الراتب اليومي +50%",
    },
    {
        "name": "market_crash", "name_ar": "انهيار السوق", "emoji": "📉",
        "event_type": "economy", "effect_key": "income_penalty", "effect_value": 0.30,
        "duration_hours": 4,
        "description_ar": "دخل المدن أقل بـ 30% لمدة 4 ساعات — احذر!",
        "effect_label": "دخل المدن ينخفض بنسبة 30% — تحذير!",
    },
    {
        "name": "trade_festival", "name_ar": "مهرجان التجارة", "emoji": "🏪",
        "event_type": "economy", "effect_key": "transfer_fee_discount", "effect_value": 0.50,
        "duration_hours": 6,
        "description_ar": "رسوم التحويل البنكي أقل بـ 50% لمدة 6 ساعات!",
        "effect_label": "رسوم التحويل البنكي -50%",
    },
    # ─── تجسس ───
    {
        "name": "spy_bonus", "name_ar": "موسم الجواسيس", "emoji": "🕵️",
        "event_type": "spy", "effect_key": "spy_success_bonus", "effect_value": 0.20,
        "duration_hours": 8,
        "description_ar": "احتمال نجاح التجسس أعلى بـ 20% لمدة 8 ساعات!",
        "effect_label": "نسبة نجاح عمليات التجسس +20%",
    },
    {
        "name": "counter_intel", "name_ar": "مكافحة التجسس", "emoji": "🔒",
        "event_type": "spy", "effect_key": "counter_intel_bonus", "effect_value": 0.30,
        "duration_hours": 6,
        "description_ar": "احتمال كشف الجواسيس أعلى بـ 30% لمدة 6 ساعات!",
        "effect_label": "نسبة كشف الجواسيس المتسللين +30%",
    },
    # ─── تحالفات ───
    {
        "name": "alliance_rally", "name_ar": "تجمع التحالفات", "emoji": "🏰",
        "event_type": "alliance", "effect_key": "support_bonus", "effect_value": 0.30,
        "duration_hours": 6,
        "description_ar": "قوة الدعم في التحالفات أعلى بـ 30% لمدة 6 ساعات!",
        "effect_label": "قوة الدعم العسكري بين التحالفات +30%",
    },
    {
        "name": "alliance_xp", "name_ar": "أسبوع التحالفات", "emoji": "🤝",
        "event_type": "alliance", "effect_key": "alliance_xp_bonus", "effect_value": 0.40,
        "duration_hours": 12,
        "description_ar": "نقاط خبرة التحالفات أعلى بـ 40% لمدة 12 ساعة!",
        "effect_label": "نقاط خبرة التحالفات +40%",
    },
    # ─── كوارث ───
    {
        "name": "natural_disaster", "name_ar": "كارثة طبيعية", "emoji": "🌪️",
        "event_type": "disaster", "effect_key": "maintenance_increase", "effect_value": 0.50,
        "duration_hours": 4,
        "description_ar": "تكاليف الصيانة أعلى بـ 50% لمدة 4 ساعات!",
        "effect_label": "تكاليف صيانة المباني ترتفع بنسبة 50% — تحذير!",
    },
    {
        "name": "plague", "name_ar": "وباء 🦠", "emoji": "🦠",
        "event_type": "disaster", "effect_key": "troop_recovery_penalty", "effect_value": 0.40,
        "duration_hours": 6,
        "description_ar": "سرعة شفاء الجنود أقل بـ 40%، ورضا السكان -5 لمدة 6 ساعات!",
        "effect_label": "سرعة شفاء الجنود تنخفض 40% ورضا السكان يتراجع",
    },
    {
        "name": "epidemic", "name_ar": "وباء عالمي", "emoji": "😷",
        "event_type": "disaster", "effect_key": "satisfaction_penalty", "effect_value": 0.10,
        "duration_hours": 8,
        "description_ar": "رضا السكان ينخفض في جميع المدن لمدة 8 ساعات!",
        "effect_label": "رضا السكان ينخفض في جميع المدن",
    },
    {
        "name": "global_recession", "name_ar": "ركود اقتصادي عالمي", "emoji": "📉",
        "event_type": "disaster", "effect_key": "income_penalty", "effect_value": 0.20,
        "duration_hours": 12,
        "description_ar": "دخل جميع المدن أقل بـ 20% لمدة 12 ساعة!",
        "effect_label": "دخل المدن ينخفض بنسبة 20% — تحذير!",
    },
    {
        "name": "war_tensions", "name_ar": "توترات حربية", "emoji": "⚔️",
        "event_type": "war", "effect_key": "war_tension_bonus", "effect_value": 0.15,
        "duration_hours": 8,
        "description_ar": "تكاليف الحرب أقل بـ 15%، والغنائم أعلى بـ 10% لمدة 8 ساعات!",
        "effect_label": "تكاليف شن الحرب -15% والغنائم +10%",
    },
    # ─── تقدم ───
    {
        "name": "golden_age", "name_ar": "العصر الذهبي", "emoji": "🌟",
        "event_type": "progress", "effect_key": "xp_bonus", "effect_value": 0.30,
        "duration_hours": 10,
        "description_ar": "نقاط الخبرة والنفوذ أعلى بـ 30% لمدة 10 ساعات!",
        "effect_label": "نقاط الخبرة والنفوذ +30%",
    },
    {
        "name": "tech_breakthrough", "name_ar": "اختراق تقني", "emoji": "⚙️",
        "event_type": "progress", "effect_key": "production_bonus", "effect_value": 0.25,
        "duration_hours": 10,
        "description_ar": "إنتاج جميع المدن أعلى بـ 25% لمدة 10 ساعات!",
        "effect_label": "إنتاجية المدن +25%",
    },
    {
        "name": "recruitment_drive", "name_ar": "حملة التجنيد", "emoji": "🪖",
        "event_type": "progress", "effect_key": "troop_cost_discount", "effect_value": 0.20,
        "duration_hours": 8,
        "description_ar": "تكلفة شراء الجنود أقل بـ 20% لمدة 8 ساعات!",
        "effect_label": "تخفيض 20% على شراء جميع وحدات الجيش",
    },
    {
        "name": "arms_sale", "name_ar": "تخفيضات الأسلحة", "emoji": "🔫",
        "event_type": "progress", "effect_key": "equipment_cost_discount", "effect_value": 0.20,
        "duration_hours": 8,
        "description_ar": "تكلفة شراء المعدات العسكرية أقل بـ 20% لمدة 8 ساعات!",
        "effect_label": "تخفيض 20% على شراء المعدات العسكرية",
    },
    {
        "name": "construction_boom", "name_ar": "طفرة البناء", "emoji": "🏗️",
        "event_type": "progress", "effect_key": "asset_cost_discount", "effect_value": 0.15,
        "duration_hours": 10,
        "description_ar": "تكلفة شراء وترقية مرافق المدن أقل بـ 15% لمدة 10 ساعات!",
        "effect_label": "تخفيض 15% على بناء وترقية مرافق المدن",
    },
]


# lookup map: effect_key → effect_label (for events loaded from DB that may lack the field)
_EFFECT_LABELS: dict[str, str] = {e["effect_key"]: e["effect_label"] for e in EVENT_POOL}


def _effect_label(event: dict) -> str:
    """Returns a human-readable effect description, never exposing internal keys."""
    return (
        event.get("effect_label")
        or _EFFECT_LABELS.get(event.get("effect_key", ""), "")
        or event.get("description_ar", "")
    )


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
        label = _effect_label(event)
        msg = (
            f"{event['emoji']} <b>حدث عالمي جديد!</b>\n\n"
            f"<b>{event['name_ar']}</b>\n"
            f"📝 {event['description_ar']}\n"
            f"🔑 التأثير: {label}\n"
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
    """نص عرض الحدث النشط — مختصر للرسائل، بدون مفاتيح تقنية"""
    event = get_active_event()
    if not event:
        return ""
    from utils.helpers import format_remaining_time
    now       = int(time.time())
    remaining = max(0, event["ends_at"] - now)
    label     = _effect_label(event)
    return (
        f"\n\n{event['emoji']} <b>حدث نشط: {event['name_ar']}</b>\n"
        f"📝 {event['description_ar']}\n"
        f"🔑 التأثير: {label}\n"
        f"⏱️ ينتهي خلال: {format_remaining_time(remaining)}"
    )


def get_events_page() -> str:
    """صفحة الأحداث الكاملة — حدث نشط + قائمة جميع الأحداث المحتملة"""
    from utils.helpers import get_lines
    lines = get_lines()
    event = get_active_event()
    now   = int(time.time())

    # ── الحدث النشط ──
    if event:
        remaining = max(0, event["ends_at"] - now)
        from utils.helpers import format_remaining_time
        label = _effect_label(event)
        active_text = (
            f"{event['emoji']} <b>{event['name_ar']}</b>\n"
            f"📝 {event['description_ar']}\n"
            f"🔑 التأثير:\n"
            f"  • {label}\n"
            f"⏱️ ينتهي خلال: {format_remaining_time(remaining)}"
        )
    else:
        active_text = "☮️ لا يوجد حدث نشط حالياً.\nتحقق لاحقاً — الأحداث تظهر بشكل عشوائي!"

    # ── آخر الأحداث ──
    recent = get_recent_events(5)
    history_lines = [
        f"  {e['emoji']} {e['name_ar']} — انتهى"
        for e in recent if e.get("status") == "ended"
    ]
    history_block = ""
    if history_lines:
        history_block = f"\n📜 <b>آخر الأحداث:</b>\n" + "\n".join(history_lines) + "\n"

    # ── قائمة جميع الأحداث المحتملة مجمّعة حسب النوع ──
    type_labels = {
        "war":      "⚔️ أحداث الحرب",
        "economy":  "💰 أحداث الاقتصاد",
        "spy":      "🕵️ أحداث التجسس",
        "alliance": "🤝 أحداث التحالفات",
        "disaster": "🌪️ الكوارث",
        "progress": "🌟 أحداث التقدم",
    }
    grouped: dict[str, list] = {}
    for e in EVENT_POOL:
        grouped.setdefault(e["event_type"], []).append(e)

    pool_lines = []
    for etype, label in type_labels.items():
        entries = grouped.get(etype, [])
        if not entries:
            continue
        pool_lines.append(f"\n<b>{label}:</b>")
        for e in entries:
            pool_lines.append(f"  {e['emoji']} <b>{e['name_ar']}</b> → {e['effect_label']}")

    pool_block = "\n".join(pool_lines)

    return (
        f"🌍 <b>الأحداث العالمية</b>\n{lines}\n\n"
        f"🔴 <b>الحدث النشط:</b>\n{active_text}\n"
        f"{history_block}"
        f"\n{lines}\n"
        f"💡 <b>جميع الأحداث المحتملة:</b>"
        f"{pool_block}"
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
    """Deprecated — event checking is now handled by the unified IntervalScheduler."""
    pass
