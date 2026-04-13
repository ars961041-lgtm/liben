"""
أوامر العقوبات والإدارة — كتم، حظر، تقييد، ترقية
قواعد:
  1. يمكن تحديد الهدف بـ: رد على رسالة | @username | user_id رقمي
  2. لا يمكن تطبيق أي إجراء على مطور البوت
  3. المنفّذ يجب أن يكون مشرفاً (للأوامر العادية)
  4. المطور يُطبّق الكتم عالمياً تلقائياً
"""
from core.bot import bot
from core.admin import is_any_dev
from database.db_queries.group_punishments_queries import (
    delete_group_punishments, get_group_punishments, get_last_punishment,
    get_user_punishments, is_user_status, log_punishment, set_user_status,
)
from handlers.group_admin.permissions import is_admin, sender_can_restrict
from utils.pagination import btn, register_action, send_ui
from utils.constants import lines
from utils.helpers import safe_reply
from utils.user_resolver import resolve_user, get_target_user_id

# ── رسائل العقوبات الموحدة ──
_MSGS = {
    "is_muted": (
        "❌ المستخدم مكتوم مسبقاً.",
        "❌ المستخدم غير مكتوم.",
        "🔇 تم كتم {name}",
        "🔊 تم رفع الكتم عن {name}",
    ),
    "is_banned": (
        "❌ المستخدم محظور مسبقاً.",
        "❌ المستخدم غير محظور.",
        "🚫 تم حظر {name}",
        "✅ تم رفع الحظر عن {name}",
    ),
    "is_restricted": (
        "❌ المستخدم مقيد مسبقاً.",
        "❌ المستخدم غير مقيد.",
        "⚠️ تم تقييد {name}",
        "🔓 تم رفع التقييد عن {name}",
    ),
}

_DEV_PROTECTED_MSG  = "❌ لا يمكن تطبيق هذا الإجراء على مطور البوت."
_REPLY_REQUIRED_MSG = (
    "❌ حدد المستخدم بإحدى الطرق:\n"
    "• الرد على رسالته\n"
    "• <code>@username</code>\n"
    "• رقم المعرف مثل: <code>123456789</code>"
)


# ══════════════════════════════════════════
# Unified User Resolver — re-exported from utils.user_resolver
# ══════════════════════════════════════════
# resolve_user and get_target_user_id are imported above from utils.user_resolver.
# They are re-exported here so existing callers that do:
#   from handlers.group_admin.restrictions import resolve_user
# continue to work without any changes.


# ══════════════════════════════════════════
# Get Target User (backward-compat alias)
# ══════════════════════════════════════════

def get_target_user(message):
    """
    واجهة متوافقة مع الكود القديم.
    يرجع (user_id, name) أو (None, hint_or_none).
    """
    uid, name, err = resolve_user(message)
    if uid is not None:
        return uid, name
    if err and "@" in err:
        for token in (message.text or "").split():
            if token.startswith("@"):
                return None, token
    return None, None


# ══════════════════════════════════════════
# Core Punishment Handler
# ══════════════════════════════════════════

