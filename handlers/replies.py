import time

from core.bot import bot
from database.reset_db import reset_database
from database.update_db import update_database
from handlers.chat_responses.chat_handler import chat_responses
from handlers.group_admin.admin_commands import custom_title, pin_message, delete_message
from handlers.group_admin.admin_commands import set_group_bio, set_group_name
from handlers.group_admin.restrictions import ban_user, handle_muted_users, mute_user, restricted_user, unban_user, unmute_user, unrestricted_user
from handlers.misc.time_date import today_date, today_time
from handlers.tops.tops_handler import top_commands
from modules.country.handlers.country_handler import create_country_command, my_country
from modules.bank.handlers.bank_handler import bank_commands
from utils.helpers import is_developer, send_reply
from .users import (add_user_if_not_exists, track_group_members, send_welcome, send_profile)

def receive_responses(message):
    add_user_if_not_exists(message)
    track_group_members(message)
    normalized_text = message.text.strip()

    if handle_muted_users(message):
        return
    
    if normalized_text == "/start":
        send_welcome(message)

    elif bank_commands(message):
        return

    elif top_commands(message):
        return
    
    elif normalized_text == "اليوم":
        today_date(message)
        
    elif normalized_text in ["كم الساعة", "كم الساعه", "الساعة كم", "الساعه كم", "الوقت"]:
        today_time(message)
        
    elif normalized_text == "اليوم":
        today_date(message)
        
    elif normalized_text == "مسح":
        delete_message(message)
        
    elif normalized_text == "تثبيت":
        pin_message(message)
        
    elif normalized_text == "لقبي":
        custom_title(message)
    
    if message.text == 'تعيين اسم المجموعة':
        set_group_name(message)
        
    if message.text == 'تعيين بايو المجموعة':
        set_group_bio(message)    

    elif normalized_text == "كتم":
        mute_user(message)
    
    elif normalized_text == "رفع الكتم":
        unmute_user(message)
    
    elif normalized_text == "حظر":
        ban_user(message)
    
    elif normalized_text == "رفع الحظر":
        unban_user(message)
    
    elif normalized_text == "تقييد":
        restricted_user(message)
    
    elif normalized_text == "رفع التقييد":
        unrestricted_user(message)
    
    #################################################################
    elif normalized_text.lower().startswith('إنشاء دولة') or normalized_text.lower().startswith('انشاء دولة'):
        create_country_command(message)
  
    elif normalized_text == 'دولتي':
        my_country(message)
 
    elif normalized_text == 'مسح قاعدة البيانات':
        reset_db(message)
 
    elif normalized_text == 'تحديث قاعدة البيانات':
        update_db(message)

    elif normalized_text in ["ايدي", "عني", "معلوماتي"]:
        send_profile(message)
    
    chat_responses(message)

def reset_db(message):
    if is_developer(message.from_user.id):
        try:
            reset_database()
            bot.reply_to(message, "✅ تم إعادة إنشاء قاعدة البيانات بنجاح.")
        except Exception as e:
            bot.reply_to(message, f"🔥 حدث خطأ أثناء إعادة إنشاء القاعدة:\n{e}")


def update_db(message):
    if is_developer(message.from_user.id):
        try:
            update_database()
            bot.reply_to(message, "✅ تم تحديث قاعدة البيانات بنجاح.")
        except Exception as e:
            bot.reply_to(message, f"🔥 حدث خطأ أثناء تحديث القاعدة:\n{e}")