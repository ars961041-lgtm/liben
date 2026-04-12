"""
City Simulation Engine
Orchestrates all simulation systems for daily ticks.

Systems:
  1. Rebellion (progressive stages via rebellion_engine.py)
  2. Smart Migration (intra-country + inter-country)
  3. Population Capacity (infra-based cap)
  4. Population Maintenance (daily upkeep)
  5. Population Types (recalculation)
  6. Internal Economy (taxes + production + consumption)
  7. Government Decisions (expire old ones)
"""
import time
from database.connection import get_db_conn
from database.db_queries.city_progression_queries import (
    get_city_satisfaction, adjust_city_satisfaction,
    get_city_population, update_city_population,
)

# ── Constants ────────────────────────────────────────────────────
BASE_POP_CAP           = 10_000
INFRA_CAP_MULTIPLIER   = 500
UPKEEP_PER_CAPITA      = 0.001
MIGRATION_RATE         = 0.02
MIGRATION_MAX          = 500
INTER_COUNTRY_MIGRATION_MAX = 200   # smaller cap for cross-country migration
INTER_COUNTRY_SAT_GAP  = 25        # minimum satisfaction gap for cross-country migration
INTER_COUNTRY_COOLDOWN = 7 * 86400  # 7 days between cross-country migrations


# ══════════════════════════════════════════
# 🔴 Rebellion (delegates to rebellion_engine)
# ══════════════════════════════════════════

def is_city_in_rebellion(city_id: int) -> bool:
    """Backward-compat wrapper — stage 3 = full rebellion."""
    try:
        from modules.city.rebellion_engine import is_city_in_rebellion as _r
        return _r(city_id)
    except Exception:
        return False


def get_rebellion_army_penalty(city_id: int) -> float:
    try:
        from modules.city.rebellion_engine import get_rebellion_army_penalty as _r
        return _r(city_id)
    except Exception:
        return 0.0


def is_construction_blocked(city_id: int) -> bool:
    try:
        from modules.city.rebellion_engine import is_construction_blocked as _r
        return _r(city_id)
    except Exception:
        return False


# ══════════════════════════════════════════
# 🏗 Population Capacity
# ══════════════════════════════════════════

def get_population_capacity(city_id: int) -> int:
    try:
        from database.db_queries.assets_queries import calculate_city_effects
        effects = calculate_city_effects(city_id)
        infra = effects.get("infrastructure", 0.0)
        base = int(BASE_POP_CAP + infra * INFRA_CAP_MULTIPLIER)

        # Government decision bonus
        try:
            conn = get_db_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT country_id FROM cities WHERE id = ?", (city_id,))
            row = cursor.fetchone()
            if row and row[0]:
                from modules.city.government_decisions import get_decision_effect
                cap_bonus = get_decision_effect(row[0], "pop_cap_bonus")
                base = int(base * (1 + cap_bonus))
        except Exception:
            pass

        return base
    except Exception:
        return BASE_POP_CAP


def is_at_population_cap(city_id: int) -> bool:
    pop = get_city_population(city_id)
    cap = get_population_capacity(city_id)
    return pop >= cap * 0.95


# ══════════════════════════════════════════
# 🚶 Intra-Country Migration
# ══════════════════════════════════════════

def tick_migration(country_id: int):
    """Move population from lowest-sat city to highest-sat city within country."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM cities WHERE country_id = ?", (country_id,))
        city_ids = [r[0] for r in cursor.fetchall()]

        if len(city_ids) < 2:
            return

        sat_map = {cid: get_city_satisfaction(cid) for cid in city_ids}
        pop_map = {cid: get_city_population(cid) for cid in city_ids}

        source = min(sat_map, key=sat_map.get)
        dest   = max(sat_map, key=sat_map.get)

        if sat_map[dest] - sat_map[source] < 15:
            return
        if sat_map[source] >= 40:
            return

        dest_cap = get_population_capacity(dest)
        if pop_map[dest] >= dest_cap * 0.95:
            return

        amount = min(MIGRATION_MAX, int(pop_map[source] * MIGRATION_RATE))
        if amount < 10:
            return

        update_city_population(source, max(100, pop_map[source] - amount))
        update_city_population(dest, min(dest_cap, pop_map[dest] + amount))

    except Exception as e:
        print(f"[migration] intra tick failed country={country_id}: {e}")


# ══════════════════════════════════════════
# 🌍 Inter-Country Migration
# ══════════════════════════════════════════

def _ensure_migration_log():
    conn = get_db_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inter_country_migration_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            from_city_id INTEGER NOT NULL,
            to_city_id   INTEGER NOT NULL,
            amount       INTEGER NOT NULL,
            migrated_at  INTEGER NOT NULL
        )
    """)
    conn.commit()


