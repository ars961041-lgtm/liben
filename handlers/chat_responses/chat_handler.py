from email import message

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
        send_random(message, hello_responses)

    # ===== السلام =====
    elif text.startswith(tuple(SALAM)):
        send_random(message, salam_responses)

    # ===== صباح الخير =====
    elif any(text.startswith(m) for m in MORNING):
        send_random(message, morning_responses)

    # ===== مساء الخير =====

    elif any(text.startswith(n) for n in NIGHT):
        send_random(message, night_responses)

    # ===== السؤال عن الحال =====
    elif text in HOW:
        send_random(message, how_are_you_responses)

    # ===== الشكر =====
    elif text.startswith(tuple(THANKS)):
        send_random(message, thanks_responses)

    # ===== الوداع =====
    elif text in BYE:
        send_random(message, bye_responses)

    elif text in FAREWELL_RESPONSES:
        send_random(message, farewell_responses)
        
    # ===== مناداة البوت =====
    elif text in BOT:
        send_random(message, bot_responses)

    # ===== الضحك =====
    elif text.startswith(tuple(LAUGH)):
        send_random(message, laugh_responses)

    # ===== الموافقة / تمام =====
    elif text in OK:
        send_random(message, ok_responses)

    # ===== المدح =====
    elif text in GOOD:
        send_random(message, good_responses)

    # ===== دينية =====
    elif "النبي" in text or "الرسول" in text:
        send_random(message, prophet_responses)
        
    elif text in LOVE:
        send_random(message, love_responses)
        
    elif text in HATE:
        send_random(message, hate_responses)
        
    elif text in WHERE:
        send_random(message, where_responses)

    elif text in ARRIVAL_WORDS_RESPONSES:
        send_random(message, arrival_words_responses)
        
    elif text in PRIVATE:
        send_random(message, private_responses)
        
    elif text in FUNNY:
        send_random(message, funny_responses)
        
    elif text in HERE:
        send_random(message, here_responses)
    
    elif text in DIE_RESPONSES:
        send_random(message, die_responses)
    
    elif text in SMALL_LAUGH_RESPONSES:
        send_random(message, small_laugh_responses)
    
    elif text in TAZ_RESPONSES:
        send_random(message, taz_responses)
    
    elif text in YES_RESPONSES:
        send_random(message, yes_responses)
        
    elif text in NAWART_RESPONSES:
        send_random(message, nawart_responses)
        
    elif text in NICE_RESPONSES:
        send_random(message, nice_responses)
    
    elif text in LOVE_WORD_RESPONSES:
        send_random(message, love_word_responses)
        
