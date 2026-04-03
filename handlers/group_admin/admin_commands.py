from core.bot import bot
from database.reset_db import reset_database
from database.update_db import update_database
from handlers.group_admin.permissions import can_delete_messages, can_pin_messages, is_admin, is_developer

# ------------------------------------------------------------- Group Name & Bio

def set_group_name(message): 
    new_name = message.reply_to_message.text
    chat_id = message.chat.id 
    if is_admin(message):
        if message.chat.type in ['supergroup', 'group']:
            if message.reply_to_message:
                if message.text:
                    bot.set_chat_title(chat_id, new_name)
                    text1 = f'<b> تم تغيير اسم المجموعة</b>'
                    bot.reply_to(message, text1, parse_mode='HTML') 
                else:
                    text2 = f'<b> يرجى الرد على نص</b>'
                    bot.reply_to(message, text2, parse_mode='HTML')  
            else:
                text3 = f'<b> يرجى الرد على الاسم الجديد للمجموعة</b>'
                bot.reply_to(message, text3, parse_mode='HTML')
    else:
        text4 = f'<b> أنت لست مشرفًا في هذه المجموعة</b>'
        bot.reply_to(message, text4, parse_mode='HTML')

def set_group_bio(message):
    new_bio = message.reply_to_message.text
    chat_id = message.chat.id
    if is_admin(message):
        if message.chat.type in ['supergroup', 'group']:    
            if message.reply_to_message:    
                if not message.reply_to_message.photo: 
                    bot.set_chat_description(chat_id, new_bio)
                    text1 = f'<b> تم تغيير بايو المجموعة</b>'
                    bot.reply_to(message, text1, parse_mode='HTML') 
                else:
                    text2 = f'<b> يرجى الرد على نص</b>'
                    bot.reply_to(message, text2, parse_mode='HTML')
            else:
                text3 = f'<b> يرجى الرد على البايو الجديد للمجموعة</b>'
                bot.reply_to(message, text3, parse_mode='HTML')
    else:
        text4 = f'<b> أنت لست مشرفًا في هذه المجموعة</b>'
        bot.reply_to(message, text4, parse_mode='HTML')

def custom_title(message):

    if not is_admin(message):
        bot.reply_to(message, "<b>أنت لست مشرف</b>", parse_mode='HTML')
        return

    member = bot.get_chat_member(message.chat.id, message.from_user.id)

    if member.custom_title:
        bot.reply_to(message, f"<b>لقبك: {member.custom_title}</b>", parse_mode='HTML')
    else:
        bot.reply_to(message, "<b>ليس لديك لقب</b>", parse_mode='HTML')

def delete_message(message):

    if not is_admin(message):
        bot.reply_to(message, "<b>ليس لديك صلاحية</b>", parse_mode='HTML')
        return
    
    if not can_delete_messages(message.chat.id):
        bot.reply_to(message, "<b>البوت لا يملك صلاحية حذف الرسائل</b>", parse_mode='HTML')
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "<b>يجب الرد على الرسالة المراد حذفها</b>", parse_mode='HTML')
        return

    try:
        bot_info = bot.get_me()
        bot_member = bot.get_chat_member(message.chat.id, bot_info.id)

        if not bot_member.can_delete_messages:
            bot.reply_to(message, "<b>البوت لا يملك صلاحية حذف الرسائل</b>", parse_mode='HTML')
            return

        bot.delete_message(
            message.chat.id,
            message.reply_to_message.message_id
        )

    except Exception as e:
        bot.reply_to(message, f"<b>error in [delete_message]</b>\n{e}", parse_mode='HTML')

def pin_message(message):

    if not is_admin(message):
        bot.reply_to(message, "<b>ليس لديك صلاحية</b>", parse_mode='HTML')
        return

    if not can_pin_messages(message.chat.id):
        bot.reply_to(message, "<b>البوت لا يملك صلاحية تثبيت الرسائل</b>", parse_mode='HTML')
        return

    if not message.reply_to_message:
        bot.reply_to(message, "<b>يجب الرد على الرسالة</b>", parse_mode='HTML')
        return

    try:
        bot_info = bot.get_me()
        bot_member = bot.get_chat_member(message.chat.id, bot_info.id)

        if not bot_member.can_pin_messages:
            bot.reply_to(message, "<b>البوت لا يملك صلاحية تثبيت الرسائل</b>", parse_mode='HTML')
            return

        bot.pin_chat_message(
            message.chat.id,
            message.reply_to_message.message_id
        )

        bot.reply_to(message, "<b>تم تثبيت الرسالة</b>", parse_mode='HTML')

    except Exception as e:
        bot.reply_to(message, f"<b>error in [pin_message]</b>\n{e}", parse_mode='HTML')
              

def reset_db(message):
    if is_developer(message):
        try:
            reset_database()
            bot.reply_to(message, "✅ تم إعادة إنشاء قاعدة البيانات بنجاح.")
        except Exception as e:
            bot.reply_to(message, f"🔥 حدث خطأ أثناء إعادة إنشاء القاعدة:\n{e}")

def update_db(message):
    if is_developer(message):
        try:
            update_database()
            bot.reply_to(message, "✅ تم تحديث قاعدة البيانات بنجاح.")
        except Exception as e:
            bot.reply_to(message, f"🔥 حدث خطأ أثناء تحديث القاعدة:\n{e}")
            
