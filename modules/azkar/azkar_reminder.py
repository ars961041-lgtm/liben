"""
نظام تذكير الأذكار — ذكرني ذكري

التدفق:
  ذكرني ذكري → اختر النوع → اختر الساعة → اختر الدقيقة
  → إذا كان التوقيت محفوظاً: تأكيد مباشر (مع خيار تغييره)
  → إذا لم يُحدَّد التوقيت: اختر التوقيت → حفظ
  في الوقت المحدد → يرسل رسالة خاصة + يفتح واجهة الأذكار
"""
import time
import threading
from datetime import datetime, timezone

from core.bot import bot
from utils.pagination import btn, send_ui, edit_ui, register_action
from utils.helpers import get_lines
from modules.azkar import azkar_db as db
from modules.azkar.azkar_handler import (
    TYPE_MORNING, TYPE_EVENING, TYPE_SLEEP, TYPE_WAKEUP,
    TYPE_LABELS, TYPE_EMOJI, _open_azkar_for_user,
)
from database.db_queries.timezone_queries import get_user_tz, set_user_tz

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
        btn("📋 تذكيراتي",  "rem_list",  {}, owner=owner, color="p"),
        btn("❌ إغلاق",     "rem_close", {}, owner=owner, color="d"),
    ]
    send_ui(cid, text=text, buttons=buttons, layout=[2, 2, 2],
            owner_id=uid, reply_to=message.message_id)
    return True


def _fmt_hour(h: int) -> str:
    """يحوّل الساعة من 24 إلى 12 مع مؤشر ص/م."""
    period = "ص" if h < 12 else "م"
    h12    = h % 12 or 12
    return f"{h12:02d} {period}"


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
    # 24 ساعة بتنسيق 12 ساعة، 4 في الصف، من اليمين لليسار
    hour_btns = [
        btn(_fmt_hour(h), "rem_pick_hour", {"t": t, "h": h}, owner=owner)
        for h in range(24)
    ]
    hour_btns.append(btn("🔙 رجوع", "rem_back_main", {}, owner=owner, color="d"))
    edit_ui(call, text=text, buttons=hour_btns, layout=[4, 4, 4, 4, 4, 4, 1])

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

    # إذا كان التوقيت محفوظاً → الدقيقة تؤدي مباشرة لشاشة التأكيد
    stored_tz     = get_user_tz(uid)
    minute_action = "rem_confirm_stored" if stored_tz is not None else "rem_pick_tz"

    text = (
        f"{TYPE_EMOJI[t]} <b>أذكار {TYPE_LABELS[t]}</b>\n"
        f"⏰ الساعة: <b>{_fmt_hour(h)}</b>\n\n"
        "اختر الدقيقة:"
    )
    min_btns = [
        btn(f"{m:02d}", minute_action, {"t": t, "h": h, "m": m}, owner=owner)
        for m in range(0, 60, 5)
    ]
    min_btns.append(btn("🔙 رجوع", "rem_pick_type", {"t": t}, owner=owner, color="d"))
    edit_ui(call, text=text, buttons=min_btns, layout=[6, 6, 1])


# ══════════════════════════════════════════
# تأكيد مباشر (التوقيت محفوظ)
# ══════════════════════════════════════════

