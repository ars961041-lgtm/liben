"""
modules/magazine/rankings.py

Computes data-driven rankings from game statistics and publishes
them as magazine posts. Rewards top players automatically.

Called by the unified scheduler:
  - Weekly  → publish_weekly_rankings()   (every Monday midnight Yemen)
  - Monthly → publish_monthly_rankings()  (1st of each month midnight Yemen)

Rankings computed:
  Weekly:
    🏆 أبطال الأسبوع  — top 3 in battles, assets, transfers, spy
    💰 أغنى لاعب       — highest balance
    ⚔️ محارب الأسبوع  — most battles won
    🕵️ جاسوس الأسبوع — most successful spy ops
    📦 أكثر شراءً      — most assets purchased
    😈 أسوأ سمعة       — lowest loyalty score
    😇 أفضل سمعة       — highest loyalty score

  Monthly:
    🏆 بطل الشهر       — most battle wins
    🌍 أقوى تحالف      — highest alliance power
    💎 أثرى لاعب       — highest balance
    🗡 أكثر هجوما     — most attacks launched
    🏙 أكثر إنفاقاً    — most spent on city assets
    🌟 بطل الموسم      — current season leader (battles category)
"""
import time
from database.connection import get_db_conn
from modules.magazine import magazine_db as db
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME
from database.db_queries.analytics_queries import (
    _week_start, _month_start,
    get_top_purchased_assets, get_top_spenders_on_assets,
    get_top_winners, get_most_active_attackers,
    get_top_spy_countries, get_top_senders,
)

# System author ID for auto-generated posts
_SYSTEM_ID = 0

# Reward amounts (can be overridden via bot_constants)
_WEEKLY_REWARD  = 500
_MONTHLY_REWARD = 2000


def _get_reward(key: str, default: int) -> int:
    try:
        from core.admin import get_const_int
        return get_const_int(key, default)
    except Exception:
        return default


def _pay(user_id: int, amount: int, reason: str):
    """Pays a reward to a user and logs it."""
    try:
        from database.db_queries.bank_queries import update_bank_balance
        update_bank_balance(user_id, amount)
    except Exception as e:
        print(f"[Rankings] فشل دفع مكافأة لـ {user_id}: {e}")


def _get_user_name(user_id: int) -> str:
    conn   = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row["name"] if row else f"#{user_id}"


def _get_richest_player() -> dict | None:
    conn   = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ua.user_id, u.name, ua.balance
        FROM user_accounts ua
        JOIN users u ON ua.user_id = u.user_id
        ORDER BY ua.balance DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    return dict(row) if row else None


