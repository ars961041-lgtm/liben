"""
معالج التذاكر — منطق الأعمال الأساسي
"""
import time
from core.bot import bot
from core.config import developers_id
from core.dev_notifier import send_to_dev_group
from utils.helpers import get_lines
from modules.tickets.ticket_db import (
    create_ticket, get_ticket, get_open_ticket_for_user,
    add_ticket_message, close_ticket, set_ticket_group_msg,
    get_ticket_by_group_msg, check_limits, record_ticket_usage,
)
from core.admin import get_const_int


def _get_dev_group_id() -> int:
    """يجلب معرف مجموعة المطورين ديناميكياً في كل استدعاء."""
    return get_const_int("dev_group_id", -1)


# ─── قائمة المطورين ───
DEVELOPERS = list(developers_id)

# ─── فئات التذاكر ───
CATEGORIES = {
    "bug":        "🐞 خطأ برمجي",
    "suggestion": "💡 اقتراح",
    "complaint":  "🚫 شكوى",
}

# ─── حالة انتظار الفئة ───
_AWAITING_CATEGORY: dict[int, dict] = {}
# ─── حالة انتظار رد المطور ───
_AWAITING_DEV_REPLY: dict[int, int] = {}  # user_id → ticket_id


def is_developer(user_id):
    return user_id in DEVELOPERS


# ══════════════════════════════════════════
# 🎫 بدء إنشاء تذكرة
# ══════════════════════════════════════════

def start_ticket_flow(message):
    """يُطلق عند كتابة 'إبلاغ المطور'"""
    user_id = message.from_user.id
    chat_id = message.chat.id

    # رفض الملصقات
    if message.sticker:
        bot.reply_to(message, "❌ لا يمكن إرسال ملصقات كتذكرة.")
        return

    # التحقق من الحدود
    ok, err = check_limits(user_id)
    if not ok:
        bot.reply_to(message, err)
        return

    # طلب اختيار الفئة
    from utils.pagination import btn, send_ui
    buttons = [
        btn("🐞 خطأ برمجي",  "ticket_cat", data={"cat": "bug"},        owner=(user_id, chat_id), color="d"),
        btn("💡 اقتراح",      "ticket_cat", data={"cat": "suggestion"}, owner=(user_id, chat_id), color="su"),
        btn("🚫 شكوى",        "ticket_cat", data={"cat": "complaint"},  owner=(user_id, chat_id), color="p"),
    ]
    send_ui(chat_id,
            text="🎫 <b>إنشاء تذكرة جديدة</b>\n\nاختر نوع التذكرة:",
            buttons=buttons, layout=[1, 1, 1], owner_id=user_id)

    # حفظ حالة الانتظار
    _AWAITING_CATEGORY[user_id] = {
        "chat_id":    chat_id,
        "message_id": message.message_id,
        "ts":         int(time.time()),
    }


def handle_category_selection(call, data):
    """يُستدعى عند اختيار الفئة"""
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    cat     = data.get("cat")

    if cat not in CATEGORIES:
        bot.answer_callback_query(call.id, "❌ فئة غير صالحة", show_alert=True)
        return

    _AWAITING_CATEGORY.pop(user_id, None)

    # طلب الرسالة
    from utils.pagination.router import set_state
    set_state(user_id, chat_id, "awaiting_ticket_msg", data={"cat": cat})

    try:
        bot.edit_message_text(
            f"🎫 <b>تذكرة جديدة — {CATEGORIES[cat]}</b>\n\n"
            f"✏️ أرسل رسالتك الآن (نص أو صورة أو ملف):",
            chat_id, call.message.message_id, parse_mode="HTML"
        )
    except Exception:
        bot.send_message(chat_id,
                         f"✏️ أرسل رسالتك للتذكرة ({CATEGORIES[cat]}):",
                         parse_mode="HTML")


# ══════════════════════════════════════════
# 📨 استقبال رسالة التذكرة الأولى
# ══════════════════════════════════════════

