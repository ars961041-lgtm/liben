"""
Entry points:
  handle_promote_command(message)  — triggered by /promote or "ترقية"
  handle_edit_command(message)     — triggered by /edit_admin or "تعديل مشرف"
  handle_promote_input(message)    — called from replies.py for text input (title)
"""
import time
from core.bot import bot
from core.state_manager import StateManager
from utils.logger import log_event
from handlers.group_admin.restrictions import get_target_user

from .promote_checks import run_promote_checks
from .promote_state import (
    init_promote_state, get_promote_extra, set_promote_extra,
    set_step, clear_state, PERMISSIONS, DEFAULT_PERMS, STATE_TYPE,
)
from .promote_ui import send_promote_ui, edit_promote_ui

# Import callbacks so their @register_action decorators fire at load time
from . import promote_callbacks  # noqa: F401


# ── /promote ──────────────────────────────────────────────────────────────────

def handle_promote_command(message):
    """Trigger: admin replies to a user with /promote or 'ترقية'."""
    uid = message.from_user.id
    cid = message.chat.id

    target_uid, target_name = get_target_user(message)
    if not target_uid:
        bot.reply_to(message, "❌ حدد المستخدم بالرد على رسالته أو بالـ ID أو اليوزر.")
        return

    ok, err, _ = run_promote_checks(message, target_uid)
    if not ok:
        bot.reply_to(message, err, parse_mode="HTML")
        return

    init_promote_state(uid, cid, target_uid, target_name, mode="promote")
    log_event("promote_started", promoter=uid, target=target_uid, chat=cid)

    msg = send_promote_ui(cid, uid, cid, page=0, reply_to=message.message_id)
    if msg:
        set_promote_extra(uid, cid, mid=msg.message_id)


# ── /edit_admin ───────────────────────────────────────────────────────────────

def handle_edit_command(message):
    """Trigger: admin replies to an existing admin with /edit_admin or 'تعديل مشرف'."""
    uid = message.from_user.id
    cid = message.chat.id

    target_uid, target_name = get_target_user(message)
    if not target_uid:
        bot.reply_to(message, "❌ حدد المشرف بالرد على رسالته أو بالـ ID أو اليوزر.")
        return

    ok, err, _ = run_promote_checks(message, target_uid)
    if not ok:
        bot.reply_to(message, err, parse_mode="HTML")
        return

    # Load current permissions from Telegram
    try:
        member = bot.get_chat_member(cid, target_uid)
        current_perms = {k: bool(getattr(member, k, False)) for k, _ in PERMISSIONS}
        current_title = getattr(member, "custom_title", "") or ""
    except Exception as e:
        bot.reply_to(message, f"❌ تعذّر جلب صلاحيات المشرف: {e}")
        return

    init_promote_state(uid, cid, target_uid, target_name,
                       perms=current_perms, mode="edit")
    set_promote_extra(uid, cid, title=current_title)
    log_event("promote_edit_started", editor=uid, target=target_uid, chat=cid)

    msg = send_promote_ui(cid, uid, cid, page=0, reply_to=message.message_id)
    if msg:
        set_promote_extra(uid, cid, mid=msg.message_id)


# ── Text input handler (title) ────────────────────────────────────────────────

def handle_promote_input(message) -> bool:
    """
    Called from replies.py dispatch.
    Returns True if the message was consumed by this flow.
    """
    uid = message.from_user.id
    cid = message.chat.id

    state = StateManager.get(uid, cid)
    if not state or state.get("type") != STATE_TYPE:
        return False
    if state.get("step") != "await_title":
        return False

    extra = get_promote_extra(uid, cid)
    if extra is None:
        return False

    raw = (message.text or "").strip()
    title = "" if raw == "-" else raw[:16]  # Telegram title max 16 chars

    set_promote_extra(uid, cid, title=title)
    set_step(uid, cid, "select")

    # Confirm to user
    label = f"<b>{title}</b>" if title else "— (بدون لقب)"
    bot.reply_to(message, f"✅ تم حفظ اللقب: {label}", parse_mode="HTML")

    # Refresh the UI message
    mid  = extra.get("mid")
    page = extra.get("page", 0)
    if mid:
        try:
            # Build a fake call-like object to reuse edit_promote_ui
            class _FakeCall:
                class message:
                    pass
            _FakeCall.message.chat = type("C", (), {"id": cid})()
            _FakeCall.message.message_id = mid
            _FakeCall.from_user = type("U", (), {"id": uid})()
            edit_promote_ui(_FakeCall, uid, cid, page=page)
        except Exception as e:
            log_event("promote_ui_refresh_error", error=str(e))

    return True
