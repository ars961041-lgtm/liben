"""
Callback handlers for the unified permissions panel.
"""
import time
from core.bot import bot
from utils.pagination.router import register_action
from utils.logger import log_event
from .perms_state import get_extra, set_extra, toggle_perm, set_step, get_step, clear
from .perms_ui import edit_ui, build_ui
from .perms_config import PRESETS, bot_can_manage_tags
from .perms_apply import apply_permissions
from utils.pagination.buttons import btn, build_keyboard


def _remove_buttons(call):
    try:
        bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id, reply_markup=None
        )
    except Exception:
        pass


def _edit_ui_with_warning(call, uid: int, cid: int, warning: str):
    """Edit the existing UI message with a warning — no new message sent."""
    result = build_ui(uid, cid)
    if not result:
        return
    text, markup = result
    text = f"⚠️ {warning}\n\n{text}"
    try:
        bot.edit_message_text(
            text, call.message.chat.id, call.message.message_id,
            parse_mode="HTML", disable_web_page_preview=True, reply_markup=markup,
        )
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            print(f"[perms_callbacks] warning edit error: {e}")


# ── No-op ─────────────────────────────────────────────────────────────────────

@register_action("pp_noop")
def on_noop(call, data: dict):
    bot.answer_callback_query(call.id)


# ── Toggle ────────────────────────────────────────────────────────────────────

@register_action("pp_toggle")
def on_toggle(call, data: dict):
    uid = call.from_user.id
    cid = call.message.chat.id

    extra = get_extra(uid, cid)
    if extra is None:
        bot.answer_callback_query(call.id, "⏳ انتهت الجلسة، أعد الأمر.", show_alert=True)
        return

    key  = data.get("k")
    page = data.get("pg", extra.get("page", 0))

    toggle_perm(uid, cid, key)
    set_extra(uid, cid, page=page)

    try:
        edit_ui(call, uid, cid)
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ {e}", show_alert=True)


# ── Paginate ──────────────────────────────────────────────────────────────────

@register_action("pp_page")
def on_page(call, data: dict):
    uid = call.from_user.id
    cid = call.message.chat.id

    extra = get_extra(uid, cid)
    if extra is None:
        bot.answer_callback_query(call.id, "⏳ انتهت الجلسة، أعد الأمر.", show_alert=True)
        return

    set_extra(uid, cid, page=data.get("pg", 0))
    try:
        edit_ui(call, uid, cid)
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ {e}", show_alert=True)


# ── Preset ────────────────────────────────────────────────────────────────────

@register_action("pp_preset")
def on_preset(call, data: dict):
    uid = call.from_user.id
    cid = call.message.chat.id

    extra = get_extra(uid, cid)
    if extra is None:
        bot.answer_callback_query(call.id, "⏳ انتهت الجلسة، أعد الأمر.", show_alert=True)
        return

    preset = PRESETS.get(data.get("p"))
    if not preset:
        bot.answer_callback_query(call.id, "❌ إعداد غير معروف.", show_alert=True)
        return

    # Merge — only overwrite keys defined in preset
    current = dict(extra.get("promote", {}))
    current.update(preset["promote"])
    set_extra(uid, cid, promote=current)

    try:
        edit_ui(call, uid, cid)
        bot.answer_callback_query(call.id, f"✅ {preset['label']}")
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ {e}", show_alert=True)


# ── Title ─────────────────────────────────────────────────────────────────────

@register_action("pp_title")
def on_title(call, data: dict):
    uid = call.from_user.id
    cid = call.message.chat.id

    extra = get_extra(uid, cid)
    if extra is None:
        bot.answer_callback_query(call.id, "⏳ انتهت الجلسة، أعد الأمر.", show_alert=True)
        return

    if not bot_can_manage_tags(cid):
        _edit_ui_with_warning(call, uid, cid, "البوت لا يملك صلاحية تعديل الوسوم")
        bot.answer_callback_query(call.id, "❌ البوت لا يملك صلاحية تعديل الوسوم",
                                  show_alert=True)
        return

    set_step(uid, cid, "await_title")
    set_extra(uid, cid, mid=call.message.message_id)
    bot.answer_callback_query(call.id)
    bot.send_message(
        cid,
        "✏️ أرسل اللقب المخصص (أو <code>-</code> لإلغاء اللقب):",
        parse_mode="HTML",
    )


# ── Cancel ────────────────────────────────────────────────────────────────────

@register_action("pp_cancel")
def on_cancel(call, data: dict):
    uid = call.from_user.id
    cid = call.message.chat.id
    clear(uid, cid)
    _remove_buttons(call)
    bot.answer_callback_query(call.id, "❌ تم الإلغاء")
    log_event("perms_panel_cancelled", user=uid, chat=cid)


# ── Apply ─────────────────────────────────────────────────────────────────────

@register_action("pp_apply")
def on_apply(call, data: dict):
    uid = call.from_user.id
    cid = call.message.chat.id

    extra = get_extra(uid, cid)
    if extra is None:
        bot.answer_callback_query(call.id, "⏳ انتهت الجلسة، أعد الأمر.", show_alert=True)
        return

    target_uid  = extra["target_uid"]
    target_name = extra["target_name"]
    promote     = extra.get("promote", {})
    title       = extra.get("title",   "")

    bot.answer_callback_query(call.id, "⏳ جاري التطبيق...")

    ok, err_msg = apply_permissions(cid, target_uid, promote)

    # Always attempt title — catch gracefully
    title_ok = True
    if any(promote.values()) and title:
        try:
            bot.set_chat_administrator_custom_title(cid, target_uid, title)
        except Exception as e:
            print(f"[perms_callbacks] title error: {e}")
            title_ok = False

    _remove_buttons(call)
    clear(uid, cid)

    user_link     = f"<a href='tg://user?id={target_uid}'>{target_name}</a>"
    executor_link = f"<a href='tg://user?id={uid}'>{call.from_user.first_name}</a>"

    if ok:
        title_line = ""
        if title and any(promote.values()):
            title_line = (f"🏷 اللقب: <b>{title}</b>\n" if title_ok
                          else "❌ البوت لا يملك صلاحية إضافة اللقب\n")
        summary = (
            f"🔧 <b>تم تطبيق الصلاحيات</b>\n"
            f"👤 المستخدم: {user_link}\n"
            f"👮 بواسطة: {executor_link}\n"
            f"{title_line}"
            f"🕒 {time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    else:
        summary = (
            f"{err_msg or '❌ فشل تطبيق الصلاحيات'}\n"
            f"👤 {user_link}"
        )

    bot.send_message(cid, summary, parse_mode="HTML", disable_web_page_preview=True)
    log_event("perms_panel_applied", executor=uid, target=target_uid, ok=ok, chat=cid)
