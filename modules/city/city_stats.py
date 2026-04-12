"""
City Stats Engine
Computes and updates population, satisfaction, XP, and level bonuses for all cities.
Called from daily_tasks.py.

═══════════════════════════════════════════════════════════
SYSTEM 1 — Population → Income & Army Capacity
  income_pop_bonus = min(0.30, population / 1_000_000 × 0.30)
  army_capacity    = 500 + population // 200   (cap: 50_000)

SYSTEM 2 — City Level Bonuses (per level above 1)
  production_bonus = (level - 1) × 0.05   → +5% income per level
  military_bonus   = (level - 1) × 0.03   → +3% power per level

SYSTEM 3 — Satisfaction Thresholds & Consequences
  ≥ 60  → normal / bonus zone
  40–59 → mild penalty: income ×0.85
  20–39 → moderate: income ×0.70, population shrinks 0.2%/day
  < 20  → severe: income ×0.50, population shrinks 0.5%/day, rebellion debuff

POPULATION GROWTH (daily):
  base_growth = population × 0.005
  edu_mult    = 1 + education_bonus × 2
  sat_mult    = satisfaction / 50   (capped 0.1–2.0)
  growth      = base_growth × edu_mult × sat_mult
  cap: 10_000_000

SATISFACTION TARGET (daily drift ±5):
  target = 50 + health_bonus×100 + income_ratio×20 - war_penalty
  income_ratio = clamp((income - maintenance) / max(1, income), -1, 1)
  war_penalty  = recent_losses × 5  (max 30)

XP GAINS (daily tick):
  base = 10 + min(50, asset_levels×0.5) + edu_bonus×20 + tasks×10
  battle win: 50 + (1 - loss_pct)×30
  battle loss: 10
═══════════════════════════════════════════════════════════
"""
import time
from database.connection import get_db_conn
from database.db_queries.assets_queries import calculate_city_effects
from database.db_queries.city_progression_queries import (
    get_city_xp, add_city_xp,
    get_city_satisfaction, set_city_satisfaction,
    get_city_population, update_city_population,
)

# ── Satisfaction thresholds ──────────────────────────────────────
SAT_MILD_THRESHOLD     = 60   # below this → mild penalty
SAT_MODERATE_THRESHOLD = 40   # below this → moderate penalty
SAT_SEVERE_THRESHOLD   = 20   # below this → severe + rebellion risk

# ── Army capacity constants ──────────────────────────────────────
ARMY_BASE_CAPACITY     = 500
ARMY_POP_DIVISOR       = 200   # 1 troop slot per 200 population
ARMY_MAX_CAPACITY      = 50_000


# ══════════════════════════════════════════
# 📊 Level Bonuses
# ══════════════════════════════════════════

def get_level_bonuses(city_id: int) -> dict:
    """
    Returns production and military bonuses from city level.
      production_bonus = (level - 1) × 0.05   (e.g. level 5 → +20%)
      military_bonus   = (level - 1) × 0.03   (e.g. level 5 → +12%)
    """
    xp_data = get_city_xp(city_id)
    level = xp_data.get("level", 1)
    production = (level - 1) * 0.05
    military   = (level - 1) * 0.03
    return {
        "level": level,
        "production_bonus": round(production, 4),
        "military_bonus":   round(military, 4),
    }


# ══════════════════════════════════════════
# 👥 Population → Income & Army Capacity
# ══════════════════════════════════════════

def get_population_income_bonus(city_id: int) -> float:
    """
    Returns income multiplier from population.
    Formula: min(0.30, population / 1_000_000 × 0.30)
    1M pop → +30% income. Scales linearly below that.
    """
    pop = get_city_population(city_id)
    return min(0.30, pop / 1_000_000 * 0.30)