def handle_punishment(message, field, action_name, apply_func=None, reverse=False, require_admin=True):
    if require_admin:
        if not is_admin(message):
            safe_reply(message, "❌ أنت لست مشرفاً في هذه المجموعة.")
            return
        if field in ("is_restricted", "is_muted", "is_banned"):
            ok, err = sender_can_restrict(message)
            if not ok:
                safe_reply(message, err)
                return

    user_id, name, err = resolve_user(message)

    if user_id is None:
        safe_reply(message, err or _REPLY_REQUIRED_MSG)
        return

    # حماية المطورين
    if is_any_dev(user_id):
        safe_reply(message, _DEV_PROTECTED_MSG)
        return

    # حماية المشرفين من الكتم/الحظر/التقييد
    if not reverse and field in ("is_muted", "is_banned", "is_restricted"):
        try:
            member = bot.get_chat_member(message.chat.id, user_id)
            if member.status in ("administrator", "creator"):
                safe_reply(message, "❌ لا يمكن تطبيق هذا الإجراء على مشرف.")
                return
            if member.user.is_bot:
                safe_reply(message, "❌ لا يمكن تطبيق هذا الأمر على بوت.")
                return
            if member.status in ("left", "kicked"):
                safe_reply(message, "❌ المستخدم ليس في المجموعة.")
                return
        except Exception:
            if not reverse:
                safe_reply(message, "❌ تعذّر التحقق من المستخدم — قد لا يكون في المجموعة.")
                return

    # التحقق من صلاحيات البوت قبل تنفيذ الإجراء
    if field in ("is_muted", "is_banned", "is_restricted"):
        try:
            bot_member = bot.get_chat_member(message.chat.id, bot.get_me().id)
            if bot_member.status != "administrator":
                safe_reply(message, "❌ البوت ليس مشرفاً في هذه المجموعة.")
                return
            if field == "is_banned" and not getattr(bot_member, "can_restrict_members", False):
                safe_reply(message, "❌ البوت لا يملك صلاحية حظر الأعضاء.")
                return
            if field in ("is_muted", "is_restricted") and not getattr(bot_member, "can_restrict_members", False):
                safe_reply(message, "❌ البوت لا يملك صلاحية تقييد الأعضاء.")
                return
        except Exception:
            pass  # تجاهل — سيظهر الخطأ عند التنفيذ

    group_id = message.chat.id
    msgs     = _MSGS.get(field)

    try:
        current_status = is_user_status(user_id, group_id, field)

        if not reverse and current_status:
            safe_reply(message, msgs[0] if msgs else f"❌ المستخدم {action_name} مسبقاً.")
            return

        if reverse and not current_status:
            safe_reply(message, msgs[1] if msgs else f"❌ المستخدم غير {action_name}.")
            return

        if apply_func:
            apply_func(group_id, user_id, reverse)

        set_user_status(user_id, group_id, field, 0 if reverse else 1)

        ACTION_TYPE_MAPPING = {"is_banned": 0, "is_muted": 1, "is_restricted": 2}
        action_type = ACTION_TYPE_MAPPING.get(field)
        if action_type is not None:
            log_punishment(group_id, user_id, action_type, message.from_user.id, reverse)

        executor_link = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
        user_link     = f"<a href='tg://user?id={user_id}'>{name}</a>"

        if msgs:
            template = msgs[3] if reverse else msgs[2]
            text = template.format(name=user_link)
            # Only show executor on apply actions, not on undo
            if not reverse and field in ("is_banned", "is_muted", "is_restricted"):
                text += f"\n👮 بواسطة: {executor_link}"
        else:
            text = (
                f"تم رفع {action_name}" if reverse
                else f"تم {action_name} {user_link}\n👮 بواسطة: {executor_link}"
            )

        safe_reply(message, text)

    except Exception as e:
        err = str(e).lower()
        print(f"[handle_punishment] error: {e}")
        if "chat_admin_required" in err or "not enough rights" in err:
            safe_reply(message, "❌ البوت لا يملك الصلاحيات الكافية لتنفيذ هذا الإجراء.")
        elif "user_not_participant" in err:
            safe_reply(message, "❌ المستخدم ليس في المجموعة.")
        else:
            safe_reply(message, "❌ حدث خطأ أثناء تنفيذ الأمر.")


# ══════════════════════════════════════════
# Actions
# ══════════════════════════════════════════

def _full_restrict_perms(allow: bool):
    """Returns a ChatPermissions object with all flags set to allow/deny."""
    from telebot.types import ChatPermissions
    return ChatPermissions(
        can_send_messages         = allow,
        can_send_audios           = allow,
        can_send_documents        = allow,
        can_send_photos           = allow,
        can_send_videos           = allow,
        can_send_video_notes      = allow,
        can_send_voice_notes      = allow,
        can_send_polls            = allow,
        can_send_other_messages   = allow,
        can_add_web_page_previews = allow,
    )


def restrict_action(group_id, user_id, reverse):
    """
    reverse=True  → lift restriction (all perms True)
    reverse=False → apply restriction (all perms False)
    Passes full ChatPermissions so Telegram enforces immediately.
    """
    bot.restrict_chat_member(group_id, user_id, _full_restrict_perms(allow=reverse))


def ban_action(group_id, user_id, reverse):
    if reverse:
        bot.unban_chat_member(group_id, user_id)
    else:
        bot.ban_chat_member(group_id, user_id)


# ══════════════════════════════════════════
# Command Wrappers
# ══════════════════════════════════════════

def restricted_user(message):
    handle_punishment(message, "is_restricted", "تقييد", restrict_action)


def unrestricted_user(message):
    handle_punishment(message, "is_restricted", "تقييد", restrict_action, reverse=True)


def ban_user(message):
    handle_punishment(message, "is_banned", "حظر", ban_action)


def unban_user(message):
    handle_punishment(message, "is_banned", "حظر", ban_action, reverse=True)


