"""
City Progression Schema
Tables: city_xp, city_satisfaction
These are separate from city_aspects (which stores raw stat scores).
"""
from ..connection import get_db_conn


def create_city_progression_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # TABLE: city_xp
    # PURPOSE: Tracks XP and level for each city.
    #   XP is gained from: battles won, asset upgrades, daily tasks.
    #   Level unlocks higher-tier assets and army capacity.
    #
    # COLUMNS:
    #   city_id    — FK → cities.id (UNIQUE — one row per city)
    #   xp         — Total accumulated XP
    #   level      — Derived level (1–20), computed from XP thresholds
    #   updated_at — Last update timestamp
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS city_xp (
        city_id    INTEGER PRIMARY KEY,
        xp         REAL    NOT NULL DEFAULT 0,
        level      INTEGER NOT NULL DEFAULT 1,
        updated_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (city_id) REFERENCES cities(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: city_satisfaction
    # PURPOSE: Tracks population satisfaction (0–100) per city.
    #   Affected by: health stats, income vs maintenance ratio,
    #   war casualties, and global events.
    #   High satisfaction → income bonus + loyalty.
    #   Low satisfaction → income penalty + instability risk.
    #
    # COLUMNS:
    #   city_id    — FK → cities.id (UNIQUE)
    #   score      — Satisfaction score 0–100 (default 50)
    #   updated_at — Last update timestamp
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS city_satisfaction (
        city_id    INTEGER PRIMARY KEY,
        score      REAL    NOT NULL DEFAULT 50.0,
        updated_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (city_id) REFERENCES cities(id)
    )
    """)

    conn.commit()
