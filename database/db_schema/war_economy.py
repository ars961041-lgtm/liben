from ..connection import get_db_conn


def create_war_economy_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # TABLE: injured_troops
    # PURPOSE: Troops that survived a battle but are wounded and
    #          need time to heal before they can fight again.
    #          The heal system checks this table and restores troops
    #          to city_troops when heal_time is reached.
    #
    # COLUMNS:
    #   id            — Internal autoincrement PK.
    #   city_id       — Which city these troops belong to.
    #   troop_type_id — Which troop type is injured.
    #   quantity      — How many units are injured.
    #   heal_time     — Unix timestamp when they finish healing.
    #   created_at    — When the injury was recorded.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS injured_troops (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id       INTEGER NOT NULL,
        troop_type_id INTEGER NOT NULL,
        quantity      INTEGER DEFAULT 0,
        heal_time     INTEGER NOT NULL,
        created_at    INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (city_id)       REFERENCES cities(id),
        FOREIGN KEY (troop_type_id) REFERENCES troop_types(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: damaged_equipment
    # PURPOSE: Equipment damaged in battle that needs repair before
    #          it can be used again. Separate from repair_queue —
    #          this records the damage event; repair_queue tracks
    #          the active repair job.
    #
    # COLUMNS:
    #   id                — Internal autoincrement PK.
    #   city_id           — Which city this equipment belongs to.
    #   equipment_type_id — Which equipment type is damaged.
    #   quantity          — How many units are damaged.
    #   repair_cost       — Total currency cost to repair.
    #   repair_time       — Unix timestamp when repair finishes.
    #   created_at        — When the damage was recorded.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS damaged_equipment (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id           INTEGER NOT NULL,
        equipment_type_id INTEGER NOT NULL,
        quantity          INTEGER DEFAULT 0,
        repair_cost       REAL    DEFAULT 0,
        repair_time       INTEGER NOT NULL,
        created_at        INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (city_id)           REFERENCES cities(id),
        FOREIGN KEY (equipment_type_id) REFERENCES equipment_types(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: country_recovery
    # PURPOSE: A country in recovery cannot be attacked. Applied
    #          automatically after losing a battle to give the
    #          defeated player time to rebuild.
    #
    # COLUMNS:
    #   country_id     — Primary key. References countries.id.
    #   recovery_until — Unix timestamp until which the country is protected.
    #   reason         — Why recovery was applied (e.g. 'battle', 'admin').
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS country_recovery (
        country_id     INTEGER PRIMARY KEY,
        recovery_until INTEGER NOT NULL,
        reason         TEXT    DEFAULT 'battle',
        FOREIGN KEY (country_id) REFERENCES countries(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: war_costs_log
    # PURPOSE: Immutable audit log of every currency deduction
    #          related to war actions (attack launch, card use,
    #          support send, etc.). Used for financial history
    #          and debugging economy issues.
    #
    # COLUMNS:
    #   id         — Internal autoincrement PK.
    #   user_id    — Who was charged.
    #   battle_id  — Related battle. NULL for non-battle costs.
    #   action     — What was paid for (e.g. 'attack', 'card', 'support').
    #   amount     — Amount deducted (positive = cost to the user).
    #   created_at — When the charge occurred.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS war_costs_log (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        battle_id  INTEGER,
        action     TEXT    NOT NULL,
        amount     REAL    NOT NULL,
        created_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (user_id)   REFERENCES users(user_id),
        FOREIGN KEY (battle_id) REFERENCES country_battles(id)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_injured_city ON injured_troops(city_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_damaged_city ON damaged_equipment(city_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recovery_country ON country_recovery(country_id)")

    conn.commit()
