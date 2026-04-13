"""
واجهة الأحداث العالمية — نظام تصفح تفاعلي بالأزرار.
"""
import time

from core.bot import bot
from utils.pagination import btn, send_ui, edit_ui, register_action, grid
from utils.helpers import get_lines
from modules.progression.global_events import (
    EVENT_POOL, get_active_event, get_recent_events, _effect_label,
)

# ── ألوان ──
BLUE  = "p"
RED   = "d"
GREEN = "su"
GREY  = "de"

# ── تسميات الفئات ──
CATEGORY_META: dict[str, dict] = {
    "war":      {"label": "⚔️ أحداث الحرب",       "emoji": "⚔️"},
    "economy":  {"label": "💰 أحداث الاقتصاد",    "emoji": "💰"},
    "spy":      {"label": "🕵️ أحداث التجسس",      "emoji": "🕵️"},
    "alliance": {"label": "🤝 أحداث التحالفات",   "emoji": "🤝"},
    "disaster": {"label": "🌪️ الكوارث",           "emoji": "🌪️"},
    "progress": {"label": "🌟 أحداث التقدم",       "emoji": "🌟"},
}


# ══════════════════════════════════════════
# 🏠 الصفحة الرئيسية
# ══════════════════════════════════════════

def _main_text() -> str:
    lines   = get_lines()
    event   = get_active_event()
    now     = int(time.time())

    if event:
        remaining = max(0, event["ends_at"] - now)
        from utils.helpers import format_remaining_time
        label = _effect_label(event)
        active_block = (
            f"{event['emoji']} <b>{event['name_ar']}</b>\n"
            f"📝 {event['description_ar']}\n"
            f"🔑 التأثير: {label}\n"
            f"⏱️ ينتهي خلال: {format_remaining_time(remaining)}"
        )
    else:
        active_block = "☮️ لا يوجد حدث نشط حالياً.\nتحقق لاحقاً — الأحداث تظهر بشكل عشوائي!"

    recent = get_recent_events(3)
    history_lines = [
        f"  {e['emoji']} {e['name_ar']} — انتهى"
        for e in recent if e.get("status") == "ended"
    ]
    history_block = ("\n📜 <b>آخر الأحداث:</b>\n" + "\n".join(history_lines)) if history_lines else ""

    return (
        f"🌍 <b>الأحداث العالمية</b>\n{lines}\n\n"
        f"🔴 <b>الحدث النشط:</b>\n{active_block}"
        f"{history_block}\n\n"
        f"💡 اختر فئة لاستعراض أحداثها:"
    )


def _main_buttons(owner: tuple) -> tuple[list, list]:
    cats = list(CATEGORY_META.items())
    buttons = [
        btn(meta["label"], "ev_category", {"cat": cat}, color=BLUE, owner=owner)
        for cat, meta in cats
    ]
    layout = grid(len(buttons), 2)
    return buttons, layout


def open_events_main(message):
    """Entry point from text command."""
    owner   = (message.from_user.id, message.chat.id)
    text    = _main_text()
    buttons, layout = _main_buttons(owner)
    send_ui(message.chat.id, text=text, buttons=buttons, layout=layout,
            owner_id=message.from_user.id)


# ══════════════════════════════════════════
# 📂 صفحة الفئة
# ══════════════════════════════════════════

def _category_text(cat: str) -> str:
    meta   = CATEGORY_META.get(cat, {"label": cat, "emoji": "📋"})
    lines  = get_lines()
    events = [e for e in EVENT_POOL if e["event_type"] == cat]
    active = get_active_event()

    rows = []
    for e in events:
        is_active = active and active.get("name") == e["name"]
        status    = "🟢 نشط الآن" if is_active else "⚪ غير نشط"
        rows.append(
            f"{e['emoji']} <b>{e['name_ar']}</b>\n"
            f"   📝 {e['effect_label']}\n"
            f"   📊 الحالة: {status} | ⏱️ المدة: {e['duration_hours']}س"
        )

    body = "\n\n".join(rows) if rows else "لا توجد أحداث في هذه الفئة."
    return (
        f"{meta['emoji']} <b>{meta['label']}</b>\n{lines}\n\n"
        f"{body}"
    )


def _category_buttons(cat: str, owner: tuple) -> tuple[list, list]:
    events  = [e for e in EVENT_POOL if e["event_type"] == cat]
    buttons = [
        btn(f"{e['emoji']} {e['name_ar']}", "ev_detail",
            {"name": e["name"]}, color=BLUE, owner=owner)
        for e in events
    ]
    buttons.append(btn("🔙 رجوع", "ev_main", {}, color=RED, owner=owner))
    layout = grid(len(buttons) - 1, 2) + [1]
    return buttons, layout


@register_action("ev_category")
def handle_ev_category(call, data):
    cat   = data.get("cat", "war")
    owner = (call.from_user.id, call.message.chat.id)
    text  = _category_text(cat)
    buttons, layout = _category_buttons(cat, owner)
    edit_ui(call, text=text, buttons=buttons, layout=layout)


# ══════════════════════════════════════════
# 🔍 صفحة تفاصيل الحدث
# ══════════════════════════════════════════

def _detail_text(event_def: dict) -> str:
    lines  = get_lines()
    active = get_active_event()
    now    = int(time.time())

    is_active = active and active.get("name") == event_def["name"]
    if is_active:
        remaining = max(0, active["ends_at"] - now)
        from utils.helpers import format_remaining_time
        status_line = f"🟢 <b>نشط الآن</b> — ينتهي خلال {format_remaining_time(remaining)}"
    else:
        status_line = "⚪ غير نشط حالياً"

    cat_meta = CATEGORY_META.get(event_def["event_type"], {"label": event_def["event_type"]})

    return (
        f"{event_def['emoji']} <b>{event_def['name_ar']}</b>\n{lines}\n\n"
        f"📝 <b>الوصف:</b>\n{event_def['description_ar']}\n\n"
        f"🔑 <b>التأثير:</b>\n  • {event_def['effect_label']}\n\n"
        f"📊 <b>الحالة:</b> {status_line}\n"
        f"⏱️ <b>المدة:</b> {event_def['duration_hours']} ساعة\n"
        f"🗂 <b>الفئة:</b> {cat_meta['label']}"
    )


@register_action("ev_detail")
def handle_ev_detail(call, data):
    name       = data.get("name", "")
    owner      = (call.from_user.id, call.message.chat.id)
    event_def  = next((e for e in EVENT_POOL if e["name"] == name), None)

    if not event_def:
        bot.answer_callback_query(call.id, "❌ الحدث غير موجود", show_alert=True)
        return

    text    = _detail_text(event_def)
    back    = [btn("🔙 رجوع", "ev_category", {"cat": event_def["event_type"]},
                   color=RED, owner=owner)]
    edit_ui(call, text=text, buttons=back, layout=[1])


# ══════════════════════════════════════════
# 🔙 رجوع للرئيسية
# ══════════════════════════════════════════

@register_action("ev_main")
def handle_ev_main(call, data):
    owner   = (call.from_user.id, call.message.chat.id)
    text    = _main_text()
    buttons, layout = _main_buttons(owner)
    edit_ui(call, text=text, buttons=buttons, layout=layout)
