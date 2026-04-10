"""
أوامر العقوبات والإدارة — كتم، حظر، تقييد، ترقية
قواعد:
  1. يجب الرد على رسالة المستخدم المستهدف، أو ذكر @username في نص الأمر
  2. لا يمكن تطبيق أي إجراء على مطور البوت
  3. المنفّذ يجب أن يكون مشرفاً
"""
from core.bot import bot
from core.admin import is_any_dev
from database.db_queries.group_punishments_queries import (
    delete_group_punishments, get_group_punishments, get_last_punishment,
    get_user_punishments, is_user_status, log_punishment, set_user_status,
)
from database.db_queries.users_queries import get_user_id_by_username
from handlers.group_admin.permissions import is_admin, sender_can_restrict
from utils.pagination import btn, register_action, send_ui
from utils.constants import lines

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

_DEV_PROTECTED_MSG = "❌ لا يمكن تطبيق هذا الإجراء على مطور البوت."
_REPLY_REQUIRED_MSG = "❌ يجب الرد على رسالة المستخدم أو ذكر @username في الأمر."


# ══════════════════════════════════════════
# Core Punishment Handler
# ══════════════════════════════════════════

def handle_punishment(message, field, action_name, apply_func=None, reverse=False, require_admin=True):
    if require_admin:
        if not is_admin(message):
            bot.reply_to(message, "❌ أنت لست مشرفاً في هذه المجموعة.", parse_mode="HTML")
            return
        if field in ("is_restricted", "is_muted", "is_banned"):
            ok, err = sender_can_restrict(message)
            if not ok:
                bot.reply_to(message, err, parse_mode="HTML")
                return

    user_id, name = get_target_user(message)

    if not user_id:
        if name:  # كان هناك @username في النص لكنه غير مسجّل
            bot.reply_to(message,
                f"❌ المستخدم <code>{name}</code> غير موجود في قاعدة البيانات.\n"
                "يجب أن يكون المستخدم قد تفاعل مع البوت مسبقاً.",
                parse_mode="HTML")
        else:
            bot.reply_to(message, _REPLY_REQUIRED_MSG)
        return

    # 2. حماية المطورين
    if is_any_dev(user_id):
        bot.reply_to(message, _DEV_PROTECTED_MSG)
        return

    # 3. تحقق من أن الهدف عضو حالي وليس بوتاً (عند التطبيق فقط)
    if not reverse:
        try:
            member = bot.get_chat_member(message.chat.id, user_id)
            if member.user.is_bot:
                bot.reply_to(message, "❌ لا يمكن تطبيق هذا الأمر على بوت.")
                return
            if member.status in ("left", "kicked"):
                bot.reply_to(message, "❌ المستخدم ليس في المجموعة.")
                return
        except Exception:
            bot.reply_to(message, "❌ تعذّر التحقق من المستخدم.")
            return

    group_id = message.chat.id
    msgs     = _MSGS.get(field)

    try:
        current_status = is_user_status(user_id, group_id, field)

        if not reverse and current_status:
            bot.reply_to(message, msgs[0] if msgs else f"❌ المستخدم {action_name} مسبقاً.")
            return

        if reverse and not current_status:
            bot.reply_to(message, msgs[1] if msgs else f"❌ المستخدم غير {action_name}.")
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
            # أضف اسم المنفّذ للحظر والطرد والتقييد
            if not reverse and field in ("is_banned", "is_muted", "is_restricted"):
                text += f"\n👮 بواسطة: {executor_link}"
        else:
            text = (
                f"تم رفع {action_name}" if reverse
                else f"تم {action_name} {user_link}\n👮 بواسطة: {executor_link}"
            )

        bot.reply_to(message, text, parse_mode="HTML")

    except Exception as e:
        bot.reply_to(message, f"❌ خطأ:\n{e}")


# ══════════════════════════════════════════
# Actions
# ══════════════════════════════════════════

def restrict_action(group_id, user_id, reverse):
    bot.restrict_chat_member(group_id, user_id, can_send_messages=reverse)


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
    handle_punishment(message, "is_muted", "كتم")


def unmute_user(message):
    handle_punishment(message, "is_muted", "كتم", reverse=True)


# ══════════════════════════════════════════
# Promote Admin
# ══════════════════════════════════════════

def promote_admin(message):
    """رفع مشرف — يجب الرد على رسالة المستخدم أو ذكر @username."""
    user_id, name = get_target_user(message)
    if not user_id:
        bot.reply_to(message, _REPLY_REQUIRED_MSG)
        return

    if not is_admin(message):
        bot.reply_to(message, "❌ أنت لست مشرفاً في هذه المجموعة.")
        return

    # حماية المطورين من التعديل غير المقصود
    if is_any_dev(user_id):
        bot.reply_to(message, _DEV_PROTECTED_MSG)
        return

    try:
        bot.promote_chat_member(
            message.chat.id,
            user_id,
            can_change_info=True,
            can_delete_messages=True,
            can_invite_users=True,
            can_restrict_members=True,
            can_pin_messages=True,
            can_manage_chat=True,
        )
        bot.reply_to(
            message,
            f"👑 تم ترقية <a href='tg://user?id={user_id}'>{name}</a> إلى مشرف.",
            parse_mode="HTML",
        )
    except Exception as e:
        bot.reply_to(message, f"❌ فشل الترقية:\n{e}")


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
# Get Target User
# ══════════════════════════════════════════

def get_target_user(message):
    """
    يجلب المستخدم المستهدف بالأولوية التالية:
    1. الرد على رسالة المستخدم
    2. @username مذكور في نص الأمر → يُحلّ من جدول users
    يرجع (user_id, name) أو (None, None)
    """
    # 1. الرد على رسالة
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        return user.id, user.first_name

    # 2. @username في نص الأمر
    text = (message.text or "").strip()
    for token in text.split():
        if token.startswith("@") and len(token) > 1:
            user_id, name = get_user_id_by_username(token)
            if user_id:
                return user_id, name or token
            else:
                # username موجود في النص لكن غير مسجّل في قاعدة البيانات
                return None, token  # نُعيد الـ token كـ hint للرسالة

    return None, None


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
        bot.reply_to(message, "ليس لديك صلاحية")
        return

    history = get_user_punishments(message.chat.id, target_user_id)
    ACTION_TYPES = {
        0: "🚫 حظر", 1: "🔇 كتم", 2: "⚠️ تقييد",
        3: "✅ رفع حظر", 4: "🔊 رفع كتم", 5: "🔓 رفع تقييد",
    }

    if not history:
        bot.reply_to(message, "❌ لا توجد سجلات لهذا المستخدم")
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
        bot.reply_to(message, "ليس لديك صلاحية")
        return
    delete_group_punishments(message.chat.id)
    bot.reply_to(message, "تم مسح سجل العقوبات لهذا القروب")
