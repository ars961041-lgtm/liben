"""
All @register_action callback handlers for the promote flow.
Registered at import time — import this module in promote_handler.py.
"""
import time
from core.bot import bot
from utils.pagination.router import register_action
from utils.logger import log_event
from .promote_state import (
    get_promote_extra, set_promote_extra, toggle_perm,
    set_step, clear_state, PERMISSIONS,
)
from .promote_ui import edit_promote_ui


# ── helpers ──────────────────────────────────────────────────────────────────

def _remove_buttons(call):
    try:
        bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id, reply_markup=None
        )
    except Exception:
        pass


def _build_perms_kwargs(perms: dict) -> dict:
    """Convert our perms dict to telebot promote kwargs."""
    return {k: v for k, v in perms.items()}


# ── Toggle a permission ───────────────────────────────────────────────────────

@register_action("prm_toggle")
def on_toggle(call, data: dict):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    perm = data.get("perm")
    page = data.get("page", 0)

    extra = get_promote_extra(uid, cid)
    if extra is None:
        bot.answer_callback_query(call.id, "⏳ انتهت الجلسة، أعد الأمر.", show_alert=True)
        return

    toggle_perm(uid, cid, perm)
    log_event("promote_toggle", user=uid, perm=perm)

    try:
        edit_promote_ui(call, uid, cid, page=page)
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ {e}", show_alert=True)


# ── Paginate ──────────────────────────────────────────────────────────────────

@register_action("prm_page")
def on_page(call, data: dict):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    page = data.get("page", 0)

    extra = get_promote_extra(uid, cid)
    if extra is None:
        bot.answer_callback_query(call.id, "⏳ انتهت الجلسة، أعد الأمر.", show_alert=True)
        return

    try:
        edit_promote_ui(call, uid, cid, page=page)
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ {e}", show_alert=True)


# ── Set title ─────────────────────────────────────────────────────────────────

@register_action("prm_set_title")
def on_set_title(call, data: dict):
    uid = call.from_user.id
    cid = call.message.chat.id

    extra = get_promote_extra(uid, cid)
    if extra is None:
        bot.answer_callback_query(call.id, "⏳ انتهت الجلسة، أعد الأمر.", show_alert=True)
        return

    set_step(uid, cid, "await_title")
    set_promote_extra(uid, cid, mid=call.message.message_id, page=data.get("page", 0))

    bot.answer_callback_query(call.id)
    bot.send_message(
        cid,
        "✏️ أرسل اللقب المخصص للمشرف (أو أرسل <code>-</code> لإلغاء اللقب):",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


# ── Cancel ────────────────────────────────────────────────────────────────────

@register_action("prm_cancel")
def on_cancel(call, data: dict):
    uid = call.from_user.id
    cid = call.message.chat.id

    clear_state(uid, cid)
    _remove_buttons(call)
    bot.answer_callback_query(call.id, "❌ تم الإلغاء")
    log_event("promote_cancelled", user=uid, chat=cid)


# ── Assign ────────────────────────────────────────────────────────────────────

@register_action("prm_assign")
def on_assign(call, data: dict):
    uid = call.from_user.id
    cid = call.message.chat.id

    extra = get_promote_extra(uid, cid)
    if extra is None:
        bot.answer_callback_query(call.id, "⏳ انتهت الجلسة، أعد الأمر.", show_alert=True)
        return

    target_uid  = extra["target_uid"]
    target_name = extra["target_name"]
    perms       = extra.get("perms", {})
    title       = extra.get("title", "")
    mode        = extra.get("mode", "promote")

    try:
        bot.promote_chat_member(cid, target_uid, **_build_perms_kwargs(perms))

        if title:
            try:
                bot.set_chat_administrator_custom_title(cid, target_uid, title)
            except Exception as e:
                log_event("promote_title_error", user=uid, target=target_uid, error=str(e))

        _remove_buttons(call)
        clear_state(uid, cid)

        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        granted = [label for key, label in PERMISSIONS if perms.get(key)]
        perms_text = "\n".join(f"  ✅ {p}" for p in granted) if granted else "  — لا صلاحيات"
        mode_label = "تعديل صلاحيات" if mode == "edit" else "ترقية"

        summary = (
            f"🎖 <b>تمت {mode_label} بنجاح</b>\n"
            f"👤 المستخدم: <a href='tg://user?id={target_uid}'>{target_name}</a>\n"
            f"🏷 اللقب: <b>{title or '—'}</b>\n"
            f"🔑 الصلاحيات:\n{perms_text}\n"
            f"🕒 {ts}"
        )
        bot.send_message(cid, summary, parse_mode="HTML", disable_web_page_preview=True)

        log_event(
            "promote_assigned",
            promoter=uid, target=target_uid, target_name=target_name,
            perms=perms, title=title, mode=mode, ts=ts,
        )
        bot.answer_callback_query(call.id, "✅ تم التعيين")

    except Exception as e:
        clear_state(uid, cid)
        _remove_buttons(call)
        log_event("promote_error", user=uid, target=target_uid, error=str(e))
        bot.answer_callback_query(call.id, f"❌ فشل: {e}", show_alert=True)
        bot.send_message(
            cid,
            f"❌ فشلت عملية الترقية:\n<code>{e}</code>",
            parse_mode="HTML",
        )
