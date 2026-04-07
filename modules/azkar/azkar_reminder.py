"""
نظام تذكير الأذكار — ذكرني ذكري

التدفق:
  ذكرني ذكري → اختر النوع → اختر الساعة → اختر الدقيقة → أدخل فارق التوقيت → حفظ
  في الوقت المحدد → يرسل رسالة خاصة + يفتح واجهة الأذكار
"""
import time
import threading
from datetime import datetime, timezone

from core.bot import bot
from utils.pagination import btn, send_ui, edit_ui, register_action, set_state, get_state, clear_state
from utils.helpers import get_lines
from modules.azkar import azkar_db as db
from modules.azkar.azkar_handler import (
    TYPE_MORNING, TYPE_EVENING, TYPE_SLEEP, TYPE_WAKEUP,
    TYPE_LABELS, TYPE_EMOJI, _open_azkar_for_user
)


_MAX_REMINDERS = 4
_LIMIT_MSG = (
    "❌ <b>لا يمكنك إضافة أكثر من 4 تذكيرات</b>\n\n"
    "قم بحذف أحد التذكيرات أولاً من قائمة 📋 تذكيراتي."
)


# ══════════════════════════════════════════
# نقطة الدخول
# ══════════════════════════════════════════

def handle_reminder_command(message) -> bool:
    if (message.text or "").strip() != "ذكرني ذكري":
        return False
    uid   = message.from_user.id
    cid   = message.chat.id
    owner = (uid, cid)

    # ── check limit before starting the flow ──
    if db.count_user_reminders(uid) >= _MAX_REMINDERS:
        send_ui(cid, text=_LIMIT_MSG,
                buttons=[
                    btn("📋 تذكيراتي", "rem_list",  {}, owner=owner, color="p"),
                    btn("❌ إغلاق",    "rem_close", {}, owner=owner, color="d"),
                ],
                layout=[1, 1], owner_id=uid, reply_to=message.message_id)
        return True

    text = (
        f"🔔 <b>تذكير الأذكار</b>\n{get_lines()}\n\n"
        "اختر نوع الأذكار التي تريد تذكيراً بها:"
    )
    buttons = [
        btn(f"{TYPE_EMOJI[t]} أذكار {TYPE_LABELS[t]}", "rem_pick_type",
            {"t": t}, owner=owner)
        for t in (TYPE_MORNING, TYPE_EVENING, TYPE_SLEEP, TYPE_WAKEUP)
    ] + [
        btn("📋 تذكيراتي",  "rem_list",   {}, owner=owner, color="p"),
        btn("❌ إغلاق",     "rem_close",  {}, owner=owner, color="d"),
    ]
    send_ui(cid, text=text, buttons=buttons, layout=[2, 2, 2],
            owner_id=uid, reply_to=message.message_id)
    return True


# ══════════════════════════════════════════
# اختيار النوع → الساعة
# ══════════════════════════════════════════

