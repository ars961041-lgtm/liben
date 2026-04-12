"""
modules/war/store_guard.py

Shared validation helpers for all store-related commands.
Import and call these before opening any store UI.
"""
from core.bot import bot

_MSG_NO_COUNTRY  = "❌ يجب أن يكون لديك دولة أولاً.\nاستخدم: <code>انشاء دولة </code>[الاسم]"
_MSG_NO_ALLIANCE = "❌ يجب أن يكون لديك تحالف أولاً.\nاستخدم: <code>إنشاء تحالف </code>[الاسم]"


def require_country(message) -> dict | None:
    """
    Checks that the sender owns a country.
    Returns the country dict on success, or None after sending an error reply.
    """
    from database.db_queries.countries_queries import get_country_by_owner
    country = get_country_by_owner(message.from_user.id)
    if not country:
        bot.reply_to(message, _MSG_NO_COUNTRY, parse_mode="HTML")
        return None
    return dict(country)


def require_alliance(message) -> dict | None:
    """
    Checks that the sender is in an alliance.
    Returns the alliance dict on success, or None after sending an error reply.
    """
    from database.db_queries.alliances_queries import get_alliance_by_user
    alliance = get_alliance_by_user(message.from_user.id)
    if not alliance:
        bot.reply_to(message, _MSG_NO_ALLIANCE, parse_mode="HTML")
        return None
    return dict(alliance)