def handle_ticket_message_input(message):
    """
    يُستدعى عندما يكون المستخدم في حالة 'awaiting_ticket_msg'.
    يرجع True إذا تم التعامل مع الرسالة.
    """
    from utils.pagination.router import get_state, clear_state

    user_id = message.from_user.id
    chat_id = message.chat.id

    state = get_state(user_id, chat_id)
    if state.get("state") != "awaiting_ticket_msg":
        return False

    # التحقق أن الرسالة نص فقط
    if not message.text:
        bot.reply_to(message, "❌ التذاكر تدعم النص فقط.")
        return True

    cat = state["data"].get("cat", "bug")
    clear_state(user_id, chat_id)

    # إنشاء التذكرة
    ticket_id = create_ticket(user_id, chat_id, cat)
    record_ticket_usage(user_id)

    msg_type = "text"
    content = message.text[:500]

    add_ticket_message(ticket_id, "user", message.message_id, msg_type, content)

    # إرسال للمجموعة
    group_msg_id = send_to_devs(ticket_id, message, cat)
    if group_msg_id:
        set_ticket_group_msg(ticket_id, group_msg_id)

    # تأكيد للمستخدم
    from core.personality import success_msg
    from core import memory as _mem
    from utils.helpers import send_bot_profile
    _mem.increment_daily_reports(user_id)

    caption = (
        f"{success_msg()}\n\n"
        f"🎫 رقم التذكرة: <b>#{ticket_id}</b>\n"
        f"📂 النوع: {CATEGORIES[cat]}\n\n"
        f"📨 سيتم إرسال الرد إليك في <b>خاص البوت</b>.\n"
        f"⚠️ إذا لم تكن قد راسلت البوت من قبل، اضغط الزر بالأسفل واضغط على بدء."
    )
    send_bot_profile(
        chat_id=chat_id,
        caption=caption,
        reply_to=message.message_id,
        open_pm_button=True,
    )

    return True


# ══════════════════════════════════════════
# 📤 إرسال للمجموعة
# ══════════════════════════════════════════
def send_to_devs(ticket_id, message, cat):
    user = message.from_user
    mention = f'<a href="tg://user?id={user.id}">{_escape(user.first_name)}</a>'
    dev_id = list(developers_id)[0]
    line = get_lines()
    try:
        dev_user = bot.get_chat(dev_id)
        dev_name = f"{dev_user.first_name or ''} {dev_user.last_name or ''}".strip()
    except Exception:
        dev_name = "المطور"

    header = (
        f"تعال <a href='tg://user?id={dev_id}'><b>{dev_name}</b></a>\n"
        f"{line}\n"
        f"🎫 <b>تذكرة جديدة #{ticket_id}</b>\n"
        f"👤 المستخدم: {mention}\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📂 النوع: {CATEGORIES.get(cat, cat)}\n"
        f"{line}\n"
        f"📩 الرسالة:\n"
    )

    from utils.pagination import btn
    from utils.pagination.buttons import build_keyboard

    buttons = [
        btn("💬 رد", "ticket_dev_reply", data={"tid": ticket_id}, owner=None, color="su"),
        btn("🔒 إغلاق التذكرة", "ticket_close", data={"tid": ticket_id}, owner=None, color="d"),
    ]
    markup = build_keyboard(buttons, [2], None)

    return send_to_dev_group(
        header + _escape(message.text) + f"\n{line}",
        reply_markup=markup,
    )

# ══════════════════════════════════════════
# 💬 رد المطور
# ══════════════════════════════════════════

def handle_dev_reply(message):
    """
    يُستدعى عندما يرد مطور في مجموعة المطورين.
    يرجع True إذا تم التعامل مع الرسالة.
    """
    user_id = message.from_user.id
    chat_id = message.chat.id

    # فقط في مجموعة المطورين
    if chat_id != _get_dev_group_id():
        return False

    # فقط المطورون
    if not is_developer(user_id):
        return False

    ticket_id = None

    # طريقة 1: رد على رسالة التذكرة
    if message.reply_to_message:
        replied_msg_id = message.reply_to_message.message_id
        ticket = get_ticket_by_group_msg(replied_msg_id)
        if ticket:
            ticket_id = ticket["id"]

    # طريقة 2: حالة انتظار الرد
    if not ticket_id and user_id in _AWAITING_DEV_REPLY:
        ticket_id = _AWAITING_DEV_REPLY.pop(user_id)

    if not ticket_id:
        return False

    ticket = get_ticket(ticket_id)
    if not ticket:
        return False

    if ticket["status"] == "closed":
        bot.reply_to(message, "❌ هذه التذكرة مغلقة.")
        return True

    # رفض الملصقات
    if message.sticker:
        return False

    msg_type, content = _extract_message_info(message)
    add_ticket_message(ticket_id, "developer", message.message_id, msg_type, content)

    # إرسال الرد للمستخدم
    _send_dev_reply_to_user(ticket, message, ticket_id)
    bot.reply_to(message, f"✅ تم إرسال ردك للمستخدم (تذكرة #{ticket_id})")
    return True

