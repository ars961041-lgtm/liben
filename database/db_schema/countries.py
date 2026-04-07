from ..connection import get_db_conn


def create_countries_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS countries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        owner_id INTEGER NOT NULL,
        created_at INTEGER DEFAULT (strftime('%s','now')),
        economy_score REAL DEFAULT 0,
        health_level REAL DEFAULT 0,
        education_level REAL DEFAULT 0,
        military_power REAL DEFAULT 0,
        infrastructure_level REAL DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS country_stats (
        country_id INTEGER PRIMARY KEY,
        economy_score REAL DEFAULT 0,
        health_level REAL DEFAULT 0,
        education_level REAL DEFAULT 0,
        military_power REAL DEFAULT 0,
        infrastructure_level REAL DEFAULT 0,
        FOREIGN KEY (country_id) REFERENCES countries(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER,
        owner_id INTEGER,
        name TEXT NOT NULL,
        level INTEGER DEFAULT 1,
        population INTEGER DEFAULT 1000,
        area REAL DEFAULT 0,
        created_at INTEGER DEFAULT (strftime('%s','now')),
        last_collect_time INTEGER DEFAULT (strftime('%s','now')),
        economy_score REAL DEFAULT 0,
        health_level REAL DEFAULT 0,
        education_level REAL DEFAULT 0,
        military_power REAL DEFAULT 0,
        infrastructure_level REAL DEFAULT 0,
        FOREIGN KEY (country_id) REFERENCES countries(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS buildings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id INTEGER NOT NULL,
        building_type TEXT NOT NULL,
        quantity INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        FOREIGN KEY (city_id) REFERENCES cities(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS city_budget (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id INTEGER NOT NULL,
        current_budget REAL DEFAULT 0,
        income_per_hour REAL DEFAULT 0,
        expense_per_hour REAL DEFAULT 0,
        last_update_time INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (city_id) REFERENCES cities(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS city_aspects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id INTEGER NOT NULL,
        aspect_type TEXT NOT NULL,
        value REAL DEFAULT 0,
        FOREIGN KEY (city_id) REFERENCES cities(id),
        UNIQUE(city_id, aspect_type)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS country_invites (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user_id INTEGER NOT NULL,
        to_user_id   INTEGER NOT NULL,
        country_id   INTEGER NOT NULL,
        city_name    TEXT    NOT NULL,
        status       TEXT    DEFAULT 'pending',
        created_at   INTEGER DEFAULT (strftime('%s','now')),
        UNIQUE(to_user_id, status)
    );
    """)

    # ─── نقل الدولة ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS country_transfers (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id       INTEGER NOT NULL,
        from_user_id     INTEGER NOT NULL,
        to_user_id       INTEGER NOT NULL,
        penalty_applied  INTEGER DEFAULT 0,
        status           TEXT    DEFAULT 'active',
        transferred_at   INTEGER DEFAULT (strftime('%s','now')),
        expires_at       INTEGER NOT NULL
    )
    """)

    # ─── كولداون الأفعال العامة (خيانة، إعادة تسمية، ...) ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS action_cooldowns (
        user_id   INTEGER NOT NULL,
        action    TEXT    NOT NULL,
        last_time INTEGER NOT NULL,
        PRIMARY KEY (user_id, action)
    )
    """)

    # ─── إجمالي إنفاق المدن (بالسعر الأصلي قبل الخصومات) ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS city_spending (
        city_id     INTEGER PRIMARY KEY,
        total_spent REAL    DEFAULT 0
    )
    """)

    conn.commit()
    create_countries_indexes()


def create_countries_indexes():
    """إنشاء الفهارس لتحسين أداء الاستعلامات."""
    conn = get_db_conn()
    cursor = conn.cursor()

    indexes = [
        # countries
        "CREATE INDEX IF NOT EXISTS idx_countries_owner ON countries(owner_id)",
        # cities
        "CREATE INDEX IF NOT EXISTS idx_cities_country ON cities(country_id)",
        "CREATE INDEX IF NOT EXISTS idx_cities_owner ON cities(owner_id)",
        # buildings
        "CREATE INDEX IF NOT EXISTS idx_buildings_city ON buildings(city_id)",
        "CREATE INDEX IF NOT EXISTS idx_buildings_city_type ON buildings(city_id, building_type)",
        # city_budget
        "CREATE INDEX IF NOT EXISTS idx_city_budget_city ON city_budget(city_id)",
        # country_invites
        "CREATE INDEX IF NOT EXISTS idx_invites_to_user ON country_invites(to_user_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_invites_country ON country_invites(country_id)",
        # country_transfers
        "CREATE INDEX IF NOT EXISTS idx_transfers_country ON country_transfers(country_id)",
    ]

    for sql in indexes:
        cursor.execute(sql)

    conn.commit()
    