@register_action("rem_confirm_stored")
def on_confirm_stored(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    t     = int(data["t"])
    h     = int(data["h"])
    m     = int(data["m"])
    owner = (uid, cid)

    stored_tz = get_user_tz(uid)
    if stored_tz is None:
        # fallback
        bot.answer_callback_query(call.id)
        _show_tz_picker(call, t, h, m, owner)
        return

    tz_h     = stored_tz // 60
    tz_label = f"UTC{'+' if tz_h >= 0 else ''}{tz_h}"
    bot.answer_callback_query(call.id)

    edit_ui(call,
            text=(
                f"{TYPE_EMOJI[t]} <b>أذكار {TYPE_LABELS[t]}</b>\n"
                f"⏰ الوقت: <b>{_fmt_hour(h)}:{m:02d}</b>\n"
                f"🌍 التوقيت المحفوظ: <b>{tz_label}</b>\n\n"
                "هل تريد الحفظ بهذا التوقيت؟"
            ),
            buttons=[
                btn("✅ حفظ", "rem_confirm",
                    {"t": t, "h": h, "m": m, "tz": stored_tz}, owner=owner, color="su"),
                btn("✏️ تغيير التوقيت", "rem_pick_tz",
                    {"t": t, "h": h, "m": m}, owner=owner, color="p"),
                btn("🔙 رجوع", "rem_pick_hour",
                    {"t": t, "h": h}, owner=owner, color="d"),
            ],
            layout=[1, 1, 1])


# ══════════════════════════════════════════
# اختيار فارق التوقيت
# ══════════════════════════════════════════

@register_action("rem_pick_tz")
def on_pick_tz(call, data):
    t = int(data["t"])
    h = int(data["h"])
    m = int(data["m"])
    owner = (call.from_user.id, call.message.chat.id)
    bot.answer_callback_query(call.id)
    _show_tz_picker(call, t, h, m, owner)


def _show_tz_picker(call, t, h, m, owner):
    text = (
        f"{TYPE_EMOJI[t]} <b>أذكار {TYPE_LABELS[t]}</b>\n"
        f"⏰ الوقت: <b>{_fmt_hour(h)}:{m:02d}</b>\n\n"
        "اختر فارق توقيتك عن UTC\n"
        "مثال: اليمن = UTC+3 → اختر <b>+3</b>"
    )
    tz_btns = [
        btn(f"UTC{'+' if o >= 0 else ''}{o}", "rem_confirm",
            {"t": t, "h": h, "m": m, "tz": o * 60}, owner=owner)
        for o in range(-12, 15)
    ]
    tz_btns.append(btn("🔙 رجوع", "rem_pick_hour", {"t": t, "h": h}, owner=owner, color="d"))
    edit_ui(call, text=text, buttons=tz_btns, layout=[3] * 9 + [1])


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

    if not _check_can_pm(uid):
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

    if db.count_user_reminders(uid) >= _MAX_REMINDERS:
        bot.answer_callback_query(call.id)
        edit_ui(call, text=_LIMIT_MSG,
                buttons=[
                    btn("📋 تذكيراتي", "rem_list",  {}, owner=owner, color="p"),
                    btn("❌ إغلاق",    "rem_close", {}, owner=owner, color="d"),
                ],
                layout=[1, 1])
        return

    # حفظ التوقيت للاستخدام المستقبلي
    set_user_tz(uid, tz)

    rem_id   = db.add_reminder(uid, t, h, m, tz)
    tz_h     = tz // 60
    tz_label = f"UTC{'+' if tz_h >= 0 else ''}{tz_h}"
    bot.answer_callback_query(call.id, "✅ تم حفظ التذكير!", show_alert=True)
    edit_ui(call,
            text=(
                f"✅ <b>تم حفظ التذكير #{rem_id}</b>\n{get_lines()}\n\n"
                f"{TYPE_EMOJI[t]} أذكار {TYPE_LABELS[t]}\n"
                f"⏰ الوقت: <b>{_fmt_hour(h)}:{m:02d}</b> ({tz_label})\n\n"
                "ستصلك رسالة خاصة في الوقت المحدد يومياً 🔔"
            ),
            buttons=[
                btn("📋 تذكيراتي",     "rem_list",      {}, owner=owner, color="p"),
                btn("✏️ تغيير توقيتي", "rem_edit_tz",   {}, owner=owner, color="p"),
                btn("➕ إضافة آخر",    "rem_back_main", {}, owner=owner),
                btn("❌ إغلاق",        "rem_close",     {}, owner=owner, color="d"),
            ],
            layout=[2, 1, 1])


# ══════════════════════════════════════════
# تعديل التوقيت المحفوظ
# ══════════════════════════════════════════

@register_action("rem_edit_tz")
def on_edit_tz(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)
    bot.answer_callback_query(call.id)

    stored_tz = get_user_tz(uid)
    tz_h      = stored_tz // 60 if stored_tz is not None else 0
    tz_label  = f"UTC{'+' if tz_h >= 0 else ''}{tz_h}" if stored_tz is not None else "غير محدد"

    tz_btns = [
        btn(f"UTC{'+' if o >= 0 else ''}{o}", "rem_save_tz",
            {"tz": o * 60}, owner=owner)
        for o in range(-12, 15)
    ]
    tz_btns.append(btn("🔙 رجوع", "rem_back_main", {}, owner=owner, color="d"))
    edit_ui(call,
            text=(
                f"🌍 <b>تعديل التوقيت</b>\n{get_lines()}\n\n"
                f"توقيتك الحالي: <b>{tz_label}</b>\n\n"
                "اختر توقيتك الجديد:"
            ),
            buttons=tz_btns,
            layout=[3] * 9 + [1])


@register_action("rem_save_tz")
def on_save_tz(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)
    tz    = int(data["tz"])
    tz_h  = tz // 60
    set_user_tz(uid, tz)
    bot.answer_callback_query(call.id,
                              f"✅ تم حفظ التوقيت: UTC{'+' if tz_h >= 0 else ''}{tz_h}",
                              show_alert=True)
    on_back_main(call, {})


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
    stored_tz = get_user_tz(uid)
    tz_h      = stored_tz // 60 if stored_tz is not None else None
    tz_info   = f"\n🌍 توقيتك المحفوظ: <b>UTC{'+' if tz_h >= 0 else ''}{tz_h}</b>" if tz_h is not None else ""

    if not reminders:
        edit_ui(call,
                text=f"📋 <b>تذكيراتك</b>{tz_info}\n\nلا توجد تذكيرات نشطة.",
                buttons=[
                    btn("➕ إضافة تذكير",  "rem_back_main", {}, owner=owner),
                    btn("✏️ تغيير توقيتي", "rem_edit_tz",   {}, owner=owner, color="p"),
                    btn("❌ إغلاق",        "rem_close",     {}, owner=owner, color="d"),
                ],
                layout=[1, 1, 1])
        return

    text = f"📋 <b>تذكيراتك ({len(reminders)})</b>{tz_info}\n{get_lines()}\n\n"
    buttons = []
    for r in reminders:
        rtz_h = r["tz_offset"] // 60
        label = (
            f"{TYPE_EMOJI[r['azkar_type']]} {_fmt_hour(r['hour'])}:{r['minute']:02d} "
            f"(UTC{'+' if rtz_h >= 0 else ''}{rtz_h})"
        )
        text += f"• {label} — أذكار {TYPE_LABELS[r['azkar_type']]}\n"
        buttons.append(btn(f"🗑 حذف #{r['id']}", "rem_delete",
                           {"rid": r["id"]}, owner=owner, color="d"))

    buttons += [
        btn("➕ إضافة تذكير",  "rem_back_main", {}, owner=owner),
        btn("✏️ تغيير توقيتي", "rem_edit_tz",   {}, owner=owner, color="p"),
        btn("❌ إغلاق",        "rem_close",     {}, owner=owner, color="d"),
    ]
    layout = [1] * len(reminders) + [1, 1, 1]
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
        btn("📋 تذكيراتي",  "rem_list",  {}, owner=owner, color="p"),
        btn("❌ إغلاق",     "rem_close", {}, owner=owner, color="d"),
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
    try:
        bot.send_chat_action(user_id, "typing")
        return True
    except Exception:
        return False


# ══════════════════════════════════════════
# المُجدوِل
# ══════════════════════════════════════════

def _scheduler_loop():
    while True:
        try:
            now        = datetime.now(timezone.utc)
            due        = db.get_due_reminders(now.hour, now.minute)
            for r in due:
                _fire_reminder(r)
        except Exception as e:
            print(f"[AzkarReminder] {e}")
        time.sleep(60 - datetime.now().second)


def _fire_reminder(r: dict):
    uid        = r["user_id"]
    azkar_type = r["azkar_type"]
    try:
        bot.send_message(
            uid,
            f"🔔 <b>حان وقت أذكار {TYPE_LABELS[azkar_type]}!</b>\n\n"
            f"{TYPE_EMOJI[azkar_type]} ابدأ أذكارك الآن 👇",
            parse_mode="HTML",
        )
        _open_azkar_for_user(uid, uid, azkar_type)
    except Exception as e:
        print(f"[AzkarReminder] فشل إرسال تذكير للمستخدم {uid}: {e}")


def start_reminder_scheduler():
    threading.Thread(target=_scheduler_loop, daemon=True).start()
