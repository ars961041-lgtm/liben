from core.bot import bot
from .chat_responses import *
from .chat_triggers import *


def chat_responses(message):

    text = message.text.strip().lower()

    if text in HELLO:
        bot.reply_to(message, rand(hello))

    elif text.startswith(tuple(SALAM)):
        bot.reply_to(message, rand(salam))

    elif text in MORNING:
        bot.reply_to(message, rand(morning))

    elif text in NIGHT:
        bot.reply_to(message, rand(night))

    elif text in HOW:
        bot.reply_to(message, rand(how_are_you))

    elif text.startswith(tuple(THANKS)):
        bot.reply_to(message, rand(thanks))

    elif text in BYE:
        bot.reply_to(message, rand(bye))

    elif text in BOT:
        bot.reply_to(message, rand(bot))

    elif text.startswith(tuple(LAUGH)):
        bot.reply_to(message, rand(laugh))

    elif text in OK:
        bot.reply_to(message, rand(agreement))

    elif text in GOOD:
        bot.reply_to(message, rand(compliments))

    elif "النبي" in text or "الرسول" in text:
        bot.reply_to(message, rand(religious))