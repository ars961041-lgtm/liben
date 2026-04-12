"""
modules/content_hub/azkar_sender.py

Periodic Azkar sender — registered with the unified IntervalScheduler.

Auto-posting policy: ONLY quotes and azkar are auto-posted.
anecdotes / stories / wisdom / poetry are available on-demand only.

Enabling/disabling per group:
  • From 'الأوامر' panel → 📿 الأذكار التلقائية (toggle button)
  • Or text command: "تفعيل الأذكار" / "إيقاف الأذكار"
  These update groups.azkar_enabled via toggle_azkar().

Interval: controlled by bot_constants.azkar_interval_minutes (default 10).
"""
import time

from core.bot import bot
from database.connection import get_db_conn
from modules.content_hub.hub_db import get_random, TYPE_LABELS

# ── in-memory throttle: group_id → last_sent_unix ────────────────
_last_sent: dict[int, float] = {}

_TABLE = "azkar"


def _get_interval_seconds() -> int:
    """Reads azkar_interval_minutes from bot_constants. Default 10 min."""
    try:
        from core.admin import get_const_int
        return get_const_int("azkar_interval_minutes", 10) * 60
    except Exception:
        return 600


def send_periodic_azkar():
    """
    Called by the IntervalScheduler every 5 minutes.
    Sends an azkar entry to each group where azkar_enabled=1,
    respecting the configured interval per group.
    """
    interval = _get_interval_seconds()
    now      = time.time()

    conn   = get_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT group_id FROM groups WHERE azkar_enabled = 1")
    except Exception:
        return  # column not yet migrated — skip silently
    groups = [row["group_id"] for row in cursor.fetchall()]

    for tg_group_id in groups:
        last = _last_sent.get(tg_group_id, 0)
        if now - last < interval:
            continue

        row = get_random(_TABLE)
        if not row:
            continue

        label = TYPE_LABELS.get(_TABLE, "📿")
        text  = f"{label}\n\n{row['content']}"

        try:
            bot.send_message(tg_group_id, text, parse_mode="HTML")
            _last_sent[tg_group_id] = now
        except Exception as e:
            print(f"[AzkarSender] فشل الإرسال للمجموعة {tg_group_id}: {e}")


# ══════════════════════════════════════════════════════════════════
# Group-level toggle
# ══════════════════════════════════════════════════════════════════

def toggle_azkar(tg_group_id: int, enable: bool) -> bool:
    """Enables or disables periodic azkar for a group. Returns True on success."""
    from database.db_queries.groups_queries import get_internal_group_id
    internal_id = get_internal_group_id(tg_group_id)
    if not internal_id:
        return False
    conn = get_db_conn()
    try:
        conn.execute(
            "UPDATE groups SET azkar_enabled = ? WHERE id = ?",
            (1 if enable else 0, internal_id)
        )
        conn.commit()
    except Exception:
        return False
    if not enable:
        _last_sent.pop(tg_group_id, None)
    return True


def is_azkar_enabled(tg_group_id: int) -> bool:
    from database.db_queries.groups_queries import get_internal_group_id
    internal_id = get_internal_group_id(tg_group_id)
    if not internal_id:
        return False
    conn   = get_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT azkar_enabled FROM groups WHERE id = ?", (internal_id,))
        row = cursor.fetchone()
        return bool(row and row["azkar_enabled"])
    except Exception:
        return False
