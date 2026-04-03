# utils/pagination/ui.py
from core.bot import bot

def send_ui(chat_id, text=None, photo=None, buttons=None, layout=None, owner_id=None,
            precheck=None, reply_to=None):
    from .history import push_history
    from .buttons import build_keyboard
    layout = layout or [1]
    if owner_id:
        push_history(owner_id, chat_id, text, buttons, layout, precheck)
    markup = build_keyboard(buttons, layout, owner_id) if buttons else None
    kwargs = {"parse_mode": "HTML"}
    if reply_to:
        kwargs["reply_to_message_id"] = reply_to
    if photo:
        return bot.send_photo(chat_id, photo, caption=text, reply_markup=markup, **kwargs)
    return bot.send_message(chat_id, text, reply_markup=markup, **kwargs)

def edit_ui(call, text=None, buttons=None, layout=None, precheck=None):
    from .history import push_history
    from .buttons import build_keyboard
    layout = layout or [1]
    markup = build_keyboard(buttons, layout, call.from_user.id) if buttons else None
    if precheck:
        push_history(call.from_user.id, call.message.chat.id, text, buttons, layout, precheck)
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" in str(e):
            try: bot.answer_callback_query(call.id)
            except: pass
            
def grid(n: int, cols: int = 3) -> list:
    layout, rem = [], n
    while rem > 0:
        layout.append(min(cols, rem))
        rem -= cols
    return layout or [1]
