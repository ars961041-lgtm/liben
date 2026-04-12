"""
news_broadcaster.py — Broadcasts important news to opted-in groups.

Groups opt in by having enable_news = 1 in their groups row.
Only HIGH and CRITICAL posts are broadcast by default.
"""
from database.connection import get_db_conn

# Minimum importance level to broadcast
_BROADCAST_LEVELS = {"HIGH", "CRITICAL"}


def get_news_enabled_groups() -> list[int]:
    """Returns Telegram group_ids where enable_news = 1."""
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        cur.execute("SELECT group_id FROM groups WHERE enable_news = 1")
        return [row[0] for row in cur.fetchall()]
    except Exception:
        return []


def broadcast_news(title: str, body: str, importance: str):
    """
    Sends a news post to all opted-in groups.
    Only broadcasts HIGH and CRITICAL importance posts.
    Silently skips groups that have blocked the bot.
    """
    if importance not in _BROADCAST_LEVELS:
        return

    groups = get_news_enabled_groups()
    if not groups:
        return

    try:
        from core.bot import bot
    except Exception:
        return

    text = f"📰 <b>{title}</b>\n\n{body}"
    sent = 0
    for group_id in groups:
        try:
            bot.send_message(group_id, text, parse_mode="HTML")
            sent += 1
        except Exception:
            pass

    if sent:
        print(f"[NewsBroadcaster] Sent '{title}' to {sent} groups.")
