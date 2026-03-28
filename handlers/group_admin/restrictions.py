from core.bot import bot
from database.connection import get_db_conn
from database.db_queries.group_punishments import is_user_status, set_user_status
from handlers.group_admin.permissions import is_admin


def handle_punishment(
    message,
    field,
    action_name,
    apply_func=None,
    reverse=False,
    require_admin=True,
    require_reply=True,
):
    if require_admin and not is_admin(message):
        bot.reply_to(message, "ليس لديك صلاحية")
        return

    if require_reply and not message.reply_to_message:
        bot.reply_to(message, "يجب الرد على المستخدم")
        return

    user = message.reply_to_message.from_user
    user_id = user.id
    group_id = message.chat.id
    name = user.first_name

    conn = get_db_conn()

    try:
        current_status = is_user_status(user_id, group_id, field)

        if not reverse and current_status:
            bot.reply_to(message, f"المستخدم {action_name} مسبقاً")
            return

        if reverse and not current_status:
            bot.reply_to(message, f"المستخدم غير {action_name}")
            return

        if apply_func:
            apply_func(group_id, user_id, reverse)

        set_user_status(user_id, group_id, field, 0 if reverse else 1)

        if reverse:
            bot.reply_to(message, f"تم إلغاء {action_name}")
        else:
            bot.reply_to(
                message,
                f"تم {action_name} <a href='tg://user?id={user_id}'>{name}</a>",
                parse_mode="HTML"
            )

    except Exception as e:
        bot.reply_to(message, f"خطأ:\n{e}")

def restrict_action(group_id, user_id, reverse):
    bot.restrict_chat_member(
        group_id,
        user_id,
        can_send_messages=reverse
    )


def ban_action(group_id, user_id, reverse):
    if reverse:
        bot.unban_chat_member(group_id, user_id)
    else:
        bot.ban_chat_member(group_id, user_id)

def restricted_user(message):
    handle_punishment(
        message,
        field="is_restricted",
        action_name="تقييد",
        apply_func=restrict_action
    )

def unrestricted_user(message):
    handle_punishment(
        message,
        field="is_restricted",
        action_name="تقييد",
        apply_func=restrict_action,
        reverse=True
    )
    
def ban_user(message):
    handle_punishment(
        message,
        field="is_banned",
        action_name="حظر",
        apply_func=ban_action
    )

def unban_user(message):
    handle_punishment(
        message,
        field="is_banned",
        action_name="حظر",
        apply_func=ban_action,
        reverse=True
    )
    
def mute_user(message):
    handle_punishment(
        message,
        field="is_muted",
        action_name="كتم"
    )

def unmute_user(message):
    handle_punishment(
        message,
        field="is_muted",
        action_name="كتم",
        reverse=True
    )
    
def handle_muted_users(message):

    if message.chat.type == "private":
        return False

    user_id = message.from_user.id
    group_id = message.chat.id

    if is_user_status(user_id, group_id, 'is_muted'):
        try:
            bot.delete_message(group_id, message.message_id)
        except:
            pass
        return True
