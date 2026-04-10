from ..connection import get_db_conn


def create_live_battle_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # TABLE: battle_state
    # PURPOSE: Real-time power snapshot for an ongoing battle.
    #          Updated on every tick by the live battle engine.
    #          One row per active battle — deleted or archived when done.
    #
    # COLUMNS:
    #   battle_id   — Primary key. References country_battles.id.
    #   atk_power   — Attacker's current remaining power (decreases each tick).
    #   def_power   — Defender's current remaining power (decreases each tick).
    #   atk_initial — Attacker's power at battle start. Used for loss % calculation.
    #   def_initial — Defender's power at battle start.
    #   last_tick   — Unix timestamp of the last tick processed.
    #   tick_count  — How many ticks have elapsed in this battle.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battle_state (
        battle_id   INTEGER PRIMARY KEY,
        atk_power   REAL    DEFAULT 0,
        def_power   REAL    DEFAULT 0,
        atk_initial REAL    DEFAULT 0,
        def_initial REAL    DEFAULT 0,
        last_tick   INTEGER DEFAULT 0,
        tick_count  INTEGER DEFAULT 0,
        FOREIGN KEY (battle_id) REFERENCES country_battles(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: battle_effects
    # PURPOSE: Temporary effects active during a battle, applied by
    #          cards or alliance upgrades. Expire at a set timestamp.
    #          The battle engine reads these each tick to modify power.
    #
    # COLUMNS:
    #   id          — Internal autoincrement PK.
    #   battle_id   — Which battle this effect is active in.
    #   country_id  — Which country the effect applies to.
    #   user_id     — Who activated the effect.
    #   effect_type — What the effect does (e.g. 'attack_boost', 'defense_boost').
    #   value       — Magnitude of the effect (e.g. 0.25 = 25%).
    #   expires_at  — Unix timestamp when the effect wears off.
    #   source      — Where the effect came from: 'card' or 'upgrade'.
    #   created_at  — When the effect was applied.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battle_effects (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        battle_id   INTEGER NOT NULL,
        country_id  INTEGER NOT NULL,
        user_id     INTEGER NOT NULL,
        effect_type TEXT    NOT NULL,
        value       REAL    DEFAULT 0,
        expires_at  INTEGER NOT NULL,
        source      TEXT    DEFAULT 'card',
        created_at  INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (battle_id)  REFERENCES country_battles(id),
        FOREIGN KEY (country_id) REFERENCES countries(id),
        FOREIGN KEY (user_id)    REFERENCES users(user_id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: battle_action_cooldowns
    # PURPOSE: Prevents players from spamming card or action use
    #          during a live battle. One row per (battle, user, action).
    #
    # COLUMNS:
    #   battle_id — Which battle.
    #   user_id   — Which player.
    #   action    — Which action (e.g. 'use_card', 'send_support').
    #   last_used — Unix timestamp of the last use. Compared against cooldown.
    #
    # PRIMARY KEY: (battle_id, user_id, action)
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battle_action_cooldowns (
        battle_id INTEGER NOT NULL,
        user_id   INTEGER NOT NULL,
        action    TEXT    NOT NULL,
        last_used INTEGER NOT NULL,
        PRIMARY KEY (battle_id, user_id, action),
        FOREIGN KEY (battle_id) REFERENCES country_battles(id),
        FOREIGN KEY (user_id)   REFERENCES users(user_id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: battle_events
    # PURPOSE: Chronological log of notable events during a battle.
    #          Used to generate the post-battle report shown to players.
    #          Includes power snapshots so the report shows how the
    #          battle evolved over time.
    #
    # COLUMNS:
    #   id                 — Internal autoincrement PK.
    #   battle_id          — Which battle.
    #   event_type         — Type of event (e.g. 'card_used', 'support_joined', 'tick').
    #   description        — Human-readable description of what happened.
    #   atk_power_snapshot — Attacker power at the moment of this event.
    #   def_power_snapshot — Defender power at the moment of this event.
    #   created_at         — When the event occurred.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battle_events (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        battle_id          INTEGER NOT NULL,
        event_type         TEXT    NOT NULL,
        description        TEXT,
        atk_power_snapshot REAL    DEFAULT 0,
        def_power_snapshot REAL    DEFAULT 0,
        created_at         INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (battle_id) REFERENCES country_battles(id)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_state ON battle_state(battle_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_effects_battle ON battle_effects(battle_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_events_battle ON battle_events(battle_id)")

    conn.commit()
