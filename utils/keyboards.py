from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.bot import bot
import json
from telebot import types
import json

# =========================
# 🟦 Inline Button with Style
# =========================
def ui_btn(text, action=None, data=None, url=None, style="primary"):
    """
    text   -> نص الزر
    action -> معرف الـ callback
    data   -> dict إضافي يدمج في callback_data
    url    -> رابط خارجي
    style  -> لون الزر: "primary","success","danger","secondary"
    """
    if url:
        # زر رابط ما يحتاج callback_data
        if style == "default":
            return types.InlineKeyboardButton(
                text=text,
                url=url
            )
        else:
            return types.InlineKeyboardButton(
                text=text,
                url=url,
                style=style
            )

    # إذا action موجود
    payload = {"a": action}
    if data:
        payload.update(data)

    callback_data = json.dumps(payload, separators=(',', ':'))
    if style == "default":
        return types.InlineKeyboardButton(
            text=text,
            callback_data=callback_data,
        )

    return types.InlineKeyboardButton(
        text=text,
        callback_data=callback_data,
        style=style
    )


# =========================
# 🧱 Build Grid Keyboard
# =========================
def build_keyboard(buttons, layout):
    """
    buttons: list of types.InlineKeyboardButton
    layout: list من عدد الأزرار في كل صف
    مثال: [2,2,1] -> صفين 2 زر + صف 2 زر + صف 1 زر
    """
    markup = types.InlineKeyboardMarkup()
    index = 0

    for count in layout:
        row_buttons = []
        for _ in range(count):
            if index >= len(buttons):
                break
            row_buttons.append(buttons[index])
            index += 1

        if row_buttons:
            markup.row(*row_buttons)

    return markup


# =========================
# 📤 إرسال UI
# =========================
def send_ui(chat_id, text=None, photo=None, buttons=None, layout=[1]):
    markup = None
    if buttons:
        markup = build_keyboard(buttons, layout)

    if photo:
        return bot.send_photo(
            chat_id,
            photo,
            reply_markup=markup,
            caption=text,
            parse_mode="HTML"
        )

    return bot.send_message(
        chat_id,
        text,
        reply_markup=markup,
        parse_mode="HTML"
    )


# =========================
# ✏️ تعديل UI
# =========================
def edit_ui(call, text=None, buttons=None, layout=[1]):
    markup = None
    if buttons:
        markup = build_keyboard(buttons, layout)

    try:
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode="HTML"
        )
    except Exception:
        pass