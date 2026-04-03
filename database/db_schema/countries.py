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
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user_id INTEGER NOT NULL,   -- صاحب الدولة
        to_user_id   INTEGER NOT NULL,   -- اللاعب المدعو
        country_id   INTEGER NOT NULL,   -- الدولة
        city_name    TEXT NOT NULL,      -- اسم المدينة المقترح
        status TEXT DEFAULT 'pending',   -- pending / accepted / rejected
        created_at INTEGER DEFAULT (strftime('%s','now')),
        UNIQUE(to_user_id, status)  -- يمنع أكثر من دعوة لنفس الشخص
    );
    """)

    conn.commit()
    
