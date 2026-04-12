"""
news_generator.py — Public API for generating news posts from game events.

Usage:
    from modules.magazine.news_generator import add_news_event

    add_news_event("war_start", war_id=5, attacker="تحالف النور", ...)

Each function:
  1. Checks the dedup cooldown.
  2. Renders a randomized template.
  3. Saves to news_posts.
  4. Broadcasts to opted-in groups (non-blocking).
  5. Also saves to legacy magazine_posts for backward compatibility.
"""
import time
from modules.magazine import news_db as db
from modules.magazine import news_templates as tpl
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

_SYSTEM_ID = 0


def _post(event_type: str, event_ref: str, importance: str,
          category: str, **kwargs) -> int | None:
    """
    Core helper: dedup check → render → save → broadcast.
    Returns post_id or None if skipped (cooldown).
    """
    event_key = f"{event_type}:{event_ref}" if event_ref else event_type
    if not db.can_post_event(event_key):
        return None

    rendered = tpl.render(event_type, currency=CURRENCY_ARABIC_NAME, **kwargs)
    if not rendered:
        return None

    post_id = db.add_news_post(
        title=rendered["title"],
        body=rendered["body"],
        importance=importance,
        category=category,
        event_type=event_type,
        event_ref=str(event_ref),
        author_id=_SYSTEM_ID,
    )
    db.mark_event_posted(event_key)

    # Backward-compat: also add to legacy magazine_posts
    try:
        from modules.magazine import magazine_db as legacy_db
        legacy_db.add_post(rendered["title"], rendered["body"], _SYSTEM_ID)
    except Exception:
        pass

    # Broadcast to groups (non-blocking)
    try:
        from modules.magazine.news_broadcaster import broadcast_news
        broadcast_news(rendered["title"], rendered["body"], importance)
    except Exception:
        pass

    return post_id


# ══════════════════════════════════════════
# ⚔️ War Events
# ══════════════════════════════════════════

def on_war_started(war_id: int, attacker: str, defender: str,
                   war_type: str, reason: str = "", threshold: int = 60):
    """Called when a political war enters the voting phase."""
    war_type_ar = {
        "country_vs_country":  "دولة ضد دولة",
        "alliance_vs_alliance": "تحالف ضد تحالف",
        "hybrid":               "هجين",
    }.get(war_type, war_type)

    _post("war_start", f"war_{war_id}", "HIGH", "war",
          attacker=attacker, defender=defender,
          war_type=war_type_ar, reason=reason or "لم يُذكر",
          threshold=threshold, war_id=war_id)


def on_war_ended(war_id: int, winner_side: str,
                 attacker: str, defender: str,
                 att_power: float, def_power: float, loot: float):
    """Called when a political war resolves."""
    if winner_side == "draw":
        _post("war_end", f"war_end_{war_id}", "HIGH", "war",
              war_id=war_id, attacker=attacker, defender=defender,
              att_power=att_power, def_power=def_power,
              winner="", loser="", winner_power=0, loser_power=0, loot=0)
        return

    if winner_side == "attacker":
        winner, loser = attacker, defender
        winner_power, loser_power = att_power, def_power
    else:
        winner, loser = defender, attacker
        winner_power, loser_power = def_power, att_power

    power_ratio = winner_power / max(1, loser_power)
    _post("war_end", f"war_end_{war_id}", "HIGH", "war",
          war_id=war_id, winner=winner, loser=loser,
          winner_power=winner_power, loser_power=loser_power,
          loot=loot, power_ratio=power_ratio,
          attacker=attacker, defender=defender,
          att_power=att_power, def_power=def_power)


def on_war_betrayal(war_id: int, country: str, alliance: str):
    """Called when a country withdraws from an active war."""
    _post("war_betrayal", f"betray_{war_id}_{country}", "HIGH", "war",
          war_id=war_id, country=country, alliance=alliance)


# ══════════════════════════════════════════
# 🏰 Alliance Events
# ══════════════════════════════════════════

def on_alliance_victory_streak(alliance_id: int, alliance_name: str,
                                streak: int, bonus_pct: int):
    """Called after record_war_result when streak >= 2."""
    if streak < 2:
        return
    _post("alliance_victory", f"streak_{alliance_id}", "MEDIUM", "alliance",
          alliance=alliance_name, streak=streak, bonus_pct=bonus_pct)


def on_alliance_collapsed(alliance_id: int, alliance_name: str,
                           member_count: int, created_at: int):
    """Called when an alliance is dissolved."""
    age_days = max(0, (int(time.time()) - created_at) // 86400)
    _post("alliance_collapse", f"collapse_{alliance_id}", "CRITICAL", "alliance",
          alliance=alliance_name, member_count=member_count, age_days=age_days)


# ══════════════════════════════════════════
# 💰 Economy Events
# ══════════════════════════════════════════

def on_richest_player_changed(player_name: str, balance: float):
    """Called when the richest player changes."""
    _post("richest_change", "richest", "MEDIUM", "economy",
          player=player_name, balance=balance)


def on_treasury_milestone(alliance_id: int, alliance_name: str, amount: float):
    """Called when an alliance treasury crosses a round milestone."""
    _post("treasury_milestone", f"treasury_{alliance_id}_{int(amount//10000)}",
          "MEDIUM", "economy",
          alliance=alliance_name, amount=amount)


def on_economy_shock(country_name: str, amount: float, reason: str = ""):
    """Called on major economic loss (e.g. war loot)."""
    _post("economy_shock", f"shock_{country_name}_{int(time.time()//3600)}",
          "MEDIUM", "economy",
          country=country_name, amount=amount,
          reason=reason or "خسارة في المعركة")


# ══════════════════════════════════════════
# 🔴 Rebellion Events
# ══════════════════════════════════════════

def on_rebellion(city_name: str, country_name: str, satisfaction: int):
    """Called when a city rebellion is triggered."""
    _post("rebellion", f"rebel_{city_name}", "HIGH", "rebellion",
          city=city_name, country=country_name, satisfaction=satisfaction)


# ══════════════════════════════════════════
# 🌍 Global Events
# ══════════════════════════════════════════

def on_global_event(event_name: str, description: str,
                    duration: str = "24 ساعة", effect: str = ""):
    """Called when a global game event is triggered."""
    _post("global_event", f"gevent_{event_name}", "HIGH", "event",
          event_name=event_name, description=description,
          duration=duration, effect=effect or "يؤثر على جميع اللاعبين")


# ══════════════════════════════════════════
# 🏆 Rankings (called from rankings.py)
# ══════════════════════════════════════════

def on_weekly_rankings(body: str):
    """Wraps the weekly rankings post in the news system."""
    _post("rankings_weekly", "weekly", "MEDIUM", "rankings", body=body)


def on_monthly_rankings(body: str):
    """Wraps the monthly rankings post in the news system."""
    _post("rankings_monthly", "monthly", "HIGH", "rankings", body=body)