@register_action("rem_pick_type")
def on_pick_type(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    t     = int(data["t"])
    owner = (uid, cid)
    bot.answer_callback_query(call.id)

    text = (
        f"{TYPE_EMOJI[t]} <b>أذكار {TYPE_LABELS[t]}</b>\n\n"
        "اختر الساعة (بتوقيتك المحلي):"
    )
    # صفوف: 0-5, 6-11, 12-17, 18-23
    hour_btns = [
        btn(f"{h:02d}", "rem_pick_hour", {"t": t, "h": h}, owner=owner)
        for h in range(24)
    ]
    hour_btns.append(btn("🔙 رجوع", "rem_back_main", {}, owner=owner, color="d"))
    layout = [6, 6, 6, 6, 1]
    edit_ui(call, text=text, buttons=hour_btns, layout=layout)


# ══════════════════════════════════════════
# اختيار الدقيقة
# ══════════════════════════════════════════

@register_action("rem_pick_hour")
def on_pick_hour(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    t     = int(data["t"])
    h     = int(data["h"])
    owner = (uid, cid)
    bot.answer_callback_query(call.id)

    text = (
        f"{TYPE_EMOJI[t]} <b>أذكار {TYPE_LABELS[t]}</b>\n"
        f"⏰ الساعة: <b>{h:02d}</b>\n\n"
        "اختر الدقيقة:"
    )
    min_btns = [
        btn(f"{m:02d}", "rem_pick_tz", {"t": t, "h": h, "m": m}, owner=owner)
        for m in range(0, 60, 5)
    ]
    min_btns.append(btn("🔙 رجوع", "rem_pick_type", {"t": t}, owner=owner, color="d"))
    layout = [6, 6] + [1]
    edit_ui(call, text=text, buttons=min_btns, layout=layout)


# ══════════════════════════════════════════
# اختيار فارق التوقيت
# ══════════════════════════════════════════

@register_action("rem_pick_tz")
def on_pick_tz(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    t     = int(data["t"])
    h     = int(data["h"])
    m     = int(data["m"])
    owner = (uid, cid)
    bot.answer_callback_query(call.id)

    text = (
        f"{TYPE_EMOJI[t]} <b>أذكار {TYPE_LABELS[t]}</b>\n"
        f"⏰ الوقت: <b>{h:02d}:{m:02d}</b>\n\n"
        "اختر فارق توقيتك عن UTC\n"
        "مثال: اليمن = UTC+3 → اختر <b>+3</b>"
    )
    # UTC-12 إلى UTC+14 بخطوة ساعة
    tz_btns = []
    for offset_h in range(-12, 15):
        label = f"UTC{'+' if offset_h >= 0 else ''}{offset_h}"
        tz_btns.append(btn(label, "rem_confirm",
                           {"t": t, "h": h, "m": m, "tz": offset_h * 60},
                           owner=owner))
    tz_btns.append(btn("🔙 رجوع", "rem_pick_hour", {"t": t, "h": h}, owner=owner, color="d"))
    layout = [3] * 9 + [1]
    edit_ui(call, text=text, buttons=tz_btns, layout=layout)


# ══════════════════════════════════════════
# تأكيد وحفظ
# ══════════════════════════════════════════

@register_action("rem_confirm")
def on_confirm(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    t     = int(data["t"])
    h     = int(data["h"])
    m     = int(data["m"])
    tz    = int(data["tz"])
    owner = (uid, cid)

    # تحقق من إمكانية مراسلة المستخدم في الخاص
    can_pm = _check_can_pm(uid)

    if not can_pm:
        bot.answer_callback_query(call.id)
        edit_ui(call,
                text=(
                    "⚠️ <b>لا يمكن إرسال التذكير!</b>\n\n"
                    "يجب أن تبدأ محادثة خاصة مع البوت أولاً.\n"
                    "افتح الخاص مع البوت واضغط Start، ثم حاول مجدداً."
                ),
                buttons=[btn("❌ إغلاق", "rem_close", {}, owner=owner, color="d")],
                layout=[1])
        return

    # ── second limit check (race-condition guard) ──
    if db.count_user_reminders(uid) >= _MAX_REMINDERS:
        bot.answer_callback_query(call.id)
        edit_ui(call, text=_LIMIT_MSG,
                buttons=[
                    btn("📋 تذكيراتي", "rem_list",  {}, owner=owner, color="p"),
                    btn("❌ إغلاق",    "rem_close", {}, owner=owner, color="d"),
                ],
                layout=[1, 1])
        return

    rem_id = db.add_reminder(uid, t, h, m, tz)
    tz_label = f"UTC{'+' if tz >= 0 else ''}{tz // 60}"
    bot.answer_callback_query(call.id, "✅ تم حفظ التذكير!", show_alert=True)
    edit_ui(call,
            text=(
                f"✅ <b>تم حفظ التذكير #{rem_id}</b>\n{get_lines()}\n\n"
                f"{TYPE_EMOJI[t]} أذكار {TYPE_LABELS[t]}\n"
                f"⏰ الوقت: <b>{h:02d}:{m:02d}</b> ({tz_label})\n\n"
                "ستصلك رسالة خاصة في الوقت المحدد يومياً 🔔"
            ),
            buttons=[
                btn("📋 تذكيراتي", "rem_list",      {}, owner=owner, color="p"),
                btn("➕ إضافة آخر", "rem_back_main", {}, owner=owner),
                btn("❌ إغلاق",    "rem_close",     {}, owner=owner, color="d"),
            ],
            layout=[1, 1, 1])


# ══════════════════════════════════════════
# قائمة التذكيرات
# ══════════════════════════════════════════

@register_action("rem_list")
def on_list(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)
    bot.answer_callback_query(call.id)

    reminders = db.get_user_reminders(uid)
    if not reminders:
        edit_ui(call,
                text="📋 <b>تذكيراتك</b>\n\nلا توجد تذكيرات نشطة.",
                buttons=[
                    btn("➕ إضافة تذكير", "rem_back_main", {}, owner=owner),
                    btn("❌ إغلاق",       "rem_close",     {}, owner=owner, color="d"),
                ],
                layout=[1, 1])
        return

    text = f"📋 <b>تذكيراتك ({len(reminders)})</b>\n{get_lines()}\n\n"
    buttons = []
    for r in reminders:
        tz_h  = r["tz_offset"] // 60
        label = f"{TYPE_EMOJI[r['azkar_type']]} {r['hour']:02d}:{r['minute']:02d} (UTC{'+' if tz_h >= 0 else ''}{tz_h})"
        text += f"• {label} — أذكار {TYPE_LABELS[r['azkar_type']]}\n"
        buttons.append(btn(f"🗑 حذف #{r['id']}", "rem_delete",
                           {"rid": r["id"]}, owner=owner, color="d"))

    buttons += [
        btn("➕ إضافة تذكير", "rem_back_main", {}, owner=owner),
        btn("❌ إغلاق",       "rem_close",     {}, owner=owner, color="d"),
    ]
    layout = [1] * len(reminders) + [1, 1]
    edit_ui(call, text=text, buttons=buttons, layout=layout)


@register_action("rem_delete")
def on_delete(call, data):
    uid = call.from_user.id
    rid = int(data["rid"])
    db.delete_reminder(rid, uid)
    bot.answer_callback_query(call.id, "✅ تم حذف التذكير", show_alert=True)
    on_list(call, {})


@register_action("rem_back_main")
def on_back_main(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)
    bot.answer_callback_query(call.id)
    text = (
        f"🔔 <b>تذكير الأذكار</b>\n{get_lines()}\n\n"
        "اختر نوع الأذكار التي تريد تذكيراً بها:"
    )
    buttons = [
        btn(f"{TYPE_EMOJI[t]} أذكار {TYPE_LABELS[t]}", "rem_pick_type",
            {"t": t}, owner=owner)
        for t in (TYPE_MORNING, TYPE_EVENING, TYPE_SLEEP, TYPE_WAKEUP)
    ] + [
        btn("📋 تذكيراتي", "rem_list",  {}, owner=owner, color="p"),
        btn("❌ إغلاق",    "rem_close", {}, owner=owner, color="d"),
    ]
    edit_ui(call, text=text, buttons=buttons, layout=[2, 2, 2])


@register_action("rem_close")
def on_close(call, data):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


# ══════════════════════════════════════════
# مساعدات
# ══════════════════════════════════════════

def _check_can_pm(user_id: int) -> bool:
    """يتحقق إذا كان البوت يستطيع مراسلة المستخدم في الخاص."""
    try:
        bot.send_chat_action(user_id, "typing")
        return True
    except Exception:
        return False


# ══════════════════════════════════════════
# المُجدوِل — يعمل في الخلفية
# ══════════════════════════════════════════

def _scheduler_loop():
    """يفحص التذكيرات كل دقيقة ويرسل الإشعارات."""
    while True:
        try:
            now        = datetime.now(timezone.utc)
            utc_hour   = now.hour
            utc_minute = now.minute
            due        = db.get_due_reminders(utc_hour, utc_minute)
            for r in due:
                _fire_reminder(r)
        except Exception as e:
            print(f"[AzkarReminder] {e}")
        # انتظر حتى بداية الدقيقة التالية
        time.sleep(60 - datetime.now().second)


def _fire_reminder(r: dict):
    """يرسل إشعار التذكير ويفتح واجهة الأذكار."""
    uid        = r["user_id"]
    azkar_type = r["azkar_type"]
    emoji      = TYPE_EMOJI[azkar_type]
    label      = TYPE_LABELS[azkar_type]

    try:
        # رسالة تنبيه
        bot.send_message(
            uid,
            f"🔔 <b>حان وقت أذكار {label}!</b>\n\n"
            f"{emoji} ابدأ أذكارك الآن 👇",
            parse_mode="HTML"
        )
        # افتح واجهة الأذكار مباشرة
        _open_azkar_for_user(uid, uid, azkar_type)
    except Exception as e:
        print(f"[AzkarReminder] فشل إرسال تذكير للمستخدم {uid}: {e}")


def start_reminder_scheduler():
    """يُشغَّل عند بدء البوت."""
    threading.Thread(target=_scheduler_loop, daemon=True).start()
