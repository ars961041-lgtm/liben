from core.bot import bot

from .chat_responses import *
from .chat_triggers import *
import random

# دالة مساعدة لإرسال رد عشوائي من قائمة
def send_random(message, lst):
    """ترسل رسالة عشوائية من القائمة lst"""
    bot.reply_to(message, random.choice(lst))

# دالة المعالجة الرئيسية
def chat_responses(message):
    # نص الرسالة بعد تنظيف الفراغات وتحويلها إلى أحرف صغيرة
    text = message.text.strip().lower()

    # ===== التحيات =====
    if text in HELLO:
        send_random(message, hello)

    # ===== السلام =====
    elif text.startswith(tuple(SALAM)):
        send_random(message, salam)

    # ===== صباح الخير =====
    elif text in MORNING:
        send_random(message, morning)

    # ===== مساء الخير =====
    elif text in NIGHT:
        send_random(message, night)

    # ===== السؤال عن الحال =====
    elif text in HOW:
        send_random(message, how_are_you)

    # ===== الشكر =====
    elif text.startswith(tuple(THANKS)):
        send_random(message, thanks)

    # ===== الوداع =====
    elif text in BYE:
        send_random(message, bye)

    # ===== مناداة البوت =====
    elif text in BOT:
        send_random(message, bot_replies)

    # ===== الضحك =====
    elif text.startswith(tuple(LAUGH)):
        send_random(message, laugh)

    # ===== الموافقة / تمام =====
    elif text in OK:
        send_random(message, agreement)

    # ===== المدح =====
    elif text in GOOD:
        send_random(message, compliments)

    # ===== دينية =====
    elif "النبي" in text or "الرسول" in text:
        send_random(message, religious)

    # ===== الردود الفكاهية العشوائية =====
    elif any(word in text for word in funny):
        send_random(message, funny)

    # ===== الردود العشوائية للدردشة =====
    else:
        # هنا لو تحب ممكن تضيف ردود عشوائية عامة
        if random.randint(1, 5) == 3:  # فرصة بسيطة للردود العشوائية
            send_random(message, random_chat)