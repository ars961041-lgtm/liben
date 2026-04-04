# import html

# from utils.helpers import send_reply

# SHORTCUTS = {
#     "#b#": ("<b>", "</b>"),
#     "#i#": ("<i>", "</i>"),
#     "#u#": ("<u>", "</u>"),
#     "#s#": ("<s>", "</s>"),
#     "#sp#": ("<tg-spoiler>", "</tg-spoiler>"),
#     "#q#": ("<blockquote>", "</blockquote>")
# }

# def _parse(text: str) -> str:
#     result = ""
#     stack = []
#     i = 0
#     while i < len(text):
#         matched = False
#         for key, (open_tag, close_tag) in SHORTCUTS.items():
#             if text[i:i+len(key)] == key:
#                 if stack and stack[-1] == key:
#                     result += close_tag
#                     stack.pop()
#                 else:
#                     result += open_tag
#                     stack.append(key)
#                 i += len(key)
#                 matched = True
#                 break
#         if not matched:
#             result += text[i]
#             i += 1

#     # أغلق أي اختصارات مفتوحة
#     while stack:
#         key = stack.pop()
#         result += SHORTCUTS[key][1]

#     return result

# def format_command(message):

#     text = message.text.strip()

#     if text != "تنسيق":
#         return False

#     if not message.reply_to_message:
#         from core.bot import bot
#         bot.reply_to(message, "❌ يجب الرد على رسالة")
#         return True

#     target = message.reply_to_message.text

#     if not target:
#         return True

#     html_text = _parse(target)

#     from core.bot import bot

#     try:

#         bot.send_message(
#             message.chat.id,
#             html_text,
#             parse_mode="HTML"
#         )
        
#         # send_reply(msg=message, text=html_text, parse_html=True, Shape=False)

#     except:
#         bot.reply_to(message, "❌ فشل التنسيق")

#     return True