from database.connection import get_db_conn


# ══════════════════════════════════════════
# 📦 جلب الأصول
# ══════════════════════════════════════════

def get_all_assets():
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, s.name AS sector_name, s.emoji AS sector_emoji
        FROM assets a
        JOIN asset_sectors s ON a.sector_id = s.id
        ORDER BY a.sector_id, a.base_price
    """)
    return [dict(r) for r in cursor.fetchall()]


def get_assets_by_sector(sector_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM assets WHERE sector_id=? ORDER BY base_price", (sector_id,))
    return [dict(r) for r in cursor.fetchall()]


def get_asset_by_name(name: str):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM assets WHERE name=? OR name_ar=?", (name, name))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_asset_by_id(asset_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM assets WHERE id=?", (asset_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_all_sectors():
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM asset_sectors ORDER BY id")
    return [dict(r) for r in cursor.fetchall()]



# ══════════════════════════════════════════
# 🏙️ مشتريات المدينة
# ══════════════════════════════════════════

def get_city_assets(city_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ca.id, ca.city_id, ca.asset_id, ca.level, ca.quantity,
               a.name, a.name_ar, a.emoji, a.base_price, a.base_value,
               a.cost_scale, a.maintenance, a.income, a.max_level,
               a.stat_economy, a.stat_health, a.stat_education,
               a.stat_military, a.stat_infrastructure,
               a.pop_effect, a.eco_effect, a.prot_effect
        FROM city_assets ca
        JOIN assets a ON ca.asset_id = a.id
        WHERE ca.city_id = ?
        ORDER BY a.sector_id, a.name, ca.level
    """, (city_id,))
    return [dict(r) for r in cursor.fetchall()]


