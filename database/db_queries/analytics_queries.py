"""
database/db_queries/analytics_queries.py

Analytics queries that mine history/log tables to produce
leaderboards, trends, and player statistics.

Source tables used:
  asset_log       — every buy/upgrade action on city assets
  bank_transfers  — every currency transfer between players
  battle_history  — completed country battles
  war_costs_log   — currency spent on war actions
  spy_operations  — spy missions attempted/succeeded
  exploration_log — exploration missions run by countries
"""
import time
from database.connection import get_db_conn


# ── Time helpers ─────────────────────────────────────────────────

def _month_start() -> int:
    """Unix timestamp of the first second of the current month (UTC)."""
    import datetime
    now = datetime.datetime.utcnow()
    return int(datetime.datetime(now.year, now.month, 1).timestamp())


def _week_start() -> int:
    """Unix timestamp of the most recent Monday 00:00 UTC."""
    import datetime
    now = datetime.datetime.utcnow()
    monday = now - datetime.timedelta(days=now.weekday())
    return int(datetime.datetime(monday.year, monday.month, monday.day).timestamp())


def _days_ago(n: int) -> int:
    return int(time.time()) - n * 86400


# ══════════════════════════════════════════════════════════════════
# 📦 Asset analytics  (source: asset_log)
# ══════════════════════════════════════════════════════════════════

def get_top_purchased_assets(limit: int = 10, since: int = None) -> list[dict]:
    """
    Most purchased assets (action='buy') ranked by total units bought.
    since — optional Unix timestamp lower bound (default: all time).
    Returns: [{name_ar, emoji, total_bought, total_spent}]
    """
    conn   = get_db_conn()
    cursor = conn.cursor()
    since  = since or 0
    cursor.execute("""
        SELECT
            a.name_ar,
            a.emoji,
            SUM(al.quantity)  AS total_bought,
            SUM(al.cost)      AS total_spent
        FROM asset_log al
        JOIN assets a ON al.asset_id = a.id
        WHERE al.action = 'buy' AND al.ts >= ?
        GROUP BY al.asset_id
        ORDER BY total_bought DESC
        LIMIT ?
    """, (since, limit))
    return [dict(r) for r in cursor.fetchall()]


def get_top_upgraded_assets(limit: int = 10, since: int = None) -> list[dict]:
    """
    Most upgraded assets ranked by total upgrade operations.
    Returns: [{name_ar, emoji, total_upgrades, total_spent}]
    """
    conn   = get_db_conn()
    cursor = conn.cursor()
    since  = since or 0
    cursor.execute("""
        SELECT
            a.name_ar,
            a.emoji,
            COUNT(*)         AS total_upgrades,
            SUM(al.cost)     AS total_spent
        FROM asset_log al
        JOIN assets a ON al.asset_id = a.id
        WHERE al.action = 'upgrade' AND al.ts >= ?
        GROUP BY al.asset_id
        ORDER BY total_upgrades DESC
        LIMIT ?
    """, (since, limit))
    return [dict(r) for r in cursor.fetchall()]


def get_top_spenders_on_assets(limit: int = 10, since: int = None) -> list[dict]:
    """
    Players who spent the most on city assets (buy + upgrade).
    Returns: [{name, user_id, total_spent}]
    """
    conn   = get_db_conn()
    cursor = conn.cursor()
    since  = since or 0
    cursor.execute("""
        SELECT
            u.name,
            al.user_id,
            SUM(al.cost) AS total_spent
        FROM asset_log al
        JOIN users u ON al.user_id = u.user_id
        WHERE al.ts >= ?
        GROUP BY al.user_id
        ORDER BY total_spent DESC
        LIMIT ?
    """, (since, limit))
    return [dict(r) for r in cursor.fetchall()]