def get_army_capacity(city_id: int) -> int:
    """
    Max troops a city can field based on population.
    Formula: 500 + population // 200, capped at 50_000.
    """
    pop = get_city_population(city_id)
    return min(ARMY_MAX_CAPACITY, ARMY_BASE_CAPACITY + pop // ARMY_POP_DIVISOR)


# ══════════════════════════════════════════
# 🧠 Satisfaction → Income Modifier
# ══════════════════════════════════════════

def get_satisfaction_income_modifier(city_id: int) -> float:
    """
    Returns income multiplier based on rebellion stage and satisfaction.
    Stage 3 (full rebellion) → 0.0
    Stage 2 → 0.40
    Stage 1 → 0.70
    ≥ 60    → 1.0 to 1.20 (bonus zone)
    40–59   → 0.85
    20–39   → 0.70
    """
    try:
        from modules.city.rebellion_engine import get_rebellion_income_modifier
        mod = get_rebellion_income_modifier(city_id)
        if mod < 1.0:
            return mod
    except Exception:
        pass

    score = get_city_satisfaction(city_id)
    if score >= SAT_MILD_THRESHOLD:
        return 1.0 + (score - SAT_MILD_THRESHOLD) / 40.0 * 0.20
    elif score >= SAT_MODERATE_THRESHOLD:
        return 0.85
    elif score >= SAT_SEVERE_THRESHOLD:
        return 0.70
    else:
        return 0.50


def get_satisfaction_status(city_id: int) -> dict:
    """Returns satisfaction score, tier label, active effects, and rebellion stage."""
    try:
        from modules.city.rebellion_engine import get_rebellion_status
        reb = get_rebellion_status(city_id)
        stage = reb["stage"]
    except Exception:
        reb = {"stage": 0, "label": "مستقرة", "effects": []}
        stage = 0

    score = get_city_satisfaction(city_id)

    if stage >= 3:
        return {"score": score, "tier": "تمرد كامل", "effects": reb["effects"], "rebellion": True, "stage": stage}
    elif stage == 2:
        return {"score": score, "tier": "أعمال شغب", "effects": reb["effects"], "rebellion": False, "stage": stage}
    elif stage == 1:
        return {"score": score, "tier": "اضطرابات", "effects": reb["effects"], "rebellion": False, "stage": stage}
    elif score >= SAT_MILD_THRESHOLD:
        tier = "مستقرة" if score < 75 else "مزدهرة"
        effects = [] if score < 75 else ["دخل +20%"]
    elif score >= SAT_MODERATE_THRESHOLD:
        tier = "متوترة"
        effects = ["دخل -15%"]
    elif score >= SAT_SEVERE_THRESHOLD:
        tier = "غاضبة"
        effects = ["دخل -30%", "هجرة سكانية"]
    else:
        tier = "ثورة"
        effects = ["دخل -50%", "هجرة سكانية شديدة", "خطر تمرد"]

    return {"score": score, "tier": tier, "effects": effects, "rebellion": False, "stage": stage}


# ══════════════════════════════════════════
# 📈 Population Growth (daily tick)
# ══════════════════════════════════════════

def tick_population(city_id: int):
    """Run daily population growth/shrink for one city."""
    from modules.city.city_simulation import get_population_capacity, is_city_in_rebellion
    effects = calculate_city_effects(city_id)
    population = get_city_population(city_id)
    satisfaction = get_city_satisfaction(city_id)

    # no growth during rebellion
    if is_city_in_rebellion(city_id):
        return population

    pop_cap = get_population_capacity(city_id)

    edu_mult = 1.0 + effects.get("education_bonus", 0.0) * 2.0
    sat_mult = max(0.1, min(2.0, satisfaction / 50.0))

    if satisfaction >= SAT_MODERATE_THRESHOLD:
        if population >= pop_cap * 0.95:
            # at capacity — no growth
            return population
        base_growth = population * 0.005
        growth = int(base_growth * edu_mult * sat_mult)
        growth = max(1, growth)
        new_pop = min(pop_cap, population + growth)
    elif satisfaction >= SAT_SEVERE_THRESHOLD:
        shrink = int(population * 0.002)
        new_pop = max(100, population - shrink)
    else:
        shrink = int(population * 0.005)
        new_pop = max(100, population - shrink)

    update_city_population(city_id, new_pop)
    return new_pop


# ══════════════════════════════════════════
# 🧠 Satisfaction (daily tick)
# ══════════════════════════════════════════

def tick_satisfaction(city_id: int):
    """Recalculate and drift satisfaction toward target for one city."""
    effects = calculate_city_effects(city_id)
    current = get_city_satisfaction(city_id)

    income = effects.get("income", 0.0)
    maintenance = effects.get("maintenance", 0.0)
    health_bonus = effects.get("health_bonus", 0.0)

    income_ratio = max(-1.0, min(1.0, (income - maintenance) / max(1.0, income)))
    target = 50.0 + health_bonus * 100.0 + income_ratio * 20.0
    war_penalty = _get_war_penalty(city_id)
    target = max(0.0, min(100.0, target - war_penalty))

    # drift 5 points per day toward target
    if current < target:
        new_score = min(target, current + 5.0)
    else:
        new_score = max(target, current - 5.0)

    set_city_satisfaction(city_id, new_score)
    return new_score


def apply_war_satisfaction_penalty(city_id: int, loss_pct: float):
    """Called after a battle loss. Reduces satisfaction based on casualties."""
    penalty = min(20.0, loss_pct * 0.3)
    from database.db_queries.city_progression_queries import adjust_city_satisfaction
    adjust_city_satisfaction(city_id, -penalty)


def _get_war_penalty(city_id: int) -> float:
    """Returns accumulated war penalty from recent losses (decays 5/day)."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        seven_days_ago = int(time.time()) - 7 * 86400
        cursor.execute("""
            SELECT COUNT(*) FROM battle_history bh
            JOIN cities c ON c.country_id = bh.loser_country_id
            WHERE c.id = ? AND bh.ended_at >= ?
        """, (city_id, seven_days_ago))
        row = cursor.fetchone()
        losses = row[0] if row else 0
        return min(30.0, losses * 5.0)
    except Exception:
        return 0.0


# ══════════════════════════════════════════
# ⭐ XP (daily tick)
# ══════════════════════════════════════════

def tick_xp(city_id: int):
    """Award daily XP to a city based on its development."""
    effects = calculate_city_effects(city_id)
    edu_bonus = effects.get("education_bonus", 0.0)
    xp = 10.0

    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(level * quantity), 0) FROM city_assets WHERE city_id = ?
        """, (city_id,))
        row = cursor.fetchone()
        xp += min(50.0, (row[0] if row else 0) * 0.5)
    except Exception:
        pass

    xp += edu_bonus * 20.0

    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM daily_tasks WHERE city_id = ? AND status = 'completed'
        """, (city_id,))
        row = cursor.fetchone()
        xp += min(40.0, (row[0] if row else 0) * 10.0)
    except Exception:
        pass

    return add_city_xp(city_id, xp)


def award_battle_xp(city_id: int, won: bool, loss_pct: float):
    """Award XP after a battle."""
    xp = (50.0 + max(0, (1.0 - loss_pct / 100.0)) * 30.0) if won else 10.0
    return add_city_xp(city_id, xp)


# ══════════════════════════════════════════
# 🔄 Daily tick for all cities
# ══════════════════════════════════════════

def run_city_progression_tick():
    """Called from daily_tasks. Runs population, satisfaction, XP for all cities."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM cities")
    cities = [row[0] for row in cursor.fetchall()]

    for city_id in cities:
        try:
            tick_population(city_id)
        except Exception as e:
            print(f"[city_stats] population tick failed city={city_id}: {e}")
        try:
            tick_satisfaction(city_id)
        except Exception as e:
            print(f"[city_stats] satisfaction tick failed city={city_id}: {e}")
        try:
            tick_xp(city_id)
        except Exception as e:
            print(f"[city_stats] xp tick failed city={city_id}: {e}")
