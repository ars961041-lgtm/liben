from core.bot import bot
from database.db_queries.group_punishments_queries import delete_group_punishments, get_group_punishments, get_last_punishment, get_user_punishments, is_user_status, log_punishment, set_user_status
from handlers.group_admin.permissions import is_admin, sender_can_restrict
from utils.pagination import btn, register_action, send_ui
from utils.constants import lines

# ── رسائل العقوبات الموحدة ──
_MSGS = {
    # field: (already_applied, already_removed, applied, removed)
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

# ---------------------------- Core Punishment Handler
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
        bot.reply_to(message, "❌ حدد المستخدم بالرد أو الآيدي أو اليوزر.")
        return

    # ── تحقق من أن الهدف عضو حالي وليس بوتاً ──
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
    msgs = _MSGS.get(field)

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

        if msgs:
            template = msgs[3] if reverse else msgs[2]
            text = template.format(name=f"<a href='tg://user?id={user_id}'>{name}</a>")
        else:
            text = f"تم رفع {action_name}" if reverse else f"تم {action_name} <a href='tg://user?id={user_id}'>{name}</a>"

        bot.reply_to(message, text, parse_mode="HTML")

    except Exception as e:
        bot.reply_to(message, f"❌ خطأ:\n{e}")

# ---------------------------- Actions
def restrict_action(group_id, user_id, reverse):
    bot.restrict_chat_member(group_id, user_id, can_send_messages=reverse)


def ban_action(group_id, user_id, reverse):
    if reverse:
        bot.unban_chat_member(group_id, user_id)
    else:
        bot.ban_chat_member(group_id, user_id)


# ---------------------------- Command Wrappers
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


# ---------------------------- Handle Muted Messages
def handle_muted_users(message) -> bool:
    """يتحقق فقط إذا كان المستخدم مكتوماً في group_members — لا يحذف الرسالة بنفسه"""
    if message.chat.type == "private":
        return False
    user_id  = message.from_user.id
    group_id = message.chat.id
    return bool(is_user_status(user_id, group_id, 'is_muted'))


# ---------------------------- Get Target User
def get_target_user(message):
    # الرد على رسالة
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        return user.id, user.first_name

    args = message.text.strip().split()
    if len(args) < 2:
        return None, None

    # نأخذ آخر كلمة في الرسالة كمعرف الهدف
    target = args[-1]

    # اذا كان ايدي
    if target.isdigit():
        try:
            user = bot.get_chat_member(message.chat.id, int(target)).user
            return user.id, user.first_name
        except:
            return None, None

    # اذا كان يوزر
    if target.startswith("@"):
        try:
            user = bot.get_chat_member(message.chat.id, target).user
            return user.id, user.first_name
        except:
            return None, None

    return None, None

def record_action(message, user_id, action_type):
    """سجل العقوبة في جدول group_punishment_log"""
    executor_id = message.from_user.id
    group_id = message.chat.id
    log_punishment(group_id, user_id, action_type, executor_id)


# استدعاء بيانات المستخدم
def fetch_user_history(message, target_user_id):
    group_id = message.chat.id
    return get_user_punishments(group_id, target_user_id)


# استدعاء بيانات المجموعة
def fetch_group_history(message):
    group_id = message.chat.id
    return get_group_punishments(group_id)


# استدعاء آخر حدث لعقوبة معينة
def fetch_last_action(message, target_user_id, action_type):
    group_id = message.chat.id
    return get_last_punishment(group_id, target_user_id, action_type)

from datetime import datetime

def format_time(timestamp):
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d | %H:%M")
    except:
        return str(timestamp)

def display_user_history(message, target_user_id):
    if not is_developer(message):
        bot.reply_to(message, "ليس لديك صلاحية")
        return

    history = get_user_punishments(message.chat.id, target_user_id)

    ACTION_TYPES = {
        0: "🚫 حظر",
        1: "🔇 كتم",
        2: "⚠️ تقييد",
        3: "✅ رفع حظر",
        4: "🔊 رفع كتم",
        5: "🔓 رفع تقييد"
    }

    if not history:
        bot.reply_to(message, "❌ لا توجد سجلات لهذا المستخدم")
        return

    text = "📜 سجل العقوبات:\n\n"

    for i, (uid, action_type, executor_id, timestamp) in enumerate(history, start=1):
        action_name = ACTION_TYPES.get(action_type, "غير معروف")
        time_text = format_time(timestamp)
        text += f"{i}. {action_name}\n"
        text += f"   👤 على: {uid}\n"
        text += f"   🛠 بواسطة: {executor_id}\n"
        text += f"   🕒 {time_text}\n\n"


    @register_action("clear_log")
    def _clear_log_action(call, data):
        group_id = call.message.chat.id
        delete_group_punishments(group_id)
        try:
            bot.edit_message_text("✅ تم مسح سجل العقوبات", group_id, call.message.message_id)
        except:
            bot.answer_callback_query(call.id, "✅ تم المسح", show_alert=True)

    send_ui(
        chat_id=message.chat.id,
        text=text,
        buttons=[btn("🔴 مسح السجل", "clear_log")],
        layout=[1],
        owner_id=message.from_user.id
    )

from handlers.group_admin.permissions import is_developer

def clear_group_log(message):
    if not is_developer(message):
        bot.reply_to(message, "ليس لديك صلاحية")
        return

    group_id = message.chat.id
    delete_group_punishments(group_id)
    bot.reply_to(message, "تم مسح سجل العقوبات لهذا القروب")