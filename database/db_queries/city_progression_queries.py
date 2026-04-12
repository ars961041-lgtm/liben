"""
City Progression Queries — XP, Satisfaction, Population
"""
import time
from database.connection import get_db_conn

# ── XP thresholds per level (level = index+1) ──────────────────
# Level N requires XP_THRESHOLDS[N-1] total XP
XP_THRESHOLDS = [
    0,      # level 1
    100,    # level 2
    250,    # level 3
    500,    # level 4
    900,    # level 5
    1400,   # level 6
    2100,   # level 7
    3000,   # level 8
    4200,   # level 9
    5800,   # level 10
    7800,   # level 11
    10200,  # level 12
    13200,  # level 13
    16800,  # level 14
    21000,  # level 15
    26000,  # level 16
    32000,  # level 17
    39000,  # level 18
    47000,  # level 19
    56000,  # level 20
]
MAX_LEVEL = len(XP_THRESHOLDS)


def xp_to_level(xp: float) -> int:
    """Convert total XP to city level (1–20)."""
    level = 1
    for i, threshold in enumerate(XP_THRESHOLDS):
        if xp >= threshold:
            level = i + 1
        else:
            break
    return min(level, MAX_LEVEL)


def xp_for_next_level(xp: float) -> tuple:
    """Returns (current_level, xp_needed_for_next, xp_at_next_threshold)."""
    lvl = xp_to_level(xp)
    if lvl >= MAX_LEVEL:
        return lvl, 0, XP_THRESHOLDS[-1]
    next_threshold = XP_THRESHOLDS[lvl]  # index = lvl (0-based), so level N+1 threshold
    return lvl, max(0, next_threshold - xp), next_threshold


# ══════════════════════════════════════════
# XP
# ══════════════════════════════════════════

def get_city_xp(city_id: int) -> dict:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT xp, level FROM city_xp WHERE city_id = ?", (city_id,))
    row = cursor.fetchone()
    if row:
        return {"xp": row[0], "level": row[1]}
    return {"xp": 0.0, "level": 1}


def add_city_xp(city_id: int, amount: float) -> dict:
    """Add XP to a city, update level if threshold crossed. Returns new state."""
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())

    cursor.execute("""
        INSERT INTO city_xp (city_id, xp, level, updated_at)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(city_id) DO UPDATE SET
            xp = xp + ?,
            updated_at = ?
    """, (city_id, amount, now, amount, now))

    cursor.execute("SELECT xp FROM city_xp WHERE city_id = ?", (city_id,))
    row = cursor.fetchone()
    new_xp = row[0] if row else amount
    new_level = xp_to_level(new_xp)

    cursor.execute("""
        UPDATE city_xp SET level = ? WHERE city_id = ?
    """, (new_level, city_id))
    conn.commit()

    return {"xp": new_xp, "level": new_level}


# ══════════════════════════════════════════
# Satisfaction
# ══════════════════════════════════════════

def get_city_satisfaction(city_id: int) -> float:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT score FROM city_satisfaction WHERE city_id = ?", (city_id,))
    row = cursor.fetchone()
    return float(row[0]) if row else 50.0


def set_city_satisfaction(city_id: int, score: float):
    score = max(0.0, min(100.0, score))
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        INSERT INTO city_satisfaction (city_id, score, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(city_id) DO UPDATE SET score = ?, updated_at = ?
    """, (city_id, score, now, score, now))
    conn.commit()


def adjust_city_satisfaction(city_id: int, delta: float):
    """Add/subtract from satisfaction, clamped to 0–100."""
    current = get_city_satisfaction(city_id)
    set_city_satisfaction(city_id, current + delta)


# ══════════════════════════════════════════
# Population
# ══════════════════════════════════════════

def get_city_population(city_id: int) -> int:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT population FROM cities WHERE id = ?", (city_id,))
    row = cursor.fetchone()
    return int(row[0]) if row else 1000


def update_city_population(city_id: int, new_population: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE cities SET population = ? WHERE id = ?",
                   (max(100, new_population), city_id))
    conn.commit()
