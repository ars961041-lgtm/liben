# handlers/utils/tops.py

from database.db_queries.groups_queries import get_top_group_members
from database.db_queries.countries_queries import get_top_country_stats
from handlers.tops.top_cache import get_top_cache, set_top_cache
from utils.helpers import is_group, limit_text, send_reply
from utils.constants import lines

# ----------------------------
# توب الرسائل
# ----------------------------
def get_top_messages(group_id):
    cache_key = f"top_messages_{group_id}"
    cached = get_top_cache(cache_key)
    if cached:
        return cached

    top_users = get_top_group_members(group_id, limit=10)
    if not top_users:
        return "لا توجد بيانات."

    emojis = ["🥇", "🥈", "🥉"] + [""] * 7
    caption = f"{lines[4]}<b>\n🏆 توب المتفاعلين\n\n"
    for i, (user_id, msg_count, name) in enumerate(top_users, 1):
        emoji = emojis[i-1] if i <= 3 else ""
        name = limit_text(name, 20)
        caption += f"{i}) {emoji} {msg_count} | {name}\n"
    caption += f"\n</b>{lines[4]}"

    set_top_cache(cache_key, caption)
    return caption

# ----------------------------
# توب النشاط
# ----------------------------
def get_top_activity(group_id):
    cache_key = f"top_activity_{group_id}"
    cached = get_top_cache(cache_key)
    if cached:
        return cached

    users = get_top_group_members(group_id, limit=10)
    caption = "⚡ أكثر الأعضاء نشاطاً\n\n"
    for i, (user_id, msg_count, name) in enumerate(users, 1):
        name = limit_text(name, 20)
        caption += f"{i}) {name} | {msg_count}\n"

    set_top_cache(cache_key, caption)
    return caption

# ----------------------------
# توب الدول
# ----------------------------
def get_top_countries():
    cache_key = "top_countries"
    cached = get_top_cache(cache_key)
    if cached:
        return cached

    countries = get_top_country_stats()
    caption = "🌍 توب الدول\n\n"
    for i, (country_name, population) in enumerate(countries, 1):
        caption += f"{i}) {country_name} | {population}\n"

    set_top_cache(cache_key, caption)
    return caption

# ----------------------------
# أوامر إرسال التوبات
# ----------------------------
def send_top_users(message):
    if not is_group(message):
        send_reply(message, "هذا الأمر متاح فقط في المجموعات!")
        return
    group_id = message.chat.id
    send_reply(message, get_top_messages(group_id))

def send_top_messages(message):
    if not is_group(message):
        send_reply(message, "هذا الأمر للمجموعات فقط")
        return
    group_id = message.chat.id
    send_reply(message, get_top_messages(group_id))

def send_top_activity(message):
    if not is_group(message):
        send_reply(message, "هذا الأمر للمجموعات فقط")
        return
    group_id = message.chat.id
    send_reply(message, get_top_activity(group_id))

def send_top_countries(message):
    send_reply(message, get_top_countries())