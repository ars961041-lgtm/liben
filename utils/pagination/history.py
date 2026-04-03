# utils/pagination/history.py
from .router import register_action
from core.bot import bot

USER_HISTORY = {}

def push_history(user_id, chat_id, text, buttons, layout, precheck=None):
    USER_HISTORY.setdefault((user_id, chat_id), []).append({
        "text": text, "buttons": buttons, "layout": layout, "precheck": precheck
    })

@register_action("back")
def go_back(call, data):
    from .ui import edit_ui

    history = USER_HISTORY.get((call.from_user.id, call.message.chat.id), [])
    if len(history) < 2:
        bot.answer_callback_query(call.id, "لا يوجد رجوع")
        return
    history.pop()
    prev = history[-1]
    edit_ui(call, prev["text"], prev["buttons"], prev["layout"], prev.get("precheck"))