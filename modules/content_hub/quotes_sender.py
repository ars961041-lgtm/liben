"""
modules/content_hub/quotes_sender.py

Periodic quotes sender — registered with the unified IntervalScheduler.

Only quotes are auto-posted. anecdotes/stories/wisdom/poetry/azkar
are available on-demand via commands only.

Enabling/disabling per group:
  Admins use: "تفعيل الاقتباسات" / "إيقاف الاقتباسات"
  These commands update groups.quotes_enabled via toggle_quotes().
"""
import time

from core.bot import bot
from database.connection import get_db_conn
from modules.content_hub.hub_db import get_random, TYPE_LABELS

# ── in-memory throttle: group_id → last_sent_unix ────────────────
_last_sent: dict[int, float] = {}

# ── only quotes are auto-posted ───────────────────────────────────
_TABLE = "quotes"


def _get_interval_seconds() -> int:
    """Reads quotes_interval_minutes from bot_constants. Default 10 min."""
    try:
        from core.admin import get_const_int
        return get_const_int("quotes_interval_minutes", 10) * 60
    except Exception:
        return 600


def send_periodic_quotes():
    """
    Called by the IntervalScheduler every 5 minutes.
    Sends a quote to each group where quotes_enabled=1,
    respecting the configured interval per group.
    """
    interval = _get_interval_seconds()
    now      = time.time()

    conn   = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT group_id FROM groups WHERE quotes_enabled = 1")
    groups = [row["group_id"] for row in cursor.fetchall()]

    for tg_group_id in groups:
        last = _last_sent.get(tg_group_id, 0)
        if now - last < interval:
            continue

        row = get_random(_TABLE)
        if not row:
            continue

        label = TYPE_LABELS.get(_TABLE, "💬")
        text  = f"{label}\n\n{row['content']}"

        try:
            bot.send_message(tg_group_id, text, parse_mode="HTML")
            _last_sent[tg_group_id] = now
        except Exception as e:
            print(f"[QuotesSender] فشل الإرسال للمجموعة {tg_group_id}: {e}")


# ══════════════════════════════════════════════════════════════════
# Group-level toggle
# ══════════════════════════════════════════════════════════════════

def toggle_quotes(tg_group_id: int, enable: bool) -> bool:
    """Enables or disables periodic quotes for a group. Returns True on success."""
    from database.db_queries.groups_queries import get_internal_group_id
    internal_id = get_internal_group_id(tg_group_id)
    if not internal_id:
        return False
    conn = get_db_conn()
    conn.execute(
        "UPDATE groups SET quotes_enabled = ? WHERE id = ?",
        (1 if enable else 0, internal_id)
    )
    conn.commit()
    if not enable:
        _last_sent.pop(tg_group_id, None)
    return True


def is_quotes_enabled(tg_group_id: int) -> bool:
    from database.db_queries.groups_queries import get_internal_group_id
    internal_id = get_internal_group_id(tg_group_id)
    if not internal_id:
        return False
    conn   = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT quotes_enabled FROM groups WHERE id = ?", (internal_id,))
    row = cursor.fetchone()
    return bool(row and row["quotes_enabled"])
