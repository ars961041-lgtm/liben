
from handlers.tops.tops import get_top_activity, get_top_countries, get_top_richest_text
from utils.helpers import is_group, send_reply


def send_top_activity(message):
    if is_group(message):
        group_id = message.chat.id
        send_reply(message, get_top_activity(group_id))

def send_top_countries(message):
    if is_group(message):
        send_reply(message, get_top_countries())
    
def send_top_richest(message):
    if is_group(message):
        text = get_top_richest_text(10)
        send_reply(message, text)
    
def top_commands(message):
    text = message.text.strip()
    
    if text == "توب":
        return True
    
    elif text == "توب الفلوس":
        send_top_richest(message)
        return True
    
    elif text == "توب المتفاعلين":
        send_top_activity(message)
        return True
    
    elif text == "توب الدول":
        top_countries_text = get_top_countries()
        send_reply(message, top_countries_text)
        return True