import time
from handlers.chat_responses.chat_handler import chat_responses
from handlers.tops.tops_handler import top_commands
from modules.country.handlers.country_handler import create_country_command, my_country
from modules.bank.handlers.bank_handler import bank_commands
from utils.helpers import send_reply
from .users import (add_user_if_not_exists, track_group_members, send_welcome, send_profile)
# from database.connection import get_db_conn
# from utils.helpers import send_reply, send_error, get_error_icons, is_group, send_error_reply
from utils.constants import lines

def receive_responses(message):
    add_user_if_not_exists(message)
    track_group_members(message)
    normalized_text = message.text.strip()

    if normalized_text == "/start":
        send_welcome(message)

    elif bank_commands(message):
        return

    elif top_commands(message):
        return
    
    elif normalized_text.lower().startswith('إنشاء دولة') or normalized_text.lower().startswith('انشاء دولة'):
        create_country_command(message)
    elif normalized_text == 'دولتي':
        my_country(message)

    # 👇 أوامر البروفايل
    elif normalized_text in ["ايدي", "عني", "معلوماتي"]:
        send_profile(message)
    
    chat_responses(message)

