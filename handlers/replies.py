"""
نقطة الدخول الرئيسية لمعالجة الرسائل.

التدفق:
  receive_responses()
    ├── Flow Engine (StateManager)
    ├── _public_commands()       — /start، المطور
    └── _dispatch()
          ├── فحص الكتم
          ├── معالجات الإدخال (حالات الانتظار)
          ├── handle_shared_commands()   — قرآن، محتوى، تنسيق، إنجازات، ...
          ├── handle_group_commands()    — بنك، ألعاب، حرب، دول، كتم، ...  (مجموعات فقط)
          ├── handle_private_commands()  — تذاكر، ...                       (خاص فقط)
          └── chat_responses()           — ردود تلقائية
"""
from core.bot import bot
from core.state_manager import StateManager
from core.admin import is_globally_muted, is_group_muted
from utils.logger import log_event
from utils.helpers import send_result

from handlers.chat_responses.chat_handler import chat_responses
from handlers.general.general_handler import show_developer
from handlers.group_admin.restrictions import handle_muted_users
from handlers.users import add_user_if_not_exists, send_welcome, track_group_members
from core import memory

# ── أوامر العقوبات (تُستخدم في group_commands أيضاً) ──
from handlers.group_admin.restrictions import (
    ban_user, mute_user, restricted_user, unban_user,
    unmute_user, unrestricted_user, get_target_user,
)

commands = {
    "كتم":         mute_user,
    "رفع الكتم":   unmute_user,
    "حظر":         ban_user,
    "رفع الحظر":   unban_user,
    "تقييد":       restricted_user,
    "رفع التقييد": unrestricted_user,
}


# ══════════════════════════════════════════
# نقطة الدخول
# ══════════════════════════════════════════

def receive_responses(message):
    """نقطة الدخول الرئيسية — حدود الخطأ الإلزامية."""
    # Guard: some update types have no from_user
    if not message.from_user:
        return

    uid   = message.from_user.id
    cid   = message.chat.id
    state = StateManager.get(uid, cid)

    try:
        # Flow Engine — أولوية مطلقة (مجموعات + خاص)
        if StateManager.exists(uid, cid):
            from handlers.group_admin.developer.dev_flows import dispatch as _flow_dispatch
            if _flow_dispatch(message, uid, cid):
                return

        _public_commands(message)

        if _is_group(message):
            _dispatch(message)
        else:
            _dispatch_private(message)

    except Exception as e:
        # Only show the error message for unexpected crashes, not for
        # routine Telegram API errors (message not modified, flood wait, etc.)
        err_str = str(e).lower()
        is_routine = any(x in err_str for x in (
            "message is not modified",
            "message to edit not found",
            "bot was blocked",
            "user is deactivated",
            "chat not found",
            "have no rights",
            "not enough rights",
        ))
        StateManager.clear(uid, cid)
        log_event("flow_error", user=uid, chat=cid, error=str(e), state=state)
        if not is_routine:
            send_result(chat_id=cid, text="❌ حدث خطأ أثناء التنفيذ، تم إلغاء العملية")


# ══════════════════════════════════════════
# أوامر عامة (خاص + مجموعات)
# ══════════════════════════════════════════

def _public_commands(message):
    if message.text == "/start":
        send_welcome(message)
        return
    if message.text == "المطور":
        show_developer(message)
        return


# ══════════════════════════════════════════
# معالج المجموعات
# ══════════════════════════════════════════

