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
from utils.helpers import safe_reply
from handlers.group_admin.restrictions import resolve_user, get_target_user

from .promote_checks import run_promote_checks
from .promote_state import (
    init_promote_state, get_promote_extra, set_promote_extra,
    set_step, clear_state, PERMISSIONS, DEFAULT_PERMS, STATE_TYPE,
)
from .promote_ui import send_promote_ui, edit_promote_ui

# Import callbacks so their @register_action decorators fire at load time
from . import promote_callbacks  # noqa: F401

_NO_TARGET_MSG = (
    "❌ حدد المستخدم بإحدى الطرق:\n"
    "• الرد على رسالته\n"
    "• <code>@username</code>\n"
    "• رقم المعرف مثل: <code>123456789</code>"
)


# ── /promote ──────────────────────────────────────────────────────────────────

def handle_promote_command(message):
    """Trigger: /promote or 'رفع مشرف' — always opens the permissions UI."""
    uid = message.from_user.id
    cid = message.chat.id

    target_uid, target_name, res_err = resolve_user(message)
    if not target_uid:
        safe_reply(message, res_err or _NO_TARGET_MSG)
        return

    ok, err, _ = run_promote_checks(message, target_uid)
    if not ok:
        safe_reply(message, err)
        return

    init_promote_state(uid, cid, target_uid, target_name, mode="promote")
    log_event("promote_started", promoter=uid, target=target_uid, chat=cid)

    msg = send_promote_ui(cid, uid, cid, page=0, reply_to=message.message_id)
    if msg:
        set_promote_extra(uid, cid, mid=msg.message_id)


# ── /edit_admin ───────────────────────────────────────────────────────────────

def handle_edit_command(message):
    """Trigger: /edit_admin or 'تعديل مشرف' — opens the permissions UI for any member."""
    uid = message.from_user.id
    cid = message.chat.id

    target_uid, target_name, res_err = resolve_user(message)
    if not target_uid:
        safe_reply(message, res_err or _NO_TARGET_MSG)
        return

    ok, err, _ = run_promote_checks(message, target_uid)
    if not ok:
        safe_reply(message, err)
        return

    # Load current permissions — works for both admins and regular members
    try:
        member = bot.get_chat_member(cid, target_uid)
        current_perms = {k: bool(getattr(member, k, False)) for k, _ in PERMISSIONS}
        current_title = getattr(member, "custom_title", "") or ""
    except Exception as e:
        print(f"[handle_edit_command] error: {e}")
        safe_reply(message, "❌ تعذّر جلب بيانات المستخدم.")
        return

    init_promote_state(uid, cid, target_uid, target_name,
                       perms=current_perms, mode="edit")
    set_promote_extra(uid, cid, title=current_title)
    log_event("promote_edit_started", editor=uid, target=target_uid, chat=cid)

    msg = send_promote_ui(cid, uid, cid, page=0, reply_to=message.message_id)
    if msg:
        set_promote_extra(uid, cid, mid=msg.message_id)


# ── /demote ───────────────────────────────────────────────────────────────────

def handle_demote_command(message):
    """Trigger: 'تنزيل مشرف' — removes admin rights from a user."""
    uid = message.from_user.id
    cid = message.chat.id

    # sender must be admin
    try:
        sender = bot.get_chat_member(cid, uid)
        if sender.status not in ("administrator", "creator"):
            safe_reply(message, "❌ أنت لست مشرفاً في هذه المجموعة.")
            return
    except Exception:
        safe_reply(message, "❌ تعذّر التحقق من صلاحياتك.")
        return

    target_uid, target_name, res_err = resolve_user(message)
    if not target_uid:
        safe_reply(message, res_err or _NO_TARGET_MSG)
        return

    # target must currently be an admin
    try:
        target = bot.get_chat_member(cid, target_uid)
        if target.status == "creator":
            safe_reply(message, "❌ لا يمكن تنزيل مؤسس المجموعة.")
            return
        if target.status != "administrator":
            safe_reply(message, "❌ المستخدم ليس مشرفاً أصلاً.")
            return
    except Exception:
        safe_reply(message, "❌ تعذّر التحقق من المستخدم.")
        return

    # bot must have can_promote_members
    try:
        bot_member = bot.get_chat_member(cid, bot.get_me().id)
        if not bot_member.can_promote_members:
            safe_reply(message, "❌ البوت لا يملك صلاحية تنزيل المشرفين.")
            return
    except Exception:
        safe_reply(message, "❌ تعذّر التحقق من صلاحيات البوت.")
        return

    try:
        bot.promote_chat_member(
            cid, target_uid,
            can_change_info=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False,
            can_manage_chat=False,
            can_manage_video_chats=False,
            can_manage_tags=False,
        )
        executor_link = f"<a href='tg://user?id={uid}'>{message.from_user.first_name}</a>"
        user_link     = f"<a href='tg://user?id={target_uid}'>{target_name}</a>"
        safe_reply(
            message,
            f"⬇️ تم تنزيل {user_link} من الإشراف\n👮 بواسطة: {executor_link}",
        )
        log_event("demote_assigned", executor=uid, target=target_uid, chat=cid)
    except Exception as e:
        err = str(e).lower()
        print(f"[handle_demote_command] error: {e}")
        if "chat_admin_required" in err or "not enough rights" in err:
            safe_reply(
                message,
                "❌ لا يمكن تنزيل هذا المشرف.\n"
                "قد يكون تم تعيينه من قبل مالك المجموعة أو صلاحيات البوت غير كافية."
            )
        else:
            safe_reply(message, "❌ فشلت عملية التنزيل.")


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

    label = f"<b>{title}</b>" if title else "— (بدون لقب)"
    safe_reply(message, f"✅ تم حفظ اللقب: {label}")

    # Refresh the UI message
    mid  = extra.get("mid")
    page = extra.get("page", 0)
    if mid:
        try:
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
