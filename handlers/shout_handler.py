"""
handlers/shout_handler.py

ميزة الصياح — عندما يرد مستخدم على رسالة بكلمة "صيح"
يرسل البوت رسالة خاصة للمستخدم المُشار إليه يُعلمه أن شخصاً ما يناديه.
"""
from core.bot import bot
from utils.keyboards import ui_btn, build_keyboard
from utils.helpers import send_reply, get_left_arrows

def handle_shout(message) -> bool:
    """
    يعالج أمر "صيح" — يجب أن يكون رداً على رسالة.
    يرجع True إذا تم التعامل مع الأمر.
    """
    if (message.text or "").strip() != "صيح":
        return False

    # يجب أن يكون رداً على رسالة
    if not message.reply_to_message or not message.reply_to_message.from_user:
        send_reply(msg=message, text= f"<b>رد على رسالة شخص ما بكلمة 'صيح' عشان تصيح له!</b> ")
        return False

    target = message.reply_to_message.from_user

    # لا يُرسَل للبوتات
    if target.is_bot:
        return False

    sender     = message.from_user
    chat       = message.chat
    chat_title = chat.title or "مجموعة"

    # اسم المُرسِل
    sender_name = (sender.first_name or "").strip()
    if sender.last_name:
        sender_name += f" {sender.last_name}"
    sender_name = sender_name or f"مستخدم {sender.id}"

    # رابط للمجموعة / الرسالة
    group_link = _build_group_link(chat, message.message_id)

    # بناء الزر
    btn     = ui_btn("📍 اذهب للمجموعة", url=group_link)
    markup  = build_keyboard([btn], [1])

    send_reply(msg= message, text= f" تم ازعاج {get_left_arrows()} <a href='tg://user?id={target.id}'>{target.first_name}</a> إذا لم يحظر البوت😎!")
    # إرسال الرسالة الخاصة للمستقبِل
    try:
        bot.send_message(
            target.id,
            f"📢 <b>{sender_name}\n</b> يناديك في <b>{chat_title}</b>!",
            parse_mode="HTML",
            reply_markup=markup,
        )
        # رد على المُرسِل بتأكيد النجاح
    except Exception:
        # المستخدم حجب البوت أو لم يبدأ محادثة — تجاهل صامت
        pass

    return True


def _build_group_link(chat, message_id: int) -> str:
    """يبني رابطاً مباشراً للرسالة في المجموعة."""
    username = getattr(chat, "username", None)
    if username:
        return f"https://t.me/{username}/{message_id}"
    # مجموعة خاصة — رابط t.me/c/
    chat_id_str = str(chat.id).lstrip("-100")
    return f"https://t.me/c/{chat_id_str}/{message_id}"