def _get_reputation_extremes() -> tuple[dict | None, dict | None]:
    """Returns (best_rep, worst_rep) player dicts."""
    conn   = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pr.user_id, u.name, pr.loyalty_score, pr.reputation_title
        FROM player_reputation pr
        JOIN users u ON pr.user_id = u.user_id
        ORDER BY pr.loyalty_score DESC
        LIMIT 1
    """)
    best = dict(cursor.fetchone()) if cursor.fetchone() else None
    # re-fetch since fetchone consumed the row
    cursor.execute("""
        SELECT pr.user_id, u.name, pr.loyalty_score, pr.reputation_title
        FROM player_reputation pr
        JOIN users u ON pr.user_id = u.user_id
        ORDER BY pr.loyalty_score DESC
        LIMIT 1
    """)
    best = dict(cursor.fetchone()) if cursor.fetchone() else None
    cursor.execute("""
        SELECT pr.user_id, u.name, pr.loyalty_score, pr.reputation_title
        FROM player_reputation pr
        JOIN users u ON pr.user_id = u.user_id
        ORDER BY pr.loyalty_score ASC
        LIMIT 1
    """)
    worst = dict(cursor.fetchone()) if cursor.fetchone() else None
    return best, worst


def _get_top_alliance() -> dict | None:
    conn   = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.name, a.power,
               u.name AS leader_name,
               COUNT(am.user_id) AS member_count
        FROM alliances a
        JOIN users u ON a.leader_id = u.user_id
        LEFT JOIN alliance_members am ON am.alliance_id = a.id
        GROUP BY a.id
        ORDER BY a.power DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    return dict(row) if row else None


def _get_season_leader() -> dict | None:
    """Returns the current season's top battle player."""
    conn   = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sh.user_id, u.name, sh.score
        FROM season_history sh
        JOIN seasons s ON sh.season_id = s.id
        JOIN users u ON sh.user_id = u.user_id
        WHERE s.status = 'active' AND sh.category = 'battles'
        ORDER BY sh.rank ASC
        LIMIT 1
    """)
    row = cursor.fetchone()
    return dict(row) if row else None


# ══════════════════════════════════════════════════════════════════
# Weekly rankings
# ══════════════════════════════════════════════════════════════════

def publish_weekly_rankings():
    """
    Computes weekly rankings and publishes them as a magazine post.
    Rewards top players automatically.
    Called every Monday at midnight Yemen time by the daily scheduler.
    """
    from utils.helpers import get_lines
    since  = _week_start()
    reward = _get_reward("weekly_ranking_reward", _WEEKLY_REWARD)
    lines  = [f"🏆 <b>أبطال الأسبوع</b>\n{get_lines()}\n"]

    # ── 💰 أغنى لاعب ──────────────────────────────────────────
    richest = _get_richest_player()
    if richest:
        lines.append(
            f"💰 <b>أغنى لاعب:</b> {richest['name']}\n"
            f"   الرصيد: {richest['balance']:,.0f} {CURRENCY_ARABIC_NAME}\n"
        )
        _pay(richest["user_id"], reward, "أغنى لاعب الأسبوع")

    # ── ⚔️ محارب الأسبوع ──────────────────────────────────────
    winners = get_top_winners(1, since)
    if winners:
        w = winners[0]
        lines.append(
            f"⚔️ <b>محارب الأسبوع:</b> {w['country_name']}\n"
            f"   الانتصارات: {w['wins']} | الغنائم: {w['total_loot']:,.0f} {CURRENCY_ARABIC_NAME}\n"
        )
        # find owner of this country and reward them
        conn   = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT owner_id FROM countries WHERE name = ?", (w["country_name"],))
        row = cursor.fetchone()
        if row:
            _pay(row["owner_id"], reward, "محارب الأسبوع")

    # ── 🕵️ جاسوس الأسبوع ─────────────────────────────────────
    spies = get_top_spy_countries(1, since)
    if spies:
        s = spies[0]
        lines.append(
            f"🕵️ <b>جاسوس الأسبوع:</b> {s['country_name']}\n"
            f"   عمليات ناجحة: {s['successes']} / {s['total_ops']} ({s['success_rate']}%)\n"
        )

    # ── 📦 أكثر شراءً ─────────────────────────────────────────
    top_assets = get_top_purchased_assets(1, since)
    if top_assets:
        a = top_assets[0]
        lines.append(
            f"📦 <b>الأصل الأكثر شراءً:</b> {a['emoji']} {a['name_ar']}\n"
            f"   {a['total_bought']:,} وحدة مشتراة\n"
        )

    # ── 📤 أكثر تحويلاً ───────────────────────────────────────
    senders = get_top_senders(1, since)
    if senders:
        s = senders[0]
        lines.append(
            f"📤 <b>أكثر المحوّلين:</b> {s['name']}\n"
            f"   {s['total_sent']:,.0f} {CURRENCY_ARABIC_NAME} في {s['transfer_count']} تحويل\n"
        )

    # ── 😇 أفضل سمعة / 😈 أسوأ سمعة ─────────────────────────
    best, worst = _get_reputation_extremes()
    if best:
        lines.append(
            f"😇 <b>أفضل سمعة:</b> {best['name']} "
            f"({best['loyalty_score']} نقطة — {best['reputation_title']})\n"
        )
    if worst:
        lines.append(
            f"😈 <b>أسوأ سمعة:</b> {worst['name']} "
            f"({worst['loyalty_score']} نقطة — {worst['reputation_title']})\n"
        )

    lines.append(f"\n🎁 المكافأة لكل بطل: {reward:,} {CURRENCY_ARABIC_NAME}")
    body = "\n".join(lines)
    post_id = db.add_post("🏆 أبطال الأسبوع", body, _SYSTEM_ID)
    print(f"[Rankings] Weekly post #{post_id} published.")


# ══════════════════════════════════════════════════════════════════
# Monthly rankings
# ══════════════════════════════════════════════════════════════════

def publish_monthly_rankings():
    """
    Computes monthly rankings and publishes them as a magazine post.
    Rewards top players automatically.
    Called on the 1st of each month at midnight Yemen time.
    """
    from utils.helpers import get_lines
    since  = _month_start()
    reward = _get_reward("monthly_ranking_reward", _MONTHLY_REWARD)
    lines  = [f"🌟 <b>أبطال الشهر</b>\n{get_lines()}\n"]

    # ── 🏆 بطل الشهر (أكثر انتصارات) ─────────────────────────
    winners = get_top_winners(3, since)
    if winners:
        lines.append("🏆 <b>أكثر الدول انتصاراً:</b>")
        medals = ["🥇", "🥈", "🥉"]
        for i, w in enumerate(winners):
            lines.append(
                f"  {medals[i]} {w['country_name']} — "
                f"{w['wins']} انتصار | {w['total_loot']:,.0f} {CURRENCY_ARABIC_NAME}"
            )
            if i == 0:
                conn   = get_db_conn()
                cursor = conn.cursor()
                cursor.execute("SELECT owner_id FROM countries WHERE name = ?", (w["country_name"],))
                row = cursor.fetchone()
                if row:
                    _pay(row["owner_id"], reward, "بطل الشهر")
        lines.append("")

    # ── 💎 أثرى لاعب ──────────────────────────────────────────
    richest = _get_richest_player()
    if richest:
        lines.append(
            f"💎 <b>أثرى لاعب:</b> {richest['name']}\n"
            f"   {richest['balance']:,.0f} {CURRENCY_ARABIC_NAME}\n"
        )
        _pay(richest["user_id"], reward, "أثرى لاعب الشهر")

    # ── 🗡 أكثر هجوما ────────────────────────────────────────
    attackers = get_most_active_attackers(1, since)
    if attackers:
        a = attackers[0]
        lines.append(
            f"🗡 <b>أكثر الدول هجوماً:</b> {a['country_name']}\n"
            f"   {a['attacks']} هجوم | نسبة الفوز: {a['win_rate']}%\n"
        )

    # ── 🏙 أكثر إنفاقاً على المدن ─────────────────────────────
    spenders = get_top_spenders_on_assets(1, since)
    if spenders:
        s = spenders[0]
        lines.append(
            f"🏙 <b>أكثر المنفقين على المدن:</b> {s['name']}\n"
            f"   {s['total_spent']:,.0f} {CURRENCY_ARABIC_NAME}\n"
        )
        _pay(s["user_id"], reward // 2, "أكثر المنفقين على المدن")

    # ── 🌍 أقوى تحالف ─────────────────────────────────────────
    alliance = _get_top_alliance()
    if alliance:
        lines.append(
            f"🌍 <b>أقوى تحالف:</b> {alliance['name']}\n"
            f"   القوة: {alliance['power']:,.0f} | الأعضاء: {alliance['member_count']}\n"
            f"   القائد: {alliance['leader_name']}\n"
        )

    # ── 🌟 بطل الموسم الحالي ──────────────────────────────────
    season_leader = _get_season_leader()
    if season_leader:
        lines.append(
            f"🌟 <b>متصدر الموسم الحالي:</b> {season_leader['name']}\n"
            f"   النقاط: {season_leader['score']:.0f}\n"
        )

    lines.append(f"\n🎁 مكافأة بطل الشهر: {reward:,} {CURRENCY_ARABIC_NAME}")
    body = "\n".join(lines)
    post_id = db.add_post("🌟 أبطال الشهر", body, _SYSTEM_ID)
    print(f"[Rankings] Monthly post #{post_id} published.")


# ══════════════════════════════════════════════════════════════════
# Scheduler hooks — called from database/daily_tasks.py
# ══════════════════════════════════════════════════════════════════

def maybe_publish_weekly():
    """
    Publishes weekly rankings if today is Monday (weekday=0 in Yemen TZ).
    Called by the daily scheduler at midnight.
    """
    from datetime import datetime, timezone, timedelta
    YEMEN_TZ = timezone(timedelta(hours=3))
    if datetime.now(YEMEN_TZ).weekday() == 0:   # Monday
        try:
            publish_weekly_rankings()
        except Exception as e:
            print(f"[Rankings] Weekly failed: {e}")


def maybe_publish_monthly():
    """
    Publishes monthly rankings if today is the 1st of the month (Yemen TZ).
    Called by the daily scheduler at midnight.
    """
    from datetime import datetime, timezone, timedelta
    YEMEN_TZ = timezone(timedelta(hours=3))
    if datetime.now(YEMEN_TZ).day == 1:
        try:
            publish_monthly_rankings()
        except Exception as e:
            print(f"[Rankings] Monthly failed: {e}")
