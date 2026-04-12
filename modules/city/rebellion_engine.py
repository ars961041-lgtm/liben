"""
Advanced Rebellion Engine — Progressive State System

Rebellion evolves through 3 stages based on how long satisfaction stays low.
Each stage has escalating effects and requires gradual recovery.

═══════════════════════════════════════════════════════════
STAGES:
  Stage 0 — Calm (no rebellion)
  Stage 1 — Unrest (sat < 30 for 1+ days)
    Effects: income ×0.70, XP gain -20%
  Stage 2 — Riots (sat < 20 for 3+ days)
    Effects: income ×0.40, random building damage (1 unit/day),
             economic slowdown (maintenance +30%)
  Stage 3 — Full Rebellion (sat < 10 for 5+ days)
    Effects: income ×0.0 (blocked), construction blocked,
             army -40%, population loss 1%/day

RECOVERY:
  Stage 3 → 2: satisfaction ≥ 20 for 2 consecutive days
  Stage 2 → 1: satisfaction ≥ 30 for 2 consecutive days
  Stage 1 → 0: satisfaction ≥ 40 for 1 day
  Each recovery step gives +5 satisfaction bonus

TABLE: city_rebellion_state
  city_id, stage (0-3), days_at_stage, last_updated
═══════════════════════════════════════════════════════════
"""
import random
import time
from database.connection import get_db_conn
from database.db_queries.city_progression_queries import (
    get_city_satisfaction, adjust_city_satisfaction, get_city_population, update_city_population
)

# Stage thresholds
STAGE_THRESHOLDS = {
    1: (30, 1),   # sat < 30 for 1+ days → stage 1
    2: (20, 3),   # sat < 20 for 3+ days → stage 2
    3: (10, 5),   # sat < 10 for 5+ days → stage 3
}
RECOVERY_THRESHOLDS = {
    3: (20, 2),   # sat ≥ 20 for 2 days → drop to stage 2
    2: (30, 2),   # sat ≥ 30 for 2 days → drop to stage 1
    1: (40, 1),   # sat ≥ 40 for 1 day  → drop to stage 0
}


def _ensure_table():
    conn = get_db_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS city_rebellion_state (
            city_id        INTEGER PRIMARY KEY,
            stage          INTEGER NOT NULL DEFAULT 0,
            days_at_stage  INTEGER NOT NULL DEFAULT 0,
            recovery_days  INTEGER NOT NULL DEFAULT 0,
            last_updated   INTEGER DEFAULT (strftime('%s','now')),
            FOREIGN KEY (city_id) REFERENCES cities(id)
        )
    """)
    conn.commit()


def get_rebellion_stage(city_id: int) -> int:
    """Returns current rebellion stage (0–3)."""
    try:
        _ensure_table()
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT stage FROM city_rebellion_state WHERE city_id = ?", (city_id,))
        row = cursor.fetchone()
        return int(row[0]) if row else 0
    except Exception:
        return 0


def _upsert_state(city_id: int, stage: int, days_at_stage: int, recovery_days: int):
    conn = get_db_conn()
    now = int(time.time())
    conn.execute("""
        INSERT INTO city_rebellion_state (city_id, stage, days_at_stage, recovery_days, last_updated)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(city_id) DO UPDATE SET
            stage = ?, days_at_stage = ?, recovery_days = ?, last_updated = ?
    """, (city_id, stage, days_at_stage, recovery_days, now,
          stage, days_at_stage, recovery_days, now))
    conn.commit()


def tick_rebellion_stage(city_id: int) -> int:
    """
    Daily tick: advance or recover rebellion stage.
    Returns new stage.
    """
    _ensure_table()
    sat = get_city_satisfaction(city_id)

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT stage, days_at_stage, recovery_days FROM city_rebellion_state WHERE city_id = ?",
        (city_id,)
    )
    row = cursor.fetchone()
    stage         = int(row[0]) if row else 0
    days_at_stage = int(row[1]) if row else 0
    recovery_days = int(row[2]) if row else 0

    # ── Recovery check ──────────────────────────────────────────
    if stage > 0:
        rec_sat, rec_days_needed = RECOVERY_THRESHOLDS[stage]
        if sat >= rec_sat:
            recovery_days += 1
            if recovery_days >= rec_days_needed:
                new_stage = stage - 1
                _upsert_state(city_id, new_stage, 0, 0)
                adjust_city_satisfaction(city_id, +5.0)
                _apply_stage_effects(city_id, new_stage)
                return new_stage
            else:
                _upsert_state(city_id, stage, days_at_stage, recovery_days)
                return stage
        else:
            recovery_days = 0  # reset recovery counter if sat drops again

    # ── Escalation check ────────────────────────────────────────
    new_stage = stage
    for s in [3, 2, 1]:
        threshold_sat, threshold_days = STAGE_THRESHOLDS[s]
        if sat < threshold_sat:
            if stage < s:
                days_at_stage += 1
                if days_at_stage >= threshold_days:
                    new_stage = s
                    days_at_stage = 0
                    recovery_days = 0
            break
    else:
        # sat is fine — no escalation
        if stage == 0:
            _upsert_state(city_id, 0, 0, 0)
            return 0

    _upsert_state(city_id, new_stage, days_at_stage, recovery_days)
    _apply_stage_effects(city_id, new_stage)
    return new_stage


def _apply_stage_effects(city_id: int, stage: int):
    """Apply one-time daily effects for the current stage."""
    if stage == 0:
        return

    if stage >= 2:
        # Random building damage: remove 1 unit from a random asset
        try:
            conn = get_db_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, asset_id, level, quantity FROM city_assets
                WHERE city_id = ? AND quantity > 0
                ORDER BY RANDOM() LIMIT 1
            """, (city_id,))
            row = cursor.fetchone()
            if row:
                new_qty = max(0, row[3] - 1)
                cursor.execute(
                    "UPDATE city_assets SET quantity = ? WHERE id = ?",
                    (new_qty, row[0])
                )
                conn.commit()
        except Exception:
            pass

    if stage >= 3:
        # Population loss 1%/day
        pop = get_city_population(city_id)
        loss = max(1, int(pop * 0.01))
        update_city_population(city_id, max(100, pop - loss))


def get_rebellion_income_modifier(city_id: int) -> float:
    """Returns income multiplier based on rebellion stage."""
    stage = get_rebellion_stage(city_id)
    modifiers = {0: 1.0, 1: 0.70, 2: 0.40, 3: 0.0}
    return modifiers.get(stage, 1.0)


def get_rebellion_army_penalty(city_id: int) -> float:
    """Returns army power reduction (0.0–0.40) based on stage."""
    stage = get_rebellion_stage(city_id)
    return 0.40 if stage >= 3 else (0.20 if stage >= 2 else 0.0)


def is_construction_blocked(city_id: int) -> bool:
    return get_rebellion_stage(city_id) >= 3


def get_rebellion_status(city_id: int) -> dict:
    stage = get_rebellion_stage(city_id)
    labels = {
        0: ("مستقرة", []),
        1: ("اضطرابات", ["دخل -30%", "XP -20%"]),
        2: ("أعمال شغب", ["دخل -60%", "أضرار عشوائية", "صيانة +30%"]),
        3: ("تمرد كامل", ["دخل محجوب", "بناء محجوب", "جيش -40%", "هجرة سكانية"]),
    }
    label, effects = labels.get(stage, ("مستقرة", []))
    return {"stage": stage, "label": label, "effects": effects}


# backward compat — used by city_stats.py
def is_city_in_rebellion(city_id: int) -> bool:
    return get_rebellion_stage(city_id) >= 3