def get_city_asset_history(city_id: int, limit: int = 20) -> list[dict]:
    """
    Recent asset actions for a specific city.
    Returns: [{name_ar, emoji, action, quantity, from_level, to_level, cost, ts}]
    """
    conn   = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            a.name_ar, a.emoji,
            al.action, al.quantity,
            al.from_level, al.to_level,
            al.cost, al.ts
        FROM asset_log al
        JOIN assets a ON al.asset_id = a.id
        WHERE al.city_id = ?
        ORDER BY al.ts DESC
        LIMIT ?
    """, (city_id, limit))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════════════════════════════
# 💸 Bank transfer analytics  (source: bank_transfers)
# ══════════════════════════════════════════════════════════════════

def get_top_senders(limit: int = 10, since: int = None) -> list[dict]:
    """
    Players who sent the most currency via transfers.
    Returns: [{name, user_id, total_sent, transfer_count}]
    """
    conn   = get_db_conn()
    cursor = conn.cursor()
    since  = since or 0
    cursor.execute("""
        SELECT
            u.name,
            bt.from_user_id AS user_id,
            SUM(bt.amount)  AS total_sent,
            COUNT(*)        AS transfer_count
        FROM bank_transfers bt
        JOIN users u ON bt.from_user_id = u.user_id
        WHERE bt.created_at >= ?
        GROUP BY bt.from_user_id
        ORDER BY total_sent DESC
        LIMIT ?
    """, (since, limit))
    return [dict(r) for r in cursor.fetchall()]


def get_top_receivers(limit: int = 10, since: int = None) -> list[dict]:
    """
    Players who received the most currency via transfers.
    Returns: [{name, user_id, total_received, transfer_count}]
    """
    conn   = get_db_conn()
    cursor = conn.cursor()
    since  = since or 0
    cursor.execute("""
        SELECT
            u.name,
            bt.to_user_id   AS user_id,
            SUM(bt.amount)  AS total_received,
            COUNT(*)        AS transfer_count
        FROM bank_transfers bt
        JOIN users u ON bt.to_user_id = u.user_id
        WHERE bt.created_at >= ?
        GROUP BY bt.to_user_id
        ORDER BY total_received DESC
        LIMIT ?
    """, (since, limit))
    return [dict(r) for r in cursor.fetchall()]


def get_transfer_volume_summary(since: int = None) -> dict:
    """
    Total transfer volume, count, and fees collected in a period.
    Returns: {total_volume, total_count, total_fees}
    """
    conn   = get_db_conn()
    cursor = conn.cursor()
    since  = since or 0
    cursor.execute("""
        SELECT
            COALESCE(SUM(amount), 0) AS total_volume,
            COUNT(*)                 AS total_count,
            COALESCE(SUM(fee), 0)    AS total_fees
        FROM bank_transfers
        WHERE created_at >= ?
    """, (since,))
    row = cursor.fetchone()
    return dict(row) if row else {"total_volume": 0, "total_count": 0, "total_fees": 0}


# ══════════════════════════════════════════════════════════════════
# ⚔️ Battle analytics  (source: battle_history)
# ══════════════════════════════════════════════════════════════════

def get_top_winners(limit: int = 10, since: int = None) -> list[dict]:
    """
    Countries with the most battle wins.
    Returns: [{country_name, wins, total_loot}]
    """
    conn   = get_db_conn()
    cursor = conn.cursor()
    since  = since or 0
    cursor.execute("""
        SELECT
            c.name          AS country_name,
            COUNT(*)        AS wins,
            SUM(bh.loot)    AS total_loot
        FROM battle_history bh
        JOIN countries c ON bh.winner_country_id = c.id
        WHERE bh.created_at >= ?
        GROUP BY bh.winner_country_id
        ORDER BY wins DESC
        LIMIT ?
    """, (since, limit))
    return [dict(r) for r in cursor.fetchall()]


def get_most_active_attackers(limit: int = 10, since: int = None) -> list[dict]:
    """
    Countries that launched the most attacks (win or lose).
    Returns: [{country_name, attacks, wins, win_rate}]
    """
    conn   = get_db_conn()
    cursor = conn.cursor()
    since  = since or 0
    cursor.execute("""
        SELECT
            c.name AS country_name,
            COUNT(*) AS attacks,
            SUM(CASE WHEN bh.winner_country_id = bh.attacker_country_id THEN 1 ELSE 0 END) AS wins
        FROM battle_history bh
        JOIN countries c ON bh.attacker_country_id = c.id
        WHERE bh.created_at >= ?
        GROUP BY bh.attacker_country_id
        ORDER BY attacks DESC
        LIMIT ?
    """, (since, limit))
    rows = [dict(r) for r in cursor.fetchall()]
    for r in rows:
        r["win_rate"] = round(r["wins"] / r["attacks"] * 100, 1) if r["attacks"] else 0
    return rows


def get_battle_summary(since: int = None) -> dict:
    """
    Overall battle statistics for a period.
    Returns: {total_battles, total_loot, avg_duration_sec}
    """
    conn   = get_db_conn()
    cursor = conn.cursor()
    since  = since or 0
    cursor.execute("""
        SELECT
            COUNT(*)                        AS total_battles,
            COALESCE(SUM(loot), 0)          AS total_loot,
            COALESCE(AVG(duration_seconds), 0) AS avg_duration_sec
        FROM battle_history
        WHERE created_at >= ?
    """, (since,))
    row = cursor.fetchone()
    return dict(row) if row else {"total_battles": 0, "total_loot": 0, "avg_duration_sec": 0}


# ══════════════════════════════════════════════════════════════════
# 🕵️ Spy analytics  (source: spy_operations)
# ══════════════════════════════════════════════════════════════════

def get_top_spy_countries(limit: int = 10, since: int = None) -> list[dict]:
    """
    Countries with the most successful spy operations.
    Returns: [{country_name, successes, total_ops, success_rate}]
    """
    conn   = get_db_conn()
    cursor = conn.cursor()
    since  = since or 0
    cursor.execute("""
        SELECT
            c.name AS country_name,
            COUNT(*) AS total_ops,
            SUM(CASE WHEN so.result IN ('success','partial') THEN 1 ELSE 0 END) AS successes
        FROM spy_operations so
        JOIN countries c ON so.attacker_country_id = c.id
        WHERE so.created_at >= ?
        GROUP BY so.attacker_country_id
        ORDER BY successes DESC
        LIMIT ?
    """, (since, limit))
    rows = [dict(r) for r in cursor.fetchall()]
    for r in rows:
        r["success_rate"] = round(r["successes"] / r["total_ops"] * 100, 1) if r["total_ops"] else 0
    return rows


# ══════════════════════════════════════════════════════════════════
# 🗺️ Exploration analytics  (source: exploration_log)
# ══════════════════════════════════════════════════════════════════

def get_top_explorers(limit: int = 10, since: int = None) -> list[dict]:
    """
    Countries that ran the most exploration missions.
    Returns: [{country_name, total_missions, discoveries, total_cost}]
    """
    conn   = get_db_conn()
    cursor = conn.cursor()
    since  = since or 0
    cursor.execute("""
        SELECT
            c.name AS country_name,
            COUNT(*) AS total_missions,
            SUM(CASE WHEN el.result = 'found' THEN 1 ELSE 0 END) AS discoveries,
            SUM(el.cost) AS total_cost
        FROM exploration_log el
        JOIN countries c ON el.country_id = c.id
        WHERE el.created_at >= ?
        GROUP BY el.country_id
        ORDER BY total_missions DESC
        LIMIT ?
    """, (since, limit))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════════════════════════════
# 💰 War spending analytics  (source: war_costs_log)
# ══════════════════════════════════════════════════════════════════

def get_top_war_spenders(limit: int = 10, since: int = None) -> list[dict]:
    """
    Players who spent the most on war actions.
    Returns: [{name, user_id, total_spent, action_count}]
    """
    conn   = get_db_conn()
    cursor = conn.cursor()
    since  = since or 0
    cursor.execute("""
        SELECT
            u.name,
            wc.user_id,
            SUM(wc.amount)  AS total_spent,
            COUNT(*)        AS action_count
        FROM war_costs_log wc
        JOIN users u ON wc.user_id = u.user_id
        WHERE wc.created_at >= ?
        GROUP BY wc.user_id
        ORDER BY total_spent DESC
        LIMIT ?
    """, (since, limit))
    return [dict(r) for r in cursor.fetchall()]
