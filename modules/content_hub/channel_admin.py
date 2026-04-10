"""
واجهة إدارة ربط القنوات بمركز المحتوى.
أوامر: ربط قناة / فك ربط قناة / القنوات المرتبطة
"""
from core.bot import bot
from core.admin import is_any_dev
from core.state_manager import StateManager
from utils.pagination import btn, send_ui, edit_ui, register_action
from modules.content_hub.hub_db import (
    link_channel, unlink_channel, get_all_linked_channels, create_tables,
    TYPE_LABELS,
)

create_tables()

# نقشة أزرار اختيار نوع المحتوى
_TYPE_BUTTONS = [
    ("📜 اقتباسات", "quotes"),
    ("📖 قصص",      "stories"),
    ("😂 نوادر",    "anecdotes"),
    ("📝 حكمة",     "wisdom"),
    ("🎤 شعر",      "poetry"),
]


# ══════════════════════════════════════════
# أوامر النص
# ══════════════════════════════════════════

def handle_channel_admin_command(message) -> bool:
    text = (message.text or "").strip()
    uid  = message.from_user.id
    cid  = message.chat.id

    if not is_any_dev(uid):
        return False

    if text == "ربط قناة":
        _start_link_flow(message, uid, cid)
        return True

    if text == "فك ربط قناة":
        _show_unlink_list(message, uid, cid)
        return True

    if text == "القنوات المرتبطة":
        _show_linked_list(message, uid, cid)
        return True

    return False


def handle_channel_admin_input(message) -> bool:
    """يعالج إدخال معرف القناة أثناء تدفق الربط."""
    uid = message.from_user.id
    cid = message.chat.id

    state = StateManager.get(uid, cid)
    if not state or state.get("type") != "ch_link":
        return False

    step = state.get("step")

    if step == "await_channel":
        _process_channel_input(message, uid, cid, state)
        return True

    return False


# ══════════════════════════════════════════
# تدفق الربط
# ══════════════════════════════════════════

def _start_link_flow(message, uid: int, cid: int):
    StateManager.set(uid, cid, {
        "type": "ch_link",
        "step": "await_channel",
        "mid":  None,
    }, ttl=300)

    owner = (uid, cid)
    cancel = btn("🚫 إلغاء", "ch_cancel", {}, color="d", owner=owner)
    from utils.pagination.buttons import build_keyboard
    bot.reply_to(
        message,
        "📡 <b>ربط قناة بمركز المحتوى</b>\n\n"
        "أرسل <b>معرف القناة</b> (مثال: <code>-1001234567890</code>)\n"
        "أو <b>أعد توجيه</b> رسالة من القناة.",
        parse_mode="HTML",
        reply_markup=build_keyboard([cancel], [1], uid),
    )


def _process_channel_input(message, uid: int, cid: int, state: dict):
    channel_id = None
    channel_name = ""

    # رسالة معاد توجيهها من قناة
    if message.forward_from_chat and message.forward_from_chat.type == "channel":
        channel_id   = message.forward_from_chat.id
        channel_name = message.forward_from_chat.title or ""
    elif message.text:
        raw = message.text.strip()
        try:
            channel_id = int(raw)
        except ValueError:
            bot.reply_to(message, "❌ معرف غير صالح. أرسل رقماً مثل <code>-1001234567890</code>.",
                         parse_mode="HTML")
            return

    if not channel_id:
        bot.reply_to(message, "❌ لم أتمكن من تحديد القناة.")
        return

    # تحقق من أن البوت مشرف في القناة
    try:
        member = bot.get_chat_member(channel_id, bot.get_me().id)
        if member.status not in ("administrator", "creator"):
            bot.reply_to(message, "❌ البوت ليس مشرفاً في هذه القناة. أضفه كمشرف أولاً.")
            StateManager.clear(uid, cid)
            return
        if not channel_name:
            chat_info = bot.get_chat(channel_id)
            channel_name = chat_info.title or str(channel_id)
    except Exception:
        bot.reply_to(message, "❌ تعذّر الوصول للقناة. تأكد من أن البوت مشرف فيها.")
        StateManager.clear(uid, cid)
        return

    # حفظ channel_id في الحالة وعرض أزرار نوع المحتوى
    StateManager.update(uid, cid, {
        "step":         "await_type",
        "extra":        {"channel_id": channel_id, "channel_name": channel_name},
    })

    owner   = (uid, cid)
    buttons = [btn(label, "ch_select_type", {"type": t, "cid": channel_id, "name": channel_name},
                   owner=owner)
               for label, t in _TYPE_BUTTONS]
    buttons.append(btn("🚫 إلغاء", "ch_cancel", {}, color="d", owner=owner))

    from utils.pagination.buttons import build_keyboard
    bot.reply_to(
        message,
        f"📡 <b>{channel_name}</b>\n\n"
        "اختر نوع المحتوى الذي ستُرسله هذه القناة:",
        parse_mode="HTML",
        reply_markup=build_keyboard(buttons, [2, 2, 1, 1], uid),
    )