def tick_inter_country_migration():
    """
    Move population between countries when satisfaction gap is large.
    Conditions:
      - Source city sat < 30
      - Destination city sat > source + 25
      - Destination has capacity headroom
      - No migration from this source in last 7 days
    """
    try:
        _ensure_migration_log()
        conn = get_db_conn()
        cursor = conn.cursor()
        now = int(time.time())
        cooldown_cutoff = now - INTER_COUNTRY_COOLDOWN

        # Find candidate source cities (low satisfaction, not recently migrated)
        cursor.execute("""
            SELECT c.id, c.country_id, cs.score
            FROM cities c
            JOIN city_satisfaction cs ON cs.city_id = c.id
            WHERE cs.score < 30
            AND c.id NOT IN (
                SELECT from_city_id FROM inter_country_migration_log
                WHERE migrated_at > ?
            )
            ORDER BY cs.score ASC
            LIMIT 5
        """, (cooldown_cutoff,))
        sources = cursor.fetchall()

        for src_row in sources:
            src_city_id, src_country_id, src_sat = src_row[0], src_row[1], src_row[2]
            src_pop = get_city_population(src_city_id)
            if src_pop < 500:
                continue

            # Find best destination in a different country
            cursor.execute("""
                SELECT c.id, cs.score
                FROM cities c
                JOIN city_satisfaction cs ON cs.city_id = c.id
                WHERE c.country_id != ? AND cs.score > ?
                ORDER BY cs.score DESC
                LIMIT 1
            """, (src_country_id, src_sat + INTER_COUNTRY_SAT_GAP))
            dest_row = cursor.fetchone()
            if not dest_row:
                continue

            dest_city_id, dest_sat = dest_row[0], dest_row[1]
            dest_cap = get_population_capacity(dest_city_id)
            dest_pop = get_city_population(dest_city_id)

            if dest_pop >= dest_cap * 0.95:
                continue

            amount = min(INTER_COUNTRY_MIGRATION_MAX, int(src_pop * 0.01))
            if amount < 5:
                continue

            update_city_population(src_city_id, max(100, src_pop - amount))
            update_city_population(dest_city_id, min(dest_cap, dest_pop + amount))

            conn.execute("""
                INSERT INTO inter_country_migration_log (from_city_id, to_city_id, amount, migrated_at)
                VALUES (?, ?, ?, ?)
            """, (src_city_id, dest_city_id, amount, now))
            conn.commit()

    except Exception as e:
        print(f"[migration] inter-country tick failed: {e}")


# ══════════════════════════════════════════
# 💰 Population Upkeep
# ══════════════════════════════════════════

def tick_population_upkeep(city_id: int, owner_id: int):
    try:
        from database.db_queries.bank_queries import get_user_balance, deduct_user_balance
        population = get_city_population(city_id)
        upkeep = round(population * UPKEEP_PER_CAPITA, 2)
        if upkeep <= 0:
            return

        balance = get_user_balance(owner_id)
        if balance >= upkeep:
            deduct_user_balance(owner_id, upkeep)
        else:
            adjust_city_satisfaction(city_id, -5.0)
    except Exception as e:
        print(f"[upkeep] tick failed city={city_id}: {e}")


# ══════════════════════════════════════════
# 🔄 Full simulation tick
# ══════════════════════════════════════════

def run_simulation_tick():
    """Run all simulation systems for all cities/countries."""
    conn = get_db_conn()
    cursor = conn.cursor()

    # Per-city: rebellion, upkeep, population types, internal economy
    cursor.execute("""
        SELECT c.id, c.owner_id, c.country_id
        FROM cities c
    """)
    cities = cursor.fetchall()

    for row in cities:
        city_id, owner_id, country_id = row[0], row[1], row[2]

        try:
            from modules.city.rebellion_engine import tick_rebellion_stage
            tick_rebellion_stage(city_id)
        except Exception as e:
            print(f"[sim] rebellion tick failed city={city_id}: {e}")

        try:
            if owner_id:
                tick_population_upkeep(city_id, owner_id)
        except Exception as e:
            print(f"[sim] upkeep tick failed city={city_id}: {e}")

        try:
            from modules.city.population_types import recalculate_population_types
            recalculate_population_types(city_id)
        except Exception as e:
            print(f"[sim] pop_types tick failed city={city_id}: {e}")

        try:
            if owner_id and country_id:
                from modules.city.internal_economy import tick_internal_economy
                tick_internal_economy(city_id, country_id, owner_id)
        except Exception as e:
            print(f"[sim] internal_economy tick failed city={city_id}: {e}")

    # Per-country: intra migration + decision expiry
    cursor.execute("SELECT id FROM countries")
    countries = cursor.fetchall()
    for row in countries:
        try:
            tick_migration(row[0])
        except Exception as e:
            print(f"[sim] migration tick failed country={row[0]}: {e}")

        try:
            from modules.city.government_decisions import expire_old_decisions
            expire_old_decisions()
        except Exception:
            pass

    # Global: inter-country migration
    try:
        tick_inter_country_migration()
    except Exception as e:
        print(f"[sim] inter-country migration failed: {e}")