def mute_user(message):
    """
    كتم — المطور: كتم عالمي. المشرف: كتم على مستوى المجموعة.
    """
    uid = message.from_user.id
    if is_any_dev(uid):
        _dev_mute(message)
    else:
        handle_punishment(message, "is_muted", "كتم", _mute_action)


def unmute_user(message):
    handle_punishment(message, "is_muted", "كتم", _mute_action, reverse=True)


def _mute_action(group_id, user_id, reverse):
    """
    reverse=True  → restore can_send_messages
    reverse=False → block can_send_messages only (mute, not full restrict)
    """
    from telebot.types import ChatPermissions
    bot.restrict_chat_member(
        group_id, user_id,
        ChatPermissions(can_send_messages=reverse)
    )


def _dev_mute(message):
    """كتم عالمي من المطور — صامت إذا لم تكن للبوت صلاحية الحذف."""
    from core.admin import global_mute as _global_mute

    user_id, name, err = resolve_user(message)
    if user_id is None:
        safe_reply(message, err or _REPLY_REQUIRED_MSG)
        return

    if is_any_dev(user_id):
        safe_reply(message, _DEV_PROTECTED_MSG)
        return

    text  = (message.text or "").strip()
    parts = text.split(maxsplit=2)
    reason = parts[2] if len(parts) >= 3 else ""

    _global_mute(user_id, message.from_user.id, reason)

    safe_reply(
        message,
        f"🔇 تم الكتم العالمي للمستخدم <a href='tg://user?id={user_id}'>{name}</a>"
        + (f"\n📝 السبب: {reason}" if reason else ""),
    )


# ══════════════════════════════════════════
# Handle Muted Messages
# ══════════════════════════════════════════

def handle_muted_users(message) -> bool:
    """يتحقق فقط إذا كان المستخدم مكتوماً في group_members."""
    if message.chat.type == "private":
        return False
    user_id  = message.from_user.id
    group_id = message.chat.id
    return bool(is_user_status(user_id, group_id, "is_muted"))


# ══════════════════════════════════════════
# Logging helpers
# ══════════════════════════════════════════

def record_action(message, user_id, action_type):
    executor_id = message.from_user.id
    group_id    = message.chat.id
    log_punishment(group_id, user_id, action_type, executor_id)


def fetch_user_history(message, target_user_id):
    return get_user_punishments(message.chat.id, target_user_id)


def fetch_group_history(message):
    return get_group_punishments(message.chat.id)


def fetch_last_action(message, target_user_id, action_type):
    return get_last_punishment(message.chat.id, target_user_id, action_type)


from datetime import datetime


def format_time(timestamp):
    try:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d | %H:%M")
    except Exception:
        return str(timestamp)


def display_user_history(message, target_user_id):
    from handlers.group_admin.permissions import is_developer
    if not is_developer(message):
        safe_reply(message, "ليس لديك صلاحية")
        return

    history = get_user_punishments(message.chat.id, target_user_id)
    ACTION_TYPES = {
        0: "🚫 حظر", 1: "🔇 كتم", 2: "⚠️ تقييد",
        3: "✅ رفع حظر", 4: "🔊 رفع كتم", 5: "🔓 رفع تقييد",
    }

    if not history:
        safe_reply(message, "❌ لا توجد سجلات لهذا المستخدم")
        return

    text = "📜 سجل العقوبات:\n\n"
    for i, (uid, action_type, executor_id, timestamp) in enumerate(history, start=1):
        action_name = ACTION_TYPES.get(action_type, "غير معروف")
        text += (
            f"{i}. {action_name}\n"
            f"   👤 على: {uid}\n"
            f"   🛠 بواسطة: {executor_id}\n"
            f"   🕒 {format_time(timestamp)}\n\n"
        )

    @register_action("clear_log")
    def _clear_log_action(call, data):
        group_id = call.message.chat.id
        delete_group_punishments(group_id)
        try:
            bot.edit_message_text("✅ تم مسح سجل العقوبات", group_id, call.message.message_id)
        except Exception:
            bot.answer_callback_query(call.id, "✅ تم المسح", show_alert=True)

    send_ui(
        chat_id=message.chat.id,
        text=text,
        buttons=[btn("🔴 مسح السجل", "clear_log")],
        layout=[1],
        owner_id=message.from_user.id,
    )


def clear_group_log(message):
    from handlers.group_admin.permissions import is_developer
    if not is_developer(message):
        safe_reply(message, "ليس لديك صلاحية")
        return
    delete_group_punishments(message.chat.id)
    safe_reply(message, "تم مسح سجل العقوبات لهذا القروب")
