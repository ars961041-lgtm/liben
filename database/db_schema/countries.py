from ..connection import get_db_conn


def create_countries_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # TABLE: countries
    # PURPOSE: Each player-owned country. Stats (economy, military,
    #          etc.) are NOT stored here — they are always computed
    #          live by aggregating city_assets via calculate_city_effects().
    #
    # COLUMNS:
    #   id         — Internal autoincrement PK.
    #   name       — Unique country name chosen by the player.
    #   owner_id   — References users.user_id. The player who owns it.
    #   created_at — Unix timestamp when the country was created.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS countries (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        name       TEXT    UNIQUE NOT NULL,
        owner_id   INTEGER NOT NULL,
        created_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (owner_id) REFERENCES users(user_id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: cities
    # PURPOSE: Each city belonging to a country. Stats are computed
    #          live from city_assets via calculate_city_effects().
    #          A city is created automatically when a country is
    #          founded, and can be added via country invites.
    #
    # COLUMNS:
    #   id                — Internal autoincrement PK.
    #   country_id        — References countries.id. Which country owns this city.
    #   owner_id          — References users.user_id. The player who owns this city.
    #   name              — City name.
    #   level             — City level. Affects what assets can be built. Default 1.
    #   population        — City population. Affects some calculations. Default 1000.
    #   area              — City area. Currently informational.
    #   created_at        — When the city was created.
    #   last_collect_time — Last time resources were collected from this city.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cities (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id        INTEGER,
        owner_id          INTEGER,
        name              TEXT    NOT NULL,
        level             INTEGER DEFAULT 1,
        population        INTEGER DEFAULT 1000,
        area              REAL    DEFAULT 0,
        created_at        INTEGER DEFAULT (strftime('%s','now')),
        last_collect_time INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (country_id) REFERENCES countries(id),
        FOREIGN KEY (owner_id)   REFERENCES users(user_id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: city_budget
    # PURPOSE: Tracks the financial state of a city over time.
    #          One row per city, created automatically when the city
    #          is created. Updated by the economy background task.
    #
    # COLUMNS:
    #   id               — Internal autoincrement PK.
    #   city_id          — References cities.id. UNIQUE — one budget per city.
    #   current_budget   — Current accumulated balance for this city.
    #   income_per_hour  — Hourly income calculated from owned assets.
    #   expense_per_hour — Hourly maintenance cost from owned assets.
    #   last_update_time — When the budget was last recalculated.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS city_budget (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id          INTEGER NOT NULL UNIQUE,
        current_budget   REAL    DEFAULT 0,
        income_per_hour  REAL    DEFAULT 0,
        expense_per_hour REAL    DEFAULT 0,
        last_update_time INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (city_id) REFERENCES cities(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: city_aspects
    # PURPOSE: Flexible key-value store for city stat scores.
    #          Stores computed aspect values (economy, health,
    #          education, infrastructure) that are derived from
    #          owned assets. Updated when assets are bought/upgraded.
    #
    # COLUMNS:
    #   id          — Internal autoincrement PK.
    #   city_id     — References cities.id.
    #   aspect_type — The stat name (e.g. 'economy', 'health').
    #   value       — The current computed value of that stat.
    #
    # UNIQUE: (city_id, aspect_type) — one row per stat per city.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS city_aspects (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id     INTEGER NOT NULL,
        aspect_type TEXT    NOT NULL,
        value       REAL    DEFAULT 0,
        UNIQUE(city_id, aspect_type),
        FOREIGN KEY (city_id) REFERENCES cities(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: city_spending
    # PURPOSE: Cumulative total spending per city. Used for
    #          leaderboards (top spending cities/countries).
    #          Created automatically when a city is created.
    #          Updated every time an asset is bought or upgraded.
    #
    # COLUMNS:
    #   id          — Internal autoincrement PK.
    #   city_id     — References cities.id. UNIQUE — one row per city.
    #   total_spent — Running total of all currency spent in this city.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS city_spending (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id     INTEGER NOT NULL UNIQUE,
        total_spent REAL    DEFAULT 0,
        FOREIGN KEY (city_id) REFERENCES cities(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: action_cooldowns
    # PURPOSE: Per-user cooldowns for game actions like betrayal,
    #          spy, exploration, etc. Prevents action spamming.
    #
    # COLUMNS:
    #   id        — Internal autoincrement PK.
    #   user_id   — References users.user_id.
    #   action    — Action name (e.g. 'betray', 'spy', 'explore').
    #   last_time — Unix timestamp of the last use. Compared against
    #               the cooldown duration to decide if allowed.
    #
    # UNIQUE: (user_id, action) — one cooldown entry per user per action.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS action_cooldowns (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id   INTEGER NOT NULL,
        action    TEXT    NOT NULL,
        last_time INTEGER NOT NULL,
        UNIQUE(user_id, action),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: country_invites
    # PURPOSE: Pending invitations for a user to join a country
    #          with a new city. The invited user can accept or reject.
    #          On acceptance, a new city is created atomically.
    #
    # COLUMNS:
    #   id           — Internal autoincrement PK.
    #   from_user_id — The country owner sending the invite.
    #   to_user_id   — The user being invited.
    #   country_id   — Which country they're being invited to join.
    #   city_name    — The name of the city created on acceptance.
    #   status       — 'pending', 'accepted', or 'rejected'.
    #   created_at   — When the invite was sent.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS country_invites (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user_id INTEGER NOT NULL,
        to_user_id   INTEGER NOT NULL,
        country_id   INTEGER NOT NULL,
        city_name    TEXT    NOT NULL,
        status       TEXT    DEFAULT 'pending',
        created_at   INTEGER DEFAULT (strftime('%s','now')),
        UNIQUE(to_user_id, status),
        FOREIGN KEY (from_user_id) REFERENCES users(user_id),
        FOREIGN KEY (to_user_id)   REFERENCES users(user_id),
        FOREIGN KEY (country_id)   REFERENCES countries(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: country_transfers
    # PURPOSE: Records when ownership of a country is transferred
    #          from one player to another. Includes a freeze period
    #          to prevent abuse immediately after transfer.
    #
    # COLUMNS:
    #   id              — Internal autoincrement PK.
    #   country_id      — The country being transferred.
    #   from_user_id    — Previous owner.
    #   to_user_id      — New owner.
    #   penalty_applied — 1 if a transfer penalty was charged.
    #   status          — 'active' or 'completed'.
    #   transferred_at  — When the transfer was initiated.
    #   expires_at      — Deadline for the transfer to complete.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS country_transfers (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id      INTEGER NOT NULL,
        from_user_id    INTEGER NOT NULL,
        to_user_id      INTEGER NOT NULL,
        penalty_applied INTEGER DEFAULT 0,
        status          TEXT    DEFAULT 'active',
        transferred_at  INTEGER DEFAULT (strftime('%s','now')),
        expires_at      INTEGER NOT NULL,
        FOREIGN KEY (country_id)   REFERENCES countries(id),
        FOREIGN KEY (from_user_id) REFERENCES users(user_id),
        FOREIGN KEY (to_user_id)   REFERENCES users(user_id)
    )
    """)

    conn.commit()
    _create_indexes(conn)


def _create_indexes(conn):
    cursor = conn.cursor()
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_countries_owner    ON countries(owner_id)",
        "CREATE INDEX IF NOT EXISTS idx_cities_country     ON cities(country_id)",
        "CREATE INDEX IF NOT EXISTS idx_cities_owner       ON cities(owner_id)",
        "CREATE INDEX IF NOT EXISTS idx_city_budget_city   ON city_budget(city_id)",
        "CREATE INDEX IF NOT EXISTS idx_city_spending_city ON city_spending(city_id)",
        "CREATE INDEX IF NOT EXISTS idx_action_cd_user     ON action_cooldowns(user_id, action)",
        "CREATE INDEX IF NOT EXISTS idx_invites_to_user    ON country_invites(to_user_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_invites_country    ON country_invites(country_id)",
        "CREATE INDEX IF NOT EXISTS idx_transfers_country  ON country_transfers(country_id)",
    ]
    for sql in indexes:
        cursor.execute(sql)
    conn.commit()
