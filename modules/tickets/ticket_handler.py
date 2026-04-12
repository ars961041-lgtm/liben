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
    is_ticket_banned,
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
# ─── رسائل معلقة بانتظار تأكيد الإرسال ───
# user_id → {"message": msg_obj, "cat": str, "chat_id": int}
_PENDING_CONFIRM: dict[int, dict] = {}


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

    # فحص الحظر
    if is_ticket_banned(user_id):
        bot.reply_to(message,
                     "🚫 <b>تم تقييد وصولك لنظام التذاكر</b>\n\n"
                     "لا يمكنك إرسال تقارير في الوقت الحالي.\n"
                     "إذا كنت تعتقد أن هذا خطأ، تواصل مع المشرف.",
                     parse_mode="HTML")
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
            f"✏️ أرسل رسالتك الآن (نص، صورة، أو فيديو):",
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
    يقبل نصاً أو صورة أو فيديو — يعرض تأكيداً قبل الإرسال.
    يرجع True إذا تم التعامل مع الرسالة.
    """
    from utils.pagination.router import get_state, clear_state

    user_id = message.from_user.id
    chat_id = message.chat.id

    state = get_state(user_id, chat_id)
    if state.get("state") != "awaiting_ticket_msg":
        return False

    # رفض الأنواع غير المدعومة
    if _is_unsupported_media(message):
        bot.reply_to(message,
                     "❌ <b>نوع الرسالة غير مدعوم</b>\n\n"
                     "يمكنك إرسال: نص، صورة، أو فيديو فقط.",
                     parse_mode="HTML")
        return True

    # التحقق من طول التعليق للوسائط (حد Telegram: 1024 حرف)
    if (message.photo or message.video) and message.caption:
        if len(message.caption) > 1024:
            bot.reply_to(message,
                         "❌ <b>التعليق طويل جداً</b>\n\n"
                         f"الحد الأقصى هو <b>1024 حرف</b>، وتعليقك يحتوي على <b>{len(message.caption)}</b> حرف.\n\n"
                         "✏️ أرسل الصورة/الفيديو مجدداً مع تعليق أقصر.",
                         parse_mode="HTML")
            return True

    cat = state["data"].get("cat", "bug")
    clear_state(user_id, chat_id)

    # حفظ الرسالة معلقة وعرض التأكيد
    _PENDING_CONFIRM[user_id] = {
        "message": message,
        "cat":     cat,
        "chat_id": chat_id,
    }
    _show_confirm_ui(user_id, chat_id, message, cat)
    return True


def _show_confirm_ui(user_id, chat_id, message, cat):
    """يعرض رسالة التأكيد مع زر الإرسال والإلغاء."""
    from utils.pagination import btn, send_ui

    # ملخص المحتوى
    if message.photo:
        content_preview = f"🖼 صورة" + (f" — {message.caption[:60]}..." if message.caption and len(message.caption) > 60
                                         else f" — {message.caption}" if message.caption else "")
    elif message.video:
        content_preview = f"🎥 فيديو" + (f" — {message.caption[:60]}..." if message.caption and len(message.caption) > 60
                                          else f" — {message.caption}" if message.caption else "")
    else:
        text_preview = (message.text[:80] + "...") if len(message.text) > 80 else message.text
        content_preview = f"💬 {text_preview}"

    text = (
        f"📋 <b>مراجعة التذكرة قبل الإرسال</b>\n\n"
        f"📂 النوع: {CATEGORIES[cat]}\n"
        f"📩 المحتوى: {_escape(content_preview)}\n\n"
        f"هل تريد إرسال هذه التذكرة للمطور؟"
    )
    buttons = [
        btn("✅ إرسال", "ticket_confirm_send", data={}, owner=(user_id, chat_id), color="su"),
        btn("❌ إلغاء",  "ticket_cancel_send",  data={}, owner=(user_id, chat_id), color="d"),
    ]
    send_ui(chat_id, text=text, buttons=buttons, layout=[2], owner_id=user_id)


def confirm_and_send_ticket(user_id, chat_id):
    """
    يُستدعى عند ضغط زر 'تأكيد الإرسال'.
    يُنشئ التذكرة ويرسلها للمجموعة ويُشعر المستخدم.
    يرجع (True, ticket_id) أو (False, None).
    """
    pending = _PENDING_CONFIRM.pop(user_id, None)
    if not pending:
        return False, None

    message = pending["message"]
    cat     = pending["cat"]

    ticket_id = create_ticket(user_id, chat_id, cat)
    record_ticket_usage(user_id)

    msg_type, content, file_id, file_unique_id = _extract_message_info(message)
    add_ticket_message(ticket_id, "user", message.message_id,
                       msg_type, content, file_id, file_unique_id)

    group_msg_id = send_to_devs(ticket_id, message, cat)
    if group_msg_id:
        set_ticket_group_msg(ticket_id, group_msg_id)

    from core import memory as _mem
    _mem.increment_daily_reports(user_id)

    return True, ticket_id


def cancel_pending_ticket(user_id):
    """يُلغي التذكرة المعلقة دون احتسابها."""
    _PENDING_CONFIRM.pop(user_id, None)


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
        btn("💬 رد",            "ticket_dev_reply", data={"tid": ticket_id},            owner=None, color="su"),
        btn("🔒 إغلاق التذكرة", "ticket_close",     data={"tid": ticket_id},            owner=None, color="d"),
        btn("🚫 حظر المستخدم",  "ticket_ban_user",  data={"uid": message.from_user.id}, owner=None, color="d"),
    ]
    markup = build_keyboard(buttons, [2, 1], None)

    dev_group_id = _get_dev_group_id()

    # صورة
    if message.photo:
        file_id = message.photo[-1].file_id
        caption_text = header + (_escape(message.caption) if message.caption else "") + f"\n{line}"
        try:
            sent = bot.send_photo(dev_group_id, file_id,
                                  caption=caption_text, parse_mode="HTML",
                                  reply_markup=markup)
            return sent.message_id
        except Exception as e:
            print(f"[Tickets] خطأ إرسال صورة للمجموعة: {e}")
            return None

    # فيديو
    if message.video:
        file_id = message.video.file_id
        caption_text = header + (_escape(message.caption) if message.caption else "") + f"\n{line}"
        try:
            sent = bot.send_video(dev_group_id, file_id,
                                  caption=caption_text, parse_mode="HTML",
                                  reply_markup=markup)
            return sent.message_id
        except Exception as e:
            print(f"[Tickets] خطأ إرسال فيديو للمجموعة: {e}")
            return None

    # نص
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

    # رفض الأنواع غير المدعومة
    if _is_unsupported_media(message):
        return False

    msg_type, content, file_id, file_unique_id = _extract_message_info(message)
    add_ticket_message(ticket_id, "developer", message.message_id,
                       msg_type, content, file_id, file_unique_id)

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
        if message.photo:
            file_id = message.photo[-1].file_id
            caption_text = header + (_escape(message.caption) if message.caption else "") + f"\n{get_lines()}"
            bot.send_photo(user_id, file_id, caption=caption_text, parse_mode="HTML")
        elif message.video:
            file_id = message.video.file_id
            caption_text = header + (_escape(message.caption) if message.caption else "") + f"\n{get_lines()}"
            bot.send_video(user_id, file_id, caption=caption_text, parse_mode="HTML")
        elif message.text:
            bot.send_message(
                user_id,
                header + _escape(message.text) + f"\n{get_lines()}",
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

    # رفض الأنواع غير المدعومة
    if _is_unsupported_media(message):
        return False

    ticket_id = ticket["id"]
    msg_type, content, file_id, file_unique_id = _extract_message_info(message)
    add_ticket_message(ticket_id, "user", message.message_id,
                       msg_type, content, file_id, file_unique_id)

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
        btn("💬 رد",            "ticket_dev_reply", data={"tid": ticket_id},            owner=None, color="su"),
        btn("🔒 إغلاق التذكرة", "ticket_close",     data={"tid": ticket_id},            owner=None, color="d"),
        btn("🚫 حظر المستخدم",  "ticket_ban_user",  data={"uid": ticket["user_id"]},    owner=None, color="d"),
    ]
    markup = build_keyboard(buttons, [2, 1], None)

    dev_group_id = _get_dev_group_id()

    if message.photo:
        file_id = message.photo[-1].file_id
        caption_text = header + (_escape(message.caption) if message.caption else "") + f"\n{get_lines()}"
        try:
            bot.send_photo(dev_group_id, file_id, caption=caption_text,
                           parse_mode="HTML", reply_markup=markup)
        except Exception as e:
            print(f"[Tickets] خطأ إعادة توجيه صورة: {e}")
    elif message.video:
        file_id = message.video.file_id
        caption_text = header + (_escape(message.caption) if message.caption else "") + f"\n{get_lines()}"
        try:
            bot.send_video(dev_group_id, file_id, caption=caption_text,
                           parse_mode="HTML", reply_markup=markup)
        except Exception as e:
            print(f"[Tickets] خطأ إعادة توجيه فيديو: {e}")
    elif message.text:
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
    """يستخرج (msg_type, content, file_id, file_unique_id) من الرسالة."""
    if message.photo:
        photo = message.photo[-1]
        return "photo", message.caption, photo.file_id, photo.file_unique_id
    if message.video:
        return "video", message.caption, message.video.file_id, message.video.file_unique_id
    if message.text:
        return "text", message.text[:500], None, None
    return "unknown", None, None, None


def _is_unsupported_media(message):
    """يرجع True إذا كانت الرسالة من نوع غير مدعوم (ملصق، صوت، إلخ)."""
    return bool(
        message.sticker or message.audio or message.voice or
        message.video_note or message.document or message.animation
    )

def _escape(text):
    if not text:
        return ""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))
