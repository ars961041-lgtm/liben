from database.connection import get_db_conn


def create_daily_tasks_pool_table():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # TABLE: daily_tasks_pool
    # PURPOSE: Master pool of all possible daily task templates.
    #          Built dynamically from asset/troop/equipment tables.
    #          Grows during the day if the pool is exhausted by many
    #          cities. Fully cleared and rebuilt at midnight (Yemen TZ).
    #
    # COLUMNS:
    #   id                — Internal autoincrement PK.
    #   type              — Task category (see types below).
    #   description       — Human-readable task text. Unique key.
    #   asset_id          — For upgrade_asset: which asset to upgrade.
    #   troop_type_id     — For buy_troops: which troop type.
    #   equipment_type_id — For buy_equipment: which equipment type.
    #   required_level    — Target level (level-based tasks).
    #                       Also used as sector_id for reach_asset_count.
    #   required_quantity — Units to purchase / target value.
    #   reward_gold       — Gold reward for completing this task.
    #   reward_troops     — Optional troop bonus (JSON or NULL).
    #   difficulty        — 1=easy, 2=medium, 3=hard.
    #   category          — Display grouping: development/military/economy/general.
    #   pool_date         — YYYY-MM-DD (Yemen TZ) when this row was generated.
    #                       Used to detect stale pool entries at midnight reset.
    #
    # TASK TYPES:
    #   upgrade_asset      — city_assets.level >= required_level
    #   buy_troops         — city_troops.quantity >= required_quantity
    #   buy_equipment      — city_equipment.quantity >= required_quantity
    #   upgrade_city_level — cities.level >= required_level
    #   accumulate_balance — user_accounts.balance >= required_quantity
    #   total_army_power   — computed power >= required_quantity
    #   reach_asset_count  — SUM(city_assets.quantity) for sector >= required_quantity
    #   collect_income     — income collected N times today (tracked in task_data)
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_tasks_pool (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        type              TEXT    NOT NULL,
        description       TEXT    NOT NULL UNIQUE,
        asset_id          INTEGER DEFAULT NULL,
        troop_type_id     INTEGER DEFAULT NULL,
        equipment_type_id INTEGER DEFAULT NULL,
        required_level    INTEGER DEFAULT NULL,
        required_quantity INTEGER DEFAULT NULL,
        reward_gold       INTEGER NOT NULL DEFAULT 200,
        reward_troops     TEXT    DEFAULT NULL,
        difficulty        INTEGER NOT NULL DEFAULT 1,
        category          TEXT    NOT NULL DEFAULT 'general',
        pool_date         TEXT    NOT NULL DEFAULT ''
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: daily_tasks
    # PURPOSE: Tasks assigned to a specific city for a specific day.
    #          One set per city per calendar day (Yemen TZ).
    #          Enforced by UNIQUE(city_id, date_key).
    #
    # COLUMNS:
    #   id               — Internal autoincrement PK.
    #   city_id          — References cities.id.
    #   task_data        — JSON snapshot of the task at assignment time.
    #   date_key         — YYYY-MM-DD (Yemen TZ) of assignment day.
    #                      Used to enforce one-time-per-day and for reset.
    #   assigned_at      — Unix timestamp when assigned.
    #   completed        — 1 = task condition is met.
    #   reward_collected — 1 = reward has been claimed.
    #
    # CONSTRAINT: UNIQUE(city_id, date_key, task_pool_id) prevents
    #             the same task being assigned twice to the same city
    #             on the same day.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_tasks (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id          INTEGER NOT NULL,
        task_data        TEXT    NOT NULL,
        date_key         TEXT    NOT NULL DEFAULT '',
        task_pool_id     INTEGER NOT NULL DEFAULT 0,
        assigned_at      INTEGER DEFAULT (strftime('%s','now')),
        completed        INTEGER DEFAULT 0,
        reward_collected INTEGER DEFAULT 0,
        UNIQUE(city_id, date_key, task_pool_id),
        FOREIGN KEY (city_id) REFERENCES cities(id)
    )
    """)

    # Safe migration: add new columns to existing databases
    for col, definition in [
        ("date_key",     "TEXT NOT NULL DEFAULT ''"),
        ("task_pool_id", "INTEGER NOT NULL DEFAULT 0"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE daily_tasks ADD COLUMN {col} {definition}")
        except Exception:
            pass

    for col, definition in [
        ("pool_date", "TEXT NOT NULL DEFAULT ''"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE daily_tasks_pool ADD COLUMN {col} {definition}")
        except Exception:
            pass

    conn.commit()
    _ensure_pool_built(conn)


def _ensure_pool_built(conn):
    """
    Builds the pool if it is empty or stale (from a previous day).
    Called at startup — safe to call multiple times.
    """
    from database.db_queries.daily_tasks_queries import _today_yemen, _build_pool
    today = _today_yemen()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) AS c FROM daily_tasks_pool WHERE pool_date = ?", (today,)
    )
    if cursor.fetchone()["c"] == 0:
        _build_pool(conn, today)