def _send_dev_reply_to_user(ticket, message, ticket_id):
    user_id = ticket["user_id"]
    dev = message.from_user
    mention = f'<a href="tg://user?id={dev.id}">{_escape(dev.first_name)}</a>'

    header = (
        f"💬 <b>رد المطور على تذكرتك #{ticket_id}</b>\n"
        f"👤 {mention}\n"
        f"{get_lines()}\n"
        f"✉️ الرد:\n"
    )

    try:
        if message.text:
            bot.send_message(
                user_id,
                header + _escape(message.text) + "\n{get_lines()}",
                parse_mode="HTML"
            )

    except Exception as e:
        print(f"[Tickets] خطأ في إرسال الرد للمستخدم: {e}")


# ══════════════════════════════════════════
# 👤 رد المستخدم على تذكرة مفتوحة
# ══════════════════════════════════════════

def handle_user_followup(message):
    """
    يُستدعى عندما يرسل المستخدم رسالة متابعة لتذكرة مفتوحة.
    يرجع True إذا تم التعامل مع الرسالة.
    """
    user_id = message.from_user.id

    # لا نعالج رسائل المجموعة هنا
    if message.chat.type != "private":
        return False

    ticket = get_open_ticket_for_user(user_id)
    if not ticket:
        return False

    # رفض الملصقات
    if message.sticker:
        return False

    ticket_id = ticket["id"]
    msg_type, content = _extract_message_info(message)
    add_ticket_message(ticket_id, "user", message.message_id, msg_type, content)

    # إعادة توجيه للمجموعة
    _forward_user_reply_to_devs(ticket, message, ticket_id)

    from core.personality import send_with_delay
    send_with_delay(
        message.chat.id,
        f"📨 تم إرسال رسالتك للمطور (تذكرة #{ticket_id}) ✅",
        delay=0.4,
        reply_to=message.message_id
    )
    return True

def _forward_user_reply_to_devs(ticket, message, ticket_id):
    user = message.from_user
    mention = f'<a href="tg://user?id={user.id}">{_escape(user.first_name)}</a>'

    header = (
        f"🎫 <b>رد على التذكرة #{ticket_id}</b>\n"
        f"👤 المستخدم: {mention}\n"
        f"{get_lines()}\n"
        f"📩 الرسالة:\n"
    )

    from utils.pagination import btn
    from utils.pagination.buttons import build_keyboard

    buttons = [
        btn("💬 رد", "ticket_dev_reply", data={"tid": ticket_id}, owner=None, color="su"),
        btn("🔒 إغلاق التذكرة", "ticket_close", data={"tid": ticket_id}, owner=None, color="d"),
    ]
    markup = build_keyboard(buttons, [2], None)

    if message.text:
        send_to_dev_group(
            header + _escape(message.text) + f"\n{get_lines()}",
            reply_markup=markup,
        )


# ══════════════════════════════════════════
# 🔒 إغلاق التذكرة
# ══════════════════════════════════════════

def close_ticket_action(ticket_id, closer_user_id):
    """يغلق التذكرة ويُشعر المستخدم"""
    if not is_developer(closer_user_id):
        return False, "❌ فقط المطورون يمكنهم إغلاق التذاكر."

    ticket = get_ticket(ticket_id)
    if not ticket:
        return False, "❌ التذكرة غير موجودة."
    if ticket["status"] == "closed":
        return False, "❌ التذكرة مغلقة بالفعل."

    close_ticket(ticket_id)

    # إشعار المستخدم مع شخصية البوت
    try:
        from core.personality import send_with_delay
        send_with_delay(
            ticket["user_id"],
            f"🔒 <b>تم إغلاق التذكرة #{ticket_id}</b>\n\n"
            f"شكراً لتواصلك معنا. نتمنى أن نكون قد أفدناك 🙆‍♂",
            delay=0.5
        )
    except Exception:
        pass

    return True, f"✅ تم إغلاق التذكرة #{ticket_id}"


# ══════════════════════════════════════════
# 🔧 مساعدات
# ══════════════════════════════════════════

def set_awaiting_dev_reply(user_id, ticket_id):
    _AWAITING_DEV_REPLY[user_id] = ticket_id


def _extract_message_info(message):
    if message.text:
        return "text", message.text[:500]
    return None, None

def _escape(text):
    if not text:
        return ""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))
