# handlers/utils/tops.py

from database.db_queries.groups_queries import get_top_group_members
from database.db_queries.countries_queries import get_top_country_stats
from handlers.tops.top_cache import get_top_cache, set_top_cache
from utils.helpers import limit_text
from utils.constants import lines

# ----------------------------
# توب الرسائل
# ----------------------------
def build_top(title, rows, limit=10):

    if not rows:
        return "لا توجد بيانات."

    emojis = ["🥇", "🥈", "🥉"] + [""] * (limit - 3)

    caption = f"{lines[4]}<b>\n🏆 {title}\n\n"

    for i, (_, value, name) in enumerate(rows, 1):
        emoji = emojis[i-1] if i <= 3 else ""
        name = limit_text(name, 20)
        caption += f"{i}) {emoji} {value} | {name}\n"

    caption += f"\n</b>{lines[4]}"

    return caption

def get_top_activity(group_id):

    # cache_key = f"top_activity_{group_id}"
    # cached = get_top_cache(cache_key)

    # if cached:
    #     return cached

    rows = get_top_group_members(group_id, 10)

    caption = build_top("توب المتفاعلين", rows)

    # set_top_cache(cache_key, caption)

    return caption

def get_top_richest(limit=10):
    from database.db_queries import get_top_bank_balances
    return get_top_bank_balances(limit)

def prepare_richest_rows(rows):

    result = []

    for row in rows:

        user_id = row["user_id"]
        balance = row["balance"]

        name = row["name"] if row["name"] else f"User {user_id}"

        result.append((user_id, f"{balance:.2f} ", name))

    return result

def get_top_richest_text(limit=10):

    # cache_key = f"top_richest_{limit}"

    # cached = get_top_cache(cache_key)
    # if cached:
    #     return cached

    rows = get_top_richest(limit)

    if not rows:
        return "لا يوجد بيانات بعد"

    rows = prepare_richest_rows(rows)

    text = build_top("أغنى اللاعبين", rows, limit)

    # set_top_cache(cache_key, text)

    return text

def get_top_countries():
    # cache_key = "top_countries"
    # cached = get_top_cache(cache_key)
    # if cached:
    #     return cached

    countries = get_top_country_stats()
    caption = "🌍 توب الدول\n\n"
    for i, (country_name, population) in enumerate(countries, 1):
        caption += f"{i}) {country_name} | {population}\n"

    # set_top_cache(cache_key, caption)
    return caption