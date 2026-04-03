import html

from utils.helpers import send_reply



SHORTCUTS = {
    "#b#": ("<b>", "</b>"),
    "#i#": ("<i>", "</i>"),
    "#u#": ("<u>", "</u>"),
    "#s#": ("<s>", "</s>"),
    "#sp#": ("<tg-spoiler>", "</tg-spoiler>"),
    "#q#": ("<blockquote>", "</blockquote>")
}


def _parse(text: str):

    lines = text.split("\n")
    result = []
    stack = []

    for line in lines:

        stripped = line.strip()

        if stripped in SHORTCUTS:

            open_tag, close_tag = SHORTCUTS[stripped]

            if stack and stack[-1] == stripped:
                result.append(close_tag)
                stack.pop()
            else:
                result.append(open_tag)
                stack.append(stripped)

            continue

        result.append(html.escape(line))

    while stack:
        key = stack.pop()
        result.append(SHORTCUTS[key][1])

    return "\n".join(result)


def format_command(message):

    text = message.text.strip()

    if text != "تنسيق":
        return False

    if not message.reply_to_message:
        from core.bot import bot
        bot.reply_to(message, "❌ يجب الرد على رسالة")
        return True

    target = message.reply_to_message.text

    if not target:
        return True

    html_text = _parse(target)

    from core.bot import bot

    try:

        # bot.send_message(
        #     message.chat.id,
        #     html_text,
        #     parse_mode="HTML"
        # )
        send_reply(msg=message, text=html_text, parse_html=True, Shape=False)

    except:
        bot.reply_to(message, "❌ فشل التنسيق")

    return True