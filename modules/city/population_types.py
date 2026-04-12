"""
Population Type System
Splits city population into three functional categories:

  Workers  — drive economy production (income)
  Soldiers — available for military (army capacity)
  Scholars — boost education, XP gain, and efficiency

Distribution formula (daily recalculation):
  base_workers  = 60% of population
  base_soldiers = 20% of population
  base_scholars = 20% of population

Modifiers:
  Education bonus → shifts 5% from workers to scholars per 10% edu_bonus
  War losses      → reduce soldiers by loss_pct × soldiers
  Rebellion stage → shifts 10% from workers to soldiers per stage
  Satisfaction    → low sat shifts scholars → workers (survival mode)

Effects:
  workers  → income multiplier: 1 + (workers/population - 0.6) × 0.5
  soldiers → army capacity bonus: soldiers // 10 extra slots
  scholars → XP multiplier: 1 + (scholars/population - 0.2) × 1.0
             education efficiency: +scholars/population × 0.3

TABLE: city_population_types
  city_id, workers, soldiers, scholars, last_updated
"""
import time
from database.connection import get_db_conn
from database.db_queries.city_progression_queries import get_city_population, get_city_satisfaction
from database.db_queries.assets_queries import calculate_city_effects


def _ensure_table():
    conn = get_db_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS city_population_types (
            city_id      INTEGER PRIMARY KEY,
            workers      INTEGER NOT NULL DEFAULT 0,
            soldiers     INTEGER NOT NULL DEFAULT 0,
            scholars     INTEGER NOT NULL DEFAULT 0,
            last_updated INTEGER DEFAULT (strftime('%s','now')),
            FOREIGN KEY (city_id) REFERENCES cities(id)
        )
    """)
    conn.commit()


def get_population_types(city_id: int) -> dict:
    """Returns current population type breakdown."""
    try:
        _ensure_table()
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT workers, soldiers, scholars FROM city_population_types WHERE city_id = ?",
            (city_id,)
        )
        row = cursor.fetchone()
        if row:
            return {"workers": row[0], "soldiers": row[1], "scholars": row[2]}
    except Exception:
        pass
    # fallback: compute from population
    return _compute_distribution(city_id)


def recalculate_population_types(city_id: int) -> dict:
    """Recompute and store population type distribution."""
    dist = _compute_distribution(city_id)
    try:
        _ensure_table()
        conn = get_db_conn()
        now = int(time.time())
        conn.execute("""
            INSERT INTO city_population_types (city_id, workers, soldiers, scholars, last_updated)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(city_id) DO UPDATE SET
                workers = ?, soldiers = ?, scholars = ?, last_updated = ?
        """, (city_id, dist["workers"], dist["soldiers"], dist["scholars"], now,
              dist["workers"], dist["soldiers"], dist["scholars"], now))
        conn.commit()
    except Exception as e:
        print(f"[pop_types] save failed city={city_id}: {e}")
    return dist


def _compute_distribution(city_id: int) -> dict:
    """Compute worker/soldier/scholar split from city conditions."""
    pop = get_city_population(city_id)
    if pop <= 0:
        return {"workers": 0, "soldiers": 0, "scholars": 0}

    effects = calculate_city_effects(city_id)
    sat = get_city_satisfaction(city_id)
    edu_bonus = effects.get("education_bonus", 0.0)

    # base split
    w_pct = 0.60
    s_pct = 0.20
    sc_pct = 0.20

    # education shifts workers → scholars (up to 10%)
    edu_shift = min(0.10, edu_bonus * 0.5)
    w_pct  -= edu_shift
    sc_pct += edu_shift

    # low satisfaction shifts scholars → workers (survival mode)
    if sat < 40:
        survival_shift = min(0.10, (40 - sat) / 40 * 0.10)
        sc_pct -= survival_shift
        w_pct  += survival_shift

    # rebellion shifts workers → soldiers
    try:
        from modules.city.rebellion_engine import get_rebellion_stage
        stage = get_rebellion_stage(city_id)
        if stage > 0:
            rebel_shift = min(0.15, stage * 0.05)
            w_pct  -= rebel_shift
            s_pct  += rebel_shift
    except Exception:
        pass

    # clamp all to [0.05, 0.85]
    w_pct  = max(0.05, min(0.85, w_pct))
    s_pct  = max(0.05, min(0.85, s_pct))
    sc_pct = max(0.05, min(0.85, sc_pct))

    # normalize to sum = 1
    total = w_pct + s_pct + sc_pct
    w_pct  /= total
    s_pct  /= total
    sc_pct /= total

    return {
        "workers":  int(pop * w_pct),
        "soldiers": int(pop * s_pct),
        "scholars": int(pop * sc_pct),
    }


def get_worker_income_bonus(city_id: int) -> float:
    """
    Income multiplier from worker ratio.
    Base ratio = 60%. Each 1% above → +0.5% income.
    """
    dist = get_population_types(city_id)
    pop  = get_city_population(city_id)
    if pop <= 0:
        return 0.0
    ratio = dist["workers"] / pop
    return max(0.0, (ratio - 0.60) * 0.5)


def get_scholar_xp_multiplier(city_id: int) -> float:
    """
    XP multiplier from scholar ratio.
    Base ratio = 20%. Each 1% above → +1% XP.
    """
    dist = get_population_types(city_id)
    pop  = get_city_population(city_id)
    if pop <= 0:
        return 1.0
    ratio = dist["scholars"] / pop
    return 1.0 + max(0.0, (ratio - 0.20) * 1.0)


def get_soldier_army_bonus(city_id: int) -> int:
    """Extra army capacity slots from soldier population."""
    dist = get_population_types(city_id)
    return dist["soldiers"] // 10


def apply_war_soldier_loss(city_id: int, loss_pct: float):
    """Reduce soldier count after a battle."""
    try:
        _ensure_table()
        dist = get_population_types(city_id)
        loss = int(dist["soldiers"] * loss_pct / 100)
        new_soldiers = max(0, dist["soldiers"] - loss)
        conn = get_db_conn()
        conn.execute(
            "UPDATE city_population_types SET soldiers = ? WHERE city_id = ?",
            (new_soldiers, city_id)
        )
        conn.commit()
    except Exception:
        pass
