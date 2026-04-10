"""
معالج أزرار التذاكر — callbacks + لوحة التحكم
"""
from core.bot import bot
from utils.pagination import btn, send_ui, edit_ui, register_action, paginate_list, grid
from modules.tickets.ticket_db import (
    get_ticket, get_tickets_paginated, count_tickets,
    get_ticket_messages, get_stats,
    get_user_tickets, count_user_tickets,
)
from modules.tickets.ticket_handler import (
    CATEGORIES, DEVELOPERS, _get_dev_group_id,
    is_developer, close_ticket_action,
    handle_category_selection, set_awaiting_dev_reply,
    _escape,
)
import time as _time
from utils.helpers import get_lines


# ══════════════════════════════════════════
# 🎫 اختيار الفئة
# ══════════════════════════════════════════

@register_action("ticket_cat")
def on_ticket_category(call, data):
    handle_category_selection(call, data)


# ══════════════════════════════════════════
# 💬 زر رد المطور
# ══════════════════════════════════════════

@register_action("ticket_dev_reply")
def on_dev_reply_btn(call, data):
    user_id   = call.from_user.id
    ticket_id = int(data["tid"])

    if not is_developer(user_id):
        bot.answer_callback_query(call.id, "❌ فقط المطورون يمكنهم الرد.", show_alert=True)
        return

    ticket = get_ticket(ticket_id)
    if not ticket:
        bot.answer_callback_query(call.id, "❌ التذكرة غير موجودة.", show_alert=True)
        return
    if ticket["status"] == "closed":
        bot.answer_callback_query(call.id, "❌ التذكرة مغلقة.", show_alert=True)
        return

    set_awaiting_dev_reply(user_id, ticket_id)
    bot.answer_callback_query(call.id,
                              f"✏️ أرسل ردك الآن على التذكرة #{ticket_id}",
                              show_alert=True)


# ══════════════════════════════════════════
# 🔒 إغلاق التذكرة
# ══════════════════════════════════════════

@register_action("ticket_close")
def on_ticket_close(call, data):
    user_id   = call.from_user.id
    ticket_id = int(data["tid"])

    ok, msg = close_ticket_action(ticket_id, user_id)
    bot.answer_callback_query(call.id, msg, show_alert=True)

    if ok:
        try:
            bot.edit_message_reply_markup(
                call.message.chat.id,
                call.message.message_id,
                reply_markup=None
            )
            # إضافة علامة الإغلاق على الرسالة
            original = call.message.text or call.message.caption or ""
            closed_note = f"\n\n🔒 <b>مغلقة</b>"
            try:
                if call.message.text:
                    bot.edit_message_text(
                        original + closed_note,
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode="HTML"
                    )
            except Exception:
                pass
        except Exception:
            pass


# ══════════════════════════════════════════
# 📊 لوحة التحكم
# ══════════════════════════════════════════

def open_admin_panel(message):
    """يفتح لوحة التحكم — للمطورين فقط"""
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not is_developer(user_id):
        bot.reply_to(message, "❌ هذا الأمر للمطورين فقط.")
        return

    _send_admin_panel(chat_id, user_id)


def _send_admin_panel(chat_id, user_id):
    stats = get_stats()
    text = (
        f"📊 <b>لوحة التحكم — نظام التذاكر</b>\n"
        f"{get_lines()}\n"
        f"📬 مفتوحة: {stats['open']}\n"
        f"📁 مغلقة: {stats['closed']}\n"
        f"📅 اليوم: {stats['today']}\n"
        f"📊 الإجمالي: {stats['total']}\n"
        f"{get_lines()}"
    )
    buttons = [
        btn("📬 التذاكر المفتوحة", "ticket_list", data={"status": "open",   "page": 0}, owner=(user_id, chat_id), color="su"),
        btn("📁 جميع التذاكر",     "ticket_list", data={"status": "all",    "page": 0}, owner=(user_id, chat_id)),
        btn("📊 إحصائيات",         "ticket_stats", data={},                             owner=(user_id, chat_id), color="p"),
    ]
    send_ui(chat_id, text=text, buttons=buttons, layout=[1, 1, 1], owner_id=user_id)


