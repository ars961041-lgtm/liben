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


def get_asset_branches(asset_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM asset_branches WHERE asset_id=?", (asset_id,))
    return [dict(r) for r in cursor.fetchall()]


def get_asset_branch(branch_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM asset_branches WHERE id=?", (branch_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


# ══════════════════════════════════════════
# 🏙️ مشتريات المدينة
# ══════════════════════════════════════════

def get_city_assets(city_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ca.id, ca.city_id, ca.asset_id, ca.branch_id, ca.level, ca.quantity,
               a.name, a.name_ar, a.emoji, a.base_price, a.base_value,
               a.cost_scale, a.maintenance, a.income, a.max_level,
               a.stat_economy, a.stat_health, a.stat_education,
               a.stat_military, a.stat_infrastructure,
               a.pop_effect, a.eco_effect, a.prot_effect,
               b.name AS branch_name, b.name_ar AS branch_name_ar,
               b.emoji AS branch_emoji, b.bonus_pct
        FROM city_assets ca
        JOIN assets a ON ca.asset_id = a.id
        LEFT JOIN asset_branches b ON ca.branch_id = b.id
        WHERE ca.city_id = ?
        ORDER BY a.sector_id, a.name, ca.branch_id, ca.level
    """, (city_id,))
    return [dict(r) for r in cursor.fetchall()]


def get_city_asset(city_id: int, asset_id: int, level: int = 1, branch_id: int = None):
    conn = get_db_conn()
    cursor = conn.cursor()
    if branch_id is None:
        cursor.execute("""
            SELECT ca.id, ca.city_id, ca.asset_id, ca.branch_id, ca.level, ca.quantity,
                   a.name, a.name_ar, a.emoji, a.base_price, a.base_value,
                   a.cost_scale, a.maintenance, a.income, a.max_level,
                   a.stat_economy, a.stat_health, a.stat_education,
                   a.stat_military, a.stat_infrastructure,
                   a.pop_effect, a.eco_effect, a.prot_effect,
                   b.name AS branch_name, b.name_ar AS branch_name_ar,
                   b.emoji AS branch_emoji, b.bonus_pct
            FROM city_assets ca
            JOIN assets a ON ca.asset_id = a.id
            LEFT JOIN asset_branches b ON ca.branch_id = b.id
            WHERE ca.city_id=? AND ca.asset_id=? AND ca.level=? AND ca.branch_id IS NULL
        """, (city_id, asset_id, level))
    else:
        cursor.execute("""
            SELECT ca.id, ca.city_id, ca.asset_id, ca.branch_id, ca.level, ca.quantity,
                   a.name, a.name_ar, a.emoji, a.base_price, a.base_value,
                   a.cost_scale, a.maintenance, a.income, a.max_level,
                   a.stat_economy, a.stat_health, a.stat_education,
                   a.stat_military, a.stat_infrastructure,
                   a.pop_effect, a.eco_effect, a.prot_effect,
                   b.name AS branch_name, b.name_ar AS branch_name_ar,
                   b.emoji AS branch_emoji, b.bonus_pct
            FROM city_assets ca
            JOIN assets a ON ca.asset_id = a.id
            LEFT JOIN asset_branches b ON ca.branch_id = b.id
            WHERE ca.city_id=? AND ca.asset_id=? AND ca.level=? AND ca.branch_id=?
        """, (city_id, asset_id, level, branch_id))
    row = cursor.fetchone()
    return dict(row) if row else None


def upsert_city_asset(city_id: int, asset_id: int,
                       level: int, quantity_delta: int,
                       branch_id: int = None):
    """Add quantity to existing row or insert new one."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO city_assets (city_id, asset_id, branch_id, level, quantity)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(city_id, asset_id, branch_id, level)
        DO UPDATE SET quantity = quantity + ?
    """, (city_id, asset_id, branch_id, level, quantity_delta, quantity_delta))
    conn.commit()


def upgrade_city_asset(city_id: int, asset_id: int, from_level: int,
                       quantity: int, branch_id: int = None):
    """Move `quantity` units from from_level to from_level+1."""
    conn = get_db_conn()
    cursor = conn.cursor()
    to_level = from_level + 1

    if branch_id is None:
        branch_filter = "AND branch_id IS NULL"
        branch_values = ()
    else:
        branch_filter = "AND branch_id = ?"
        branch_values = (branch_id,)

    # reduce from current level
    cursor.execute(f"""
        UPDATE city_assets SET quantity = quantity - ?
        WHERE city_id=? AND asset_id=? AND level=? {branch_filter}
    """, (quantity, city_id, asset_id, from_level, *branch_values))

    # remove row if empty
    cursor.execute(f"""
        DELETE FROM city_assets
        WHERE city_id=? AND asset_id=? AND level=? AND quantity <= 0 {branch_filter}
    """, (city_id, asset_id, from_level, *branch_values))

    # add to next level
    cursor.execute("""
        INSERT INTO city_assets (city_id, asset_id, branch_id, level, quantity)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(city_id, asset_id, branch_id, level)
        DO UPDATE SET quantity = quantity + ?
    """, (city_id, asset_id, branch_id, to_level, quantity, quantity))

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
    Military power is NOT included here — use get_city_military_power() instead.
    value = base_value * quantity * (1 + level * 0.2)
    """
    empty = {
        "economy": 0.0, "health": 0.0, "education": 0.0,
        "infrastructure": 0.0,
        "population_bonus": 0.0, "eco_bonus": 0.0,
        "income": 0.0, "maintenance": 0.0,
    }
    try:
        rows = get_city_assets(city_id)
    except Exception:
        return empty

    stats = dict(empty)
    for r in rows:
        qty = r["quantity"]
        lvl = r["level"]
        multiplier = qty * (1 + lvl * 0.2)
        bonus_pct = r.get("bonus_pct") or 0.0

        stats["economy"]          += r["stat_economy"]        * multiplier
        stats["health"]           += r["stat_health"]         * multiplier
        stats["education"]        += r["stat_education"]      * multiplier
        stats["infrastructure"]   += r["stat_infrastructure"] * multiplier
        stats["population_bonus"] += r["pop_effect"]          * multiplier
        stats["eco_bonus"]        += r["eco_effect"]          * multiplier
        stats["income"]           += calculate_asset_income(r["income"], bonus_pct, lvl, qty)
        stats["maintenance"]      += r["maintenance"]         * qty * lvl

    stats["economy"] += stats["eco_bonus"]
    stats["health"]  += stats["population_bonus"] * 10

    return {k: round(v, 2) for k, v in stats.items()}


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
