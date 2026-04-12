from email import message

from core.bot import bot

from .chat_responses import *
from .chat_triggers import *
import random

# دالة مساعدة لإرسال رد عشوائي من قائمة
def send_random(message, lst):
    # if random.random() < 0.4:
    """ترسل رسالة عشوائية من القائمة lst"""
    bot.reply_to(message, "<b>" + random.choice(lst) + "</b>", parse_mode="HTML")

# دالة المعالجة الرئيسية
def chat_responses(message):
    # نص الرسالة بعد تنظيف الفراغات وتحويلها إلى أحرف صغيرة
    text = message.text.strip().lower()

    # ===== مناداة البوت =====
    if any(text.startswith(b) for b in BELO_WORDS):
        send_random(message, belo_responses)
        
    elif any(text.startswith(b) for b in BOT_WORDS):
        send_random(message, bot_responses)
        
    # ===== التحيات =====
    if text in HELLO_WORDS:
        send_random(message, hello_responses)

    # ===== السلام =====
    elif text.startswith(tuple(SALAM_WORDS)):
        send_random(message, salam_responses)

    # ===== صباح الخير =====
    elif any(text.startswith(m) for m in MORNING_WORDS):
        send_random(message, morning_responses)

    # ===== مساء الخير =====

    elif any(text.startswith(n) for n in NIGHT_WORDS):
        send_random(message, night_responses)

    # ===== السؤال عن الحال =====
    elif any(text.startswith(h) for h in HOW_WORDS):
        send_random(message, how_are_you_responses)
        
    # ===== الشكر =====
    elif any(text.startswith(t) for t in THANKS_WORDS):
        send_random(message, thanks_responses)

    # ===== الوداع =====
    elif any(text.startswith(b) for b in BYE_WORDS):
        send_random(message, bye_responses)

    elif any(text.startswith(f) for f in FAREWELL_WORDS):
        send_random(message, farewell_responses)
    

    # ===== الضحك =====
    elif text.startswith("هه") and len(text) <= 4:
        send_random(message, small_laugh_responses)

    elif text.startswith(tuple(LAUGH_WORDS)):
        send_random(message, laugh_responses)

    # ===== الموافقة / تمام =====
    elif text.startswith(tuple(OK_WORDS)):
        send_random(message, ok_responses)

    # ===== المدح =====
    elif any(text.startswith(g) for g in GOOD_WORDS):
        send_random(message, good_responses)

    # ===== دينية =====
    elif "النبي" in text or "الرسول" in text:
        send_random(message, prophet_responses)
        
    elif text in LOVE_WORDS:
        send_random(message, love_responses)
        
    elif text in LOVE_WORD:
        send_random(message, love_word_responses)
        
    elif text in HATE_WORDS:
        send_random(message, hate_responses)
        
    elif text in WHERE_WORDS:
        send_random(message, where_responses)

    elif text in ARRIVAL_WORDS:
        send_random(message, arrival_words_responses)
        
    elif text in PRIVATE_WORDS:
        send_random(message, private_responses)
        
    elif text in CONTINUE_WORDS:
        send_random(message, continue_responses)
        
    elif text.startswith(tuple(HERE_WORDS)):
        send_random(message, here_responses)
    
    elif text in DIE_WORDS:
        send_random(message, die_responses)
    
    elif any(word in text for word in DISMISSIVE_WORDS):
        send_random(message, dismissive_responses)
    
    elif text.startswith(tuple(AGREE_WORDS)):
        send_random(message, agree_responses)
        
    elif text.startswith(tuple(NAWART_WORDS)):
        send_random(message, nawart_responses)
        
    elif text.startswith(tuple(PRAISE_WORDS)):
        send_random(message, praise_responses)
    
    elif text.startswith(tuple(WHAT_WORDS)):
        send_random(message, what_responses)
        
    elif text.startswith(tuple(BORED_WORDS)):
        send_random(message, bored_responses) 
        
    elif text.startswith(tuple(SILENCE_WORDS)):
        send_random(message, silence_responses) 
        
    elif text.startswith(tuple(KAFU_WORDS)):
        send_random(message, kafu_responses)
        
    elif text.startswith(tuple(KADHAB_WORDS)):
        send_random(message, kadhab_responses)
        
    elif text.startswith(tuple(SHDAWA_WORDS)):
        send_random(message, shdawa_responses)
        
    elif text.startswith(tuple(RIGHT_WORDS)):
        send_random(message, right_responses)
        
    elif text.startswith(tuple(WRONG_WORDS)):
        send_random(message, wrong_responses)
        
    