@register_action("ticket_stats")
def on_ticket_stats(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if not is_developer(user_id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return

    stats = get_stats()
    text = (
        f"📊 <b>إحصائيات التذاكر</b>\n"
        f"{get_lines()}\n"
        f"📅 تذاكر اليوم: <b>{stats['today']}</b>\n"
        f"📬 مفتوحة: <b>{stats['open']}</b>\n"
        f"📁 مغلقة: <b>{stats['closed']}</b>\n"
        f"📊 الإجمالي: <b>{stats['total']}</b>\n"
        f"{get_lines()}"
    )
    edit_ui(call, text=text,
            buttons=[btn("🔙 رجوع", "ticket_admin_back", data={}, owner=(user_id, chat_id))],
            layout=[1])


@register_action("ticket_admin_back")
def on_admin_back(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    if not is_developer(user_id):
        return
    stats = get_stats()
    text = (
        f"📊 <b>لوحة التحكم — نظام التذاكر</b>\n"
        f"{get_lines()}\n"
        f"📬 مفتوحة: {stats['open']}\n"
        f"📁 مغلقة: {stats['closed']}\n"
        f"📅 اليوم: {stats['today']}\n"
        f"📊 الإجمالي: {stats['total']}\n"
        f"{get_lines()}"
    )
    buttons = [
        btn("📬 التذاكر المفتوحة", "ticket_list", data={"status": "open", "page": 0}, owner=(user_id, chat_id), color="su"),
        btn("📁 جميع التذاكر",     "ticket_list", data={"status": "all",  "page": 0}, owner=(user_id, chat_id)),
        btn("📊 إحصائيات",         "ticket_stats", data={},                           owner=(user_id, chat_id), color="p"),
    ]
    edit_ui(call, text=text, buttons=buttons, layout=[1, 1, 1])


# ══════════════════════════════════════════
# 📋 قائمة التذاكر مع pagination
# ══════════════════════════════════════════

@register_action("ticket_list")
def on_ticket_list(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if not is_developer(user_id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return

    status = data.get("status", "all")
    page   = int(data.get("page", 0))
    per_page = 10

    status_filter = None if status == "all" else status
    tickets = get_tickets_paginated(status_filter, page, per_page)
    total   = count_tickets(status_filter)
    total_pages = max(1, (total + per_page - 1) // per_page)

    if not tickets:
        edit_ui(call,
                text="📭 لا توجد تذاكر.",
                buttons=[btn("🔙 رجوع", "ticket_admin_back", data={}, owner=(user_id, chat_id))],
                layout=[1])
        return

    status_label = "المفتوحة" if status == "open" else "الكل"
    text = f"🎫 <b>التذاكر — {status_label}</b> (صفحة {page+1}/{total_pages})\n{get_lines()}\n\n"

    buttons = []
    for t in tickets:
        status_icon = "📬" if t["status"] == "open" else "📁"
        cat_label   = CATEGORIES.get(t["category"], t["category"])
        text += f"{status_icon} <b>#{t['id']}</b> | {cat_label} | ID: {t['user_id']}\n"
        buttons.append(
            btn(f"{status_icon} #{t['id']} — {cat_label}",
                "ticket_view",
                data={"tid": t["id"], "back_status": status, "back_page": page},
                owner=(user_id, chat_id))
        )

    nav = []
    if page < total_pages - 1:
        nav.append(btn("التالي ◀️", "ticket_list",
                       data={"status": status, "page": page + 1}, owner=(user_id, chat_id)))
    if page > 0:
        nav.append(btn("▶️ السابق", "ticket_list",
                       data={"status": status, "page": page - 1}, owner=(user_id, chat_id)))
    nav.append(btn("🔙 رجوع", "ticket_admin_back", data={}, owner=(user_id, chat_id)))

    layout = [1] * len(buttons) + [len(nav)]
    edit_ui(call, text=text, buttons=buttons + nav, layout=layout)


# ══════════════════════════════════════════
# 🔍 عرض تذكرة واحدة
# ══════════════════════════════════════════

@register_action("ticket_view")
def on_ticket_view(call, data):
    user_id   = call.from_user.id
    chat_id   = call.message.chat.id
    ticket_id = int(data["tid"])
    back_status = data.get("back_status", "all")
    back_page   = int(data.get("back_page", 0))

    if not is_developer(user_id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return

    ticket = get_ticket(ticket_id)
    if not ticket:
        bot.answer_callback_query(call.id, "❌ التذكرة غير موجودة", show_alert=True)
        return

    messages = get_ticket_messages(ticket_id, limit=15)
    cat_label    = CATEGORIES.get(ticket["category"], ticket["category"])
    status_label = "📬 مفتوحة" if ticket["status"] == "open" else "📁 مغلقة"
    created      = _time.strftime("%Y-%m-%d %H:%M", _time.localtime(ticket["created_at"]))

    text = (
        f"🎫 <b>تذكرة #{ticket_id}</b>\n"
        f"{get_lines()}\n"
        f"👤 المستخدم: <code>{ticket['user_id']}</code>\n"
        f"📂 النوع: {cat_label}\n"
        f"📊 الحالة: {status_label}\n"
        f"📅 التاريخ: {created}\n"
        f"{get_lines()}\n\n"
        f"💬 <b>المحادثة ({len(messages)} رسالة):</b>\n\n"
    )

    for msg in messages[-10:]:  # آخر 10 رسائل
        sender_label = "👤 المستخدم" if msg["sender"] == "user" else "👨‍💻 المطور"
        msg_time = _time.strftime("%H:%M", _time.localtime(msg["created_at"]))
        content  = _escape(msg["content"] or f"[{msg['message_type']}]")
        text += f"<b>{sender_label}</b> [{msg_time}]:\n{content}\n\n"

    buttons = []
    if ticket["status"] == "open":
        buttons.append(btn("💬 رد", "ticket_dev_reply",
                           data={"tid": ticket_id}, owner=(user_id, chat_id), color="su"))
        buttons.append(btn("🔒 إغلاق", "ticket_close_from_view",
                           data={"tid": ticket_id, "back_status": back_status, "back_page": back_page},
                           owner=(user_id, chat_id), color="d"))
    buttons.append(btn("🔙 رجوع", "ticket_list",
                       data={"status": back_status, "page": back_page},
                       owner=(user_id, chat_id)))

    layout = [2, 1] if len(buttons) == 3 else [1, 1]
    edit_ui(call, text=text, buttons=buttons, layout=layout)


@register_action("ticket_close_from_view")
def on_close_from_view(call, data):
    user_id     = call.from_user.id
    ticket_id   = int(data["tid"])
    back_status = data.get("back_status", "all")
    back_page   = int(data.get("back_page", 0))

    ok, msg = close_ticket_action(ticket_id, user_id)
    bot.answer_callback_query(call.id, msg, show_alert=True)

    if ok:
        # تحديث العرض
        on_ticket_view(call, {"tid": ticket_id, "back_status": back_status, "back_page": back_page})


# ══════════════════════════════════════════
# 📋 تذاكري — عرض تذاكر المستخدم
# ══════════════════════════════════════════

_PER_PAGE = 5

def show_my_tickets(message):
    """نقطة الدخول النصية لأمر تذاكري."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    owner   = (user_id, chat_id)

    tickets = get_user_tickets(user_id, page=0, per_page=_PER_PAGE)
    total   = count_user_tickets(user_id)

    text, buttons, layout = _build_my_tickets_view(user_id, chat_id, tickets, total, page=0)
    send_ui(chat_id, text=text, buttons=buttons, layout=layout,
            owner_id=user_id, reply_to=message.message_id)


def _build_my_tickets_view(user_id, chat_id, tickets, total, page):
    owner       = (user_id, chat_id)
    total_pages = max(1, (total + _PER_PAGE - 1) // _PER_PAGE)

    if not tickets:
        text = (
            f"🎫 <b>تذاكري</b>\n{get_lines()}\n\n"
            "📭 لا توجد تذاكر مسجلة بعد.\n\n"
            "اكتب <code>تذكرة</code> لفتح تذكرة دعم جديدة."
        )
        return text, [], []

    text = (
        f"🎫 <b>تذاكري</b> (صفحة {page+1}/{total_pages})\n"
        f"{get_lines()}\n\n"
    )
    buttons = []
    for t in tickets:
        status_icon = "📬" if t["status"] == "open" else "📁"
        cat_label   = CATEGORIES.get(t["category"], t["category"])
        created     = _time.strftime("%Y-%m-%d", _time.localtime(t["created_at"]))
        text += f"{status_icon} <b>#{t['id']}</b> | {cat_label} | {created}\n"
        buttons.append(
            btn(f"{status_icon} #{t['id']} — {cat_label}",
                "my_ticket_view",
                data={"tid": t["id"], "page": page},
                owner=owner)
        )

    nav = []
    if page < total_pages - 1:
        nav.append(btn("التالي ◀️", "my_tickets_page",
                       data={"page": page + 1}, owner=owner))
    if page > 0:
        nav.append(btn("▶️ السابق", "my_tickets_page",
                       data={"page": page - 1}, owner=owner))

    layout = [1] * len(buttons) + ([len(nav)] if nav else [])
    return text, buttons + nav, layout


@register_action("my_tickets_page")
def on_my_tickets_page(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    page    = int(data.get("page", 0))

    tickets = get_user_tickets(user_id, page=page, per_page=_PER_PAGE)
    total   = count_user_tickets(user_id)
    text, buttons, layout = _build_my_tickets_view(user_id, chat_id, tickets, total, page)
    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons, layout=layout)


@register_action("my_ticket_view")
def on_my_ticket_view(call, data):
    user_id   = call.from_user.id
    chat_id   = call.message.chat.id
    ticket_id = int(data["tid"])
    back_page = int(data.get("page", 0))
    owner     = (user_id, chat_id)

    ticket = get_ticket(ticket_id)
    if not ticket:
        bot.answer_callback_query(call.id, "❌ التذكرة غير موجودة", show_alert=True)
        return

    # المستخدم يرى تذاكره فقط
    if ticket["user_id"] != user_id:
        bot.answer_callback_query(call.id, "❌ هذه التذكرة ليست لك", show_alert=True)
        return

    messages  = get_ticket_messages(ticket_id, limit=20)
    cat_label    = CATEGORIES.get(ticket["category"], ticket["category"])
    status_label = "📬 مفتوحة" if ticket["status"] == "open" else "📁 مغلقة"
    created      = _time.strftime("%Y-%m-%d %H:%M", _time.localtime(ticket["created_at"]))

    text = (
        f"🎫 <b>تذكرة #{ticket_id}</b>\n"
        f"{get_lines()}\n"
        f"📂 النوع: {cat_label}\n"
        f"📊 الحالة: {status_label}\n"
        f"📅 التاريخ: {created}\n"
        f"{get_lines()}\n\n"
        f"💬 <b>المحادثة ({len(messages)} رسالة):</b>\n\n"
    )

    for msg in messages[-10:]:
        sender_label = "👤 أنت" if msg["sender"] == "user" else "👨‍💻 المطور"
        msg_time = _time.strftime("%H:%M", _time.localtime(msg["created_at"]))
        content  = _escape(msg["content"] or f"[{msg['message_type']}]")
        text += f"<b>{sender_label}</b> [{msg_time}]:\n{content}\n\n"

    buttons = [
        btn("🔙 رجوع", "my_tickets_page", data={"page": back_page}, owner=owner)
    ]
    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons, layout=[1])


# ══════════════════════════════════════════
# 📝 أوامر نصية للتذاكر
# ══════════════════════════════════════════

def handle_ticket_commands(message):
    """
    يعالج الأوامر النصية المتعلقة بالتذاكر.
    يرجع True إذا تم التعامل مع الرسالة.
    """
    if not message.text:
        return False

    text       = message.text.strip()
    normalized = text.lower()
    user_id    = message.from_user.id
    chat_id    = message.chat.id

    # ─── إبلاغ المطور ───
    if normalized in ["إبلاغ المطور", "ابلاغ المطور", "تذكرة", "بلاغ"]:
        from modules.tickets.ticket_handler import start_ticket_flow
        start_ticket_flow(message)
        return True

    # ─── تذاكري ───
    if normalized in ["تذاكري", "تذاكر المستخدم"]:
        show_my_tickets(message)
        return True

    # ─── لوحة التحكم ───
    if normalized in ["لوحة التذاكر", "تذاكر", "/tickets"]:
        open_admin_panel(message)
        return True

    # ─── رد المطور في المجموعة ───
    if chat_id == _get_dev_group_id() and is_developer(user_id):
        from modules.tickets.ticket_handler import handle_dev_reply
        if handle_dev_reply(message):
            return True

    return False


def handle_ticket_media(message):
    """
    يعالج الرسائل غير النصية (صور، ملفات، إلخ).
    يرجع True إذا تم التعامل مع الرسالة.
    """
    user_id = message.from_user.id
    chat_id = message.chat.id

    # حالة انتظار رسالة التذكرة
    from utils.pagination.router import get_state
    state = get_state(user_id, chat_id)
    if state.get("state") == "awaiting_ticket_msg":
        from modules.tickets.ticket_handler import handle_ticket_message_input
        return handle_ticket_message_input(message)

    # رد المطور في المجموعة
    if chat_id == _get_dev_group_id() and is_developer(user_id):
        from modules.tickets.ticket_handler import handle_dev_reply
        if handle_dev_reply(message):
            return True

    # متابعة المستخدم في الخاص
    if message.chat.type == "private":
        from modules.tickets.ticket_handler import handle_user_followup
        if handle_user_followup(message):
            return True

    return False
