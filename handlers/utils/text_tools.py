# import arabic_reshaper
# from bidi.algorithm import get_display
# from core.bot import bot


# def reshape_text(message):

#     if not message.reply_to_message:
#         return

#     text = message.reply_to_message.text

#     reshaped = arabic_reshaper.reshape(text)
#     bidi_text = get_display(reshaped)

#     bot.reply_to(message, bidi_text)