from ..connection import get_db_conn


def create_war_balance_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # TABLE: repair_queue
    # PURPOSE: Equipment queued for repair after battle damage.
    #          The repair system checks this table periodically and
    #          restores equipment to city_equipment when ready.
    #
    # COLUMNS:
    #   id                — Internal autoincrement PK.
    #   city_id           — Which city's equipment is being repaired.
    #   equipment_type_id — Which equipment type is in the queue.
    #   quantity          — How many units are queued for repair.
    #   repair_cost       — Total currency cost to complete the repair.
    #   repair_ready_at   — Unix timestamp when repair completes.
    #   status            — 'pending' or 'done'.
    #   created_at        — When the repair was queued.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS repair_queue (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id           INTEGER NOT NULL,
        equipment_type_id INTEGER NOT NULL,
        quantity          INTEGER DEFAULT 0,
        repair_cost       REAL    DEFAULT 0,
        repair_ready_at   INTEGER NOT NULL,
        status            TEXT    DEFAULT 'pending',
        created_at        INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (city_id)           REFERENCES cities(id),
        FOREIGN KEY (equipment_type_id) REFERENCES equipment_types(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: army_fatigue
    # PURPOSE: Tracks how tired a country's army is after repeated
    #          battles. High fatigue reduces combat effectiveness.
    #          Recovers over time when the country is not fighting.
    #
    # COLUMNS:
    #   country_id     — Primary key. References countries.id.
    #   fatigue_level  — 0.0 to 1.0. Higher = weaker in battle.
    #                    Applied as a multiplier to attack/defense power.
    #   last_battle_at — Unix timestamp of the last battle. Used to
    #                    calculate natural recovery over time.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS army_fatigue (
        country_id     INTEGER PRIMARY KEY,
        fatigue_level  REAL    DEFAULT 0.0,
        last_battle_at INTEGER DEFAULT 0,
        FOREIGN KEY (country_id) REFERENCES countries(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: battle_history
    # PURPOSE: Permanent archive of completed battles for stats,
    #          leaderboards, and season rankings. Written once when
    #          a battle finishes and never modified.
    #
    # COLUMNS:
    #   id                  — Internal autoincrement PK.
    #   battle_id           — References country_battles.id.
    #   attacker_country_id — The attacker.
    #   defender_country_id — The defender.
    #   attacker_name       — Attacker's country name at battle time (snapshot).
    #   defender_name       — Defender's country name at battle time (snapshot).
    #   winner_country_id   — Who won. NULL if draw.
    #   attacker_losses_pct — Percentage of attacker's army lost (0.0–1.0).
    #   defender_losses_pct — Percentage of defender's army lost (0.0–1.0).
    #   loot                — Currency transferred to the winner.
    #   battle_type         — 'normal' or 'sudden'.
    #   duration_seconds    — How long the battle lasted.
    #   created_at          — When the battle was recorded.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battle_history (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        battle_id           INTEGER NOT NULL,
        attacker_country_id INTEGER NOT NULL,
        defender_country_id INTEGER NOT NULL,
        attacker_name       TEXT,
        defender_name       TEXT,
        winner_country_id   INTEGER,
        attacker_losses_pct REAL    DEFAULT 0,
        defender_losses_pct REAL    DEFAULT 0,
        loot                REAL    DEFAULT 0,
        battle_type         TEXT    DEFAULT 'normal',
        duration_seconds    INTEGER DEFAULT 0,
        created_at          INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (battle_id)           REFERENCES country_battles(id),
        FOREIGN KEY (attacker_country_id) REFERENCES countries(id),
        FOREIGN KEY (defender_country_id) REFERENCES countries(id)
    )
    """)

    # Safe migration: add disabled_until to city_assets if missing
    try:
        cursor.execute("ALTER TABLE city_assets ADD COLUMN disabled_until INTEGER DEFAULT 0")
    except Exception:
        pass  # column already exists

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_repair_queue_city ON repair_queue(city_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_army_fatigue ON army_fatigue(country_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_history_attacker ON battle_history(attacker_country_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_history_defender ON battle_history(defender_country_id)")

    conn.commit()