def _dispatch(message):
    """معالج رسائل المجموعات."""
    add_user_if_not_exists(message)
    track_group_members(message)

    uid = message.from_user.id
    cid = message.chat.id

    # ── فحص انتهاء الجلسة ──
    # If the old router has a stale state but StateManager doesn't, just clear it silently.
    from utils.pagination.router import get_state as _gs, clear_state as _cs
    if _gs(uid, cid).get("state") and not StateManager.get(uid, cid):
        _cs(uid, cid)   # clear stale router state — no message to user

    # ── فحص الكتم ──
    if is_globally_muted(uid):
        try: bot.delete_message(cid, message.message_id)
        except Exception: pass
        return

    if is_group_muted(uid, cid) or handle_muted_users(message):
        try: bot.delete_message(cid, message.message_id)
        except Exception: pass
        return

    memory.set_last_interaction(uid, message.chat.type)

    # ── فحص قفل الوسائط ──
    from handlers.group_admin.media_lock import handle_media_lock
    if handle_media_lock(message):
        return

    if not message.text:
        return

    text            = message.text.strip()
    normalized_text = text.lower()

    if not text:
        return

    # ── معالجات الإدخال (حالات الانتظار) ──
    if _handle_input_states(message):
        return

    memory.set_last_command(uid, text)

    # ── أوامر مشتركة ──
    from handlers.command_handlers.shared_commands import handle_shared_commands
    if handle_shared_commands(message, normalized_text, text):
        return

    # ── أوامر المجموعات ──
    from handlers.command_handlers.group_commands import handle_group_commands
    if handle_group_commands(message, normalized_text, text):
        return

    # ── ردود تلقائية ──
    from database.db_queries.group_features_queries import is_feature_enabled as _feat
    if _feat(cid, "feat_replies"):
        chat_responses(message)


# ══════════════════════════════════════════
# معالج الخاص
# ══════════════════════════════════════════

def _dispatch_private(message):
    """معالج رسائل الخاص."""
    add_user_if_not_exists(message)

    uid = message.from_user.id
    cid = message.chat.id

    if is_globally_muted(uid):
        return

    memory.set_last_interaction(uid, message.chat.type)

    if not message.text:
        return

    text            = message.text.strip()
    normalized_text = text.lower()

    # ── معالجات الإدخال (حالات الانتظار) ──
    if _handle_input_states(message):
        return

    memory.set_last_command(uid, text)

    # ── أوامر مشتركة ──
    from handlers.command_handlers.shared_commands import handle_shared_commands
    if handle_shared_commands(message, normalized_text, text):
        return

    # ── أوامر الخاص فقط ──
    from handlers.command_handlers.private_commands import handle_private_commands
    if handle_private_commands(message):
        return

    # ── ردود تلقائية ──
    chat_responses(message)


# ══════════════════════════════════════════
# معالجات الإدخال النصي (حالات الانتظار)
# ══════════════════════════════════════════

def _handle_input_states(message) -> bool:
    """يعالج جميع حالات الانتظار. يرجع True إذا تم التعامل مع الرسالة."""
    from handlers.group_admin.developer.dev_panel import handle_dev_input
    from handlers.group_admin.developer.admin_panel import handle_admin_input
    from handlers.group_admin.developer.dev_store import handle_dev_store_input
    from handlers.group_admin.developer.dev_control_panel import handle_developer_input
    from modules.quran.quran_handler import handle_dev_quran_input
    from modules.content_hub.hub_handler import handle_hub_input
    from handlers.group_admin.promote import handle_promote_input
    from modules.country.city_management import handle_rename_input
    from modules.tickets.ticket_callbacks import handle_ticket_commands
    from utils.pagination.router import get_state as _gs

    uid = message.from_user.id
    cid = message.chat.id

    if handle_dev_input(message):       return True
    if handle_admin_input(message):     return True
    if handle_dev_store_input(message): return True
    if handle_developer_input(message): return True
    if handle_dev_quran_input(message): return True
    if handle_hub_input(message):       return True
    if handle_promote_input(message):   return True
    if handle_rename_input(message):    return True

    from modules.azkar.azkar_handler import handle_azkar_input
    if handle_azkar_input(message):     return True

    from modules.azkar.custom_zikr import handle_custom_zikr_input
    if handle_custom_zikr_input(message): return True

    from modules.magazine.magazine_handler import handle_magazine_input
    if handle_magazine_input(message):    return True

    from modules.post_creator import handle_post_creator_input
    if handle_post_creator_input(message): return True

    if handle_ticket_commands(message): return True

    if _gs(uid, cid).get("state") == "awaiting_ticket_msg":
        from modules.tickets.ticket_handler import handle_ticket_message_input
        handle_ticket_message_input(message)
        return True

    return False


# ══════════════════════════════════════════
# مساعدات
# ══════════════════════════════════════════

def _is_group(message) -> bool:
    return message.chat.type in ("group", "supergroup")


# backward-compat alias used by other modules
def is_group(message) -> bool:
    return _is_group(message)