# ══════════════════════════════════════════
# عرض القنوات المرتبطة
# ══════════════════════════════════════════

def _show_linked_list(message, uid: int, cid: int):
    channels = get_all_linked_channels()
    if not channels:
        bot.reply_to(message, "📭 لا توجد قنوات مرتبطة حتى الآن.")
        return

    lines = ["📡 <b>القنوات المرتبطة:</b>\n"]
    for ch in channels:
        label = TYPE_LABELS.get(ch["content_type"], ch["content_type"])
        name  = ch["channel_name"] or str(ch["channel_id"])
        lines.append(f"• <b>{name}</b> — {label}\n  <code>{ch['channel_id']}</code>")

    bot.reply_to(message, "\n".join(lines), parse_mode="HTML")


def _show_unlink_list(message, uid: int, cid: int):
    channels = get_all_linked_channels()
    if not channels:
        bot.reply_to(message, "📭 لا توجد قنوات مرتبطة.")
        return

    owner   = (uid, cid)
    buttons = [
        btn(f"📡 {ch['channel_name'] or ch['channel_id']} ❌",
            "ch_unlink", {"channel_id": ch["channel_id"]}, color="d", owner=owner)
        for ch in channels
    ]
    buttons.append(btn("🚫 إلغاء", "ch_cancel", {}, color="su", owner=owner))

    send_ui(cid,
            text="🗑️ <b>اختر القناة لفك ربطها:</b>",
            buttons=buttons,
            layout=[1] * len(buttons),
            owner_id=uid,
            reply_to=message.message_id)


# ══════════════════════════════════════════
# Callbacks
# ══════════════════════════════════════════

@register_action("ch_select_type")
def on_select_type(call, data):
    uid          = call.from_user.id
    content_type = data.get("type")
    channel_id   = data.get("cid")
    channel_name = data.get("name", "")

    if not is_any_dev(uid):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط.", show_alert=True)
        return

    link_channel(channel_id, content_type, channel_name)
    StateManager.clear(uid, call.message.chat.id)

    label = TYPE_LABELS.get(content_type, content_type)
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=f"✅ <b>تم ربط القناة بنجاح!</b>\n\n"
                 f"📡 <b>{channel_name or channel_id}</b>\n"
                 f"📂 النوع: {label}",
            buttons=[btn("✅ إغلاق", "ch_cancel", {}, color="su", owner=(uid, call.message.chat.id))],
            layout=[1])


@register_action("ch_unlink")
def on_unlink(call, data):
    uid        = call.from_user.id
    channel_id = data.get("channel_id")

    if not is_any_dev(uid):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط.", show_alert=True)
        return

    ok = unlink_channel(channel_id)
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text="❌ <b>تم فك الربط بنجاح.</b>" if ok else "⚠️ القناة غير موجودة.",
            buttons=[btn("✅ إغلاق", "ch_cancel", {}, color="su", owner=(uid, call.message.chat.id))],
            layout=[1])


@register_action("ch_cancel")
def on_cancel(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    StateManager.clear(uid, cid)
    bot.answer_callback_query(call.id, "تم الإلغاء")
    try:
        bot.delete_message(cid, call.message.message_id)
    except Exception:
        pass
