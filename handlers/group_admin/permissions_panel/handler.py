"""
Entry point for the unified 'صلاحيات' command.
"""
from core.bot import bot
from core.state_manager import StateManager
from utils.helpers import safe_reply
from utils.logger import log_event
from utils.user_resolver import resolve_user

from .perms_config import ADMIN_PERMS, bot_can_promote
from .perms_state import STATE_TYPE, init_state, get_extra, set_extra, set_step, get_step, clear
from .perms_ui import send_ui, edit_ui

from . import perms_callbacks  # noqa: F401 — registers @register_action handlers

_NO_TARGET = (
    "❌ حدد المستخدم بإحدى الطرق:\n"
    "• الرد على رسالته\n"
    "• <code>@username</code>\n"
    "• رقم المعرف مثل: <code>123456789</code>"
)


def handle_permissions_command(message):
    """Trigger: 'صلاحيات' — opens the admin permissions panel."""
    uid = message.from_user.id
    cid = message.chat.id

    if message.chat.type not in ("group", "supergroup"):
        safe_reply(message, "❌ هذا الأمر يعمل في المجموعات فقط.")
        return

    # Sender must be admin
    try:
        sender = bot.get_chat_member(cid, uid)
        if sender.status not in ("administrator", "creator"):
            safe_reply(message, "❌ أنت لست مشرفاً في هذه المجموعة.")
            return
        # Sender must hold can_promote_members (or be creator)
        if sender.status == "administrator" and not getattr(sender, "can_promote_members", False):
            safe_reply(message, "⛔ ليس لديك صلاحية <b>ترقية الأعضاء</b> لاستخدام هذا الأمر.")
            return
    except Exception:
        safe_reply(message, "❌ تعذّر التحقق من صلاحياتك.")
        return

    if not bot_can_promote(cid):
        safe_reply(message, "❌ البوت لا يملك صلاحية ترقية الأعضاء.")
        return

    target_uid, target_name, res_err = resolve_user(message)
    if not target_uid:
        safe_reply(message, res_err or _NO_TARGET)
        return

    # Prevent self-targeting
    if target_uid == uid:
        safe_reply(message, "❌ لا يمكنك تعديل صلاحياتك الخاصة.")
        return

    try:
        member = bot.get_chat_member(cid, target_uid)
        if member.status in ("left", "kicked"):
            safe_reply(message, "❌ المستخدم غير موجود في المجموعة.")
            return
        if member.status == "creator":
            safe_reply(message, "❌ لا يمكن تعديل صلاحيات مؤسس المجموعة.")
            return
        # Anonymous admins can't be targeted via API
        if getattr(member, "is_anonymous", False) and member.status == "administrator":
            safe_reply(message, "❌ لا يمكن تعديل صلاحيات مشرف مجهول الهوية.")
            return
        target_is_admin = member.status == "administrator"
    except Exception as e:
        err = str(e).lower()
        if "user_not_participant" in err:
            safe_reply(message, "❌ المستخدم غير موجود في المجموعة.")
        else:
            safe_reply(message, "❌ تعذّر التحقق من المستخدم.")
        return

    # Load current admin permissions if target is already an admin
    current_promote = {k: False for k, _ in ADMIN_PERMS}
    if target_is_admin:
        for k, _ in ADMIN_PERMS:
            current_promote[k] = bool(getattr(member, k, False))

    init_state(uid, cid, target_uid, target_name, target_is_admin,
               promote=current_promote)
    log_event("perms_panel_opened", opener=uid, target=target_uid, chat=cid)

    msg = send_ui(cid, uid, cid, reply_to=message.message_id)
    if msg:
        set_extra(uid, cid, mid=msg.message_id)


def handle_permissions_input(message) -> bool:
    """Handles title text input during await_title step."""
    uid = message.from_user.id
    cid = message.chat.id

    state = StateManager.get(uid, cid)
    if not state or state.get("type") != STATE_TYPE:
        return False
    if get_step(uid, cid) != "await_title":
        return False

    extra = get_extra(uid, cid)
    if extra is None:
        return False

    raw   = (message.text or "").strip()
    title = "" if raw == "-" else raw[:16]

    set_extra(uid, cid, title=title)
    set_step(uid, cid, "main")

    label = f"<b>{title}</b>" if title else "— (بدون لقب)"
    safe_reply(message, f"✅ تم حفظ اللقب: {label}")

    mid = extra.get("mid")
    if mid:
        try:
            class _FakeCall:
                class message:
                    pass
            _FakeCall.message.chat       = type("C", (), {"id": cid})()
            _FakeCall.message.message_id = mid
            _FakeCall.from_user          = type("U", (), {"id": uid})()
            edit_ui(_FakeCall, uid, cid)
        except Exception as e:
            log_event("perms_panel_ui_refresh_error", error=str(e))

    return True