def get_city_asset(city_id: int, asset_id: int, level: int = 1):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ca.id, ca.city_id, ca.asset_id, ca.level, ca.quantity,
               a.name, a.name_ar, a.emoji, a.base_price, a.base_value,
               a.cost_scale, a.maintenance, a.income, a.max_level,
               a.stat_economy, a.stat_health, a.stat_education,
               a.stat_military, a.stat_infrastructure,
               a.pop_effect, a.eco_effect, a.prot_effect
        FROM city_assets ca
        JOIN assets a ON ca.asset_id = a.id
        WHERE ca.city_id=? AND ca.asset_id=? AND ca.level=?
    """, (city_id, asset_id, level))
    row = cursor.fetchone()
    return dict(row) if row else None


def upsert_city_asset(city_id: int, asset_id: int,
                       level: int, quantity_delta: int):
    """Add quantity to existing row or insert new one."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO city_assets (city_id, asset_id, level, quantity)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(city_id, asset_id, level)
        DO UPDATE SET quantity = quantity + ?
    """, (city_id, asset_id, level, quantity_delta, quantity_delta))
    conn.commit()


def upgrade_city_asset(city_id: int, asset_id: int, from_level: int, quantity: int):
    """Move `quantity` units from from_level to from_level+1."""
    conn = get_db_conn()
    cursor = conn.cursor()
    to_level = from_level + 1

    cursor.execute("""
        UPDATE city_assets SET quantity = quantity - ?
        WHERE city_id=? AND asset_id=? AND level=?
    """, (quantity, city_id, asset_id, from_level))

    cursor.execute("""
        DELETE FROM city_assets
        WHERE city_id=? AND asset_id=? AND level=? AND quantity <= 0
    """, (city_id, asset_id, from_level))

    cursor.execute("""
        INSERT INTO city_assets (city_id, asset_id, level, quantity)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(city_id, asset_id, level)
        DO UPDATE SET quantity = quantity + ?
    """, (city_id, asset_id, to_level, quantity, quantity))

    conn.commit()


# ══════════════════════════════════════════
# 📊 حساب تأثيرات المدينة
# ══════════════════════════════════════════

def calculate_asset_income(base_income: float, bonus_pct: float = 0.0,
                            level: int = 1, quantity: int = 1) -> float:
    bonus_pct = bonus_pct or 0.0
    return base_income * (1 + bonus_pct) * level * quantity


def calculate_city_effects(city_id: int) -> dict:
    """
    Returns aggregated stats for a city based on all city_assets.

    Direct stats (raw sums):
      economy, health, education, infrastructure, income, maintenance

    Derived bonuses (0.0–1.0 multipliers, capped):
      health_bonus       — reduces army maintenance cost (up to 25%)
      education_bonus    — boosts economy income (up to 20%) + population growth
      infra_bonus        — boosts overall economy efficiency (up to 20%)
                           and reduces war logistics cost (up to 15%)
      population_bonus   — population growth rate bonus
      eco_bonus          — direct economy stat bonus

    Cross-sector synergy:
      A city with all four sectors developed gets a 10% synergy bonus
      applied to income (encourages diversified investment).
    """
    empty = {
        "economy": 0.0, "health": 0.0, "education": 0.0,
        "infrastructure": 0.0,
        "population_bonus": 0.0, "eco_bonus": 0.0,
        "income": 0.0, "maintenance": 0.0,
        # derived bonuses
        "health_bonus": 0.0,
        "education_bonus": 0.0,
        "infra_bonus": 0.0,
    }
    try:
        rows = get_city_assets(city_id)
    except Exception:
        return empty

    stats = dict(empty)
    sectors_present = set()

    for r in rows:
        qty = r["quantity"]
        lvl = r["level"]
        multiplier = qty * (1 + lvl * 0.2)

        stats["economy"]          += r["stat_economy"]        * multiplier
        stats["health"]           += r["stat_health"]         * multiplier
        stats["education"]        += r["stat_education"]      * multiplier
        stats["infrastructure"]   += r["stat_infrastructure"] * multiplier
        stats["population_bonus"] += r["pop_effect"]          * multiplier
        stats["eco_bonus"]        += r["eco_effect"]          * multiplier
        stats["income"]           += calculate_asset_income(r["income"], 0.0, lvl, qty)
        stats["maintenance"]      += r["maintenance"]         * qty * lvl

        # track which sectors are invested in
        if r["stat_health"] > 0 or r.get("name", "").startswith(("hospital", "clinic", "pharmacy", "medical", "ambulance", "health", "research_medical")):
            sectors_present.add("health")
        if r["stat_education"] > 0:
            sectors_present.add("education")
        if r["stat_economy"] > 0 or r["eco_effect"] > 0:
            sectors_present.add("economy")
        if r["stat_infrastructure"] > 0:
            sectors_present.add("infrastructure")

    stats["economy"] += stats["eco_bonus"]
    stats["health"]  += stats["population_bonus"] * 10

    # ── Derived bonuses (capped multipliers) ──────────────────────────────
    # Health → reduces army maintenance (hospitals, clinics, etc.)
    # Formula: each 10 health points = 1% reduction, cap 25%
    stats["health_bonus"]    = min(0.25, stats["health"] * 0.001)

    # Education → boosts income efficiency + population growth
    # Formula: each 10 education points = 1% income boost, cap 20%
    stats["education_bonus"] = min(0.20, stats["education"] * 0.001)

    # Infrastructure → boosts economy efficiency + reduces war logistics cost
    # Formula: each 10 infra points = 1% boost, cap 20%
    stats["infra_bonus"]     = min(0.20, stats["infrastructure"] * 0.001)

    # Apply education + infra bonuses to income
    income_multiplier = 1.0 + stats["education_bonus"] + stats["infra_bonus"]

    # Cross-sector synergy: all 4 sectors → +10% income
    if len(sectors_present) >= 4:
        income_multiplier += 0.10

    stats["income"] = round(stats["income"] * income_multiplier, 2)

    # ── Population income bonus (applied after base multipliers) ──
    try:
        from modules.city.city_stats import get_population_income_bonus, get_satisfaction_income_modifier, get_level_bonuses
        pop_bonus  = get_population_income_bonus(city_id)
        sat_mod    = get_satisfaction_income_modifier(city_id)
        lvl_data   = get_level_bonuses(city_id)
        lvl_prod   = lvl_data["production_bonus"]
        stats["income"] = round(stats["income"] * (1.0 + pop_bonus) * (1.0 + lvl_prod) * sat_mod, 2)
        stats["level_production_bonus"] = lvl_prod
        stats["level_military_bonus"]   = lvl_data["military_bonus"]
        stats["population_income_bonus"] = pop_bonus
        stats["satisfaction_modifier"]   = sat_mod
    except Exception:
        stats["level_production_bonus"] = 0.0
        stats["level_military_bonus"]   = 0.0
        stats["population_income_bonus"] = 0.0
        stats["satisfaction_modifier"]   = 1.0

    return {k: round(v, 4) if isinstance(v, float) else v for k, v in stats.items()}


# ══════════════════════════════════════════
# 🪖 القوة العسكرية — محسوبة من نظام الحرب فقط
# ══════════════════════════════════════════

def get_city_military_power(city_id: int) -> float:
    conn = get_db_conn()
    cursor = conn.cursor()

    # الجنود
    cursor.execute("""
        SELECT ct.quantity, tt.attack, tt.defense, tt.hp
        FROM city_troops ct
        JOIN troop_types tt ON ct.troop_type_id = tt.id
        WHERE ct.city_id = ?
    """, (city_id,))
    troops = cursor.fetchall()

    troop_power = sum(
        r["quantity"] * ((r["attack"] * 1.2 + r["defense"]) * (r["hp"] / 100))
        for r in troops
    )

    # المعدات
    cursor.execute("""
        SELECT ce.quantity, et.attack_bonus, et.defense_bonus
        FROM city_equipment ce
        JOIN equipment_types et ON ce.equipment_type_id = et.id
        WHERE ce.city_id = ?
    """, (city_id,))
    equipment = cursor.fetchall()

    equip_bonus = sum(
        r["quantity"] * (r["attack_bonus"] + r["defense_bonus"])
        for r in equipment
    )

    return troop_power + equip_bonus

def get_country_military_power(country_id: int) -> float:
    """
    Country military power = sum of all its cities' military power.
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM cities WHERE country_id = ?", (country_id,))
    cities = cursor.fetchall()
    return round(sum(get_city_military_power(c["id"]) for c in cities), 2)


# ══════════════════════════════════════════
# 📝 سجل العمليات
# ══════════════════════════════════════════

def log_asset_action(city_id, user_id, asset_id, action, quantity=0,
                     from_level=1, to_level=1, cost=0):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO asset_log (city_id, user_id, asset_id, action, quantity, from_level, to_level, cost)
        VALUES (?,?,?,?,?,?,?,?)
    """, (city_id, user_id, asset_id, action, quantity, from_level, to_level, cost))
    conn.commit()
