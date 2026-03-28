# core/permissions.py
from core.config import developers_id

def is_developer(user_id: int) -> bool:
    return user_id in developers_id

from core.bot import bot

def is_admin(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False
    
def bot_is_admin(chat_id):

    bot_info = bot.get_me()
    member = bot.get_chat_member(chat_id, bot_info.id)

    return member.status == "administrator"

def can_delete_messages(chat_id):

    bot_info = bot.get_me()
    member = bot.get_chat_member(chat_id, bot_info.id)

    return member.can_delete_messages

def can_pin_messages(chat_id):

    bot_info = bot.get_me()
    member = bot.get_chat_member(chat_id, bot_info.id)

    return member.can_pin_messages

def can_restrict_members(chat_id):

    bot_info = bot.get_me()
    member = bot.get_chat_member(chat_id, bot_info.id)

    return member.can_restrict_members

def can_change_info(chat_id):

    bot_info = bot.get_me()
    member = bot.get_chat_member(chat_id, bot_info.id)

    return member.can_change_info