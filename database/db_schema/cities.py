from ..connection import get_db_conn

def create_cities_tables():
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # جدول المدن
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        owner_id INTEGER,
        country_id INTEGER,
        population INTEGER DEFAULT 0,
        area REAL DEFAULT 100.0,
        level INTEGER DEFAULT 1,
        last_active INTEGER,
        UNIQUE(name, country_id),
        FOREIGN KEY (owner_id) REFERENCES users(user_id) ON DELETE SET NULL,
        FOREIGN KEY (country_id) REFERENCES countries(id) ON DELETE CASCADE
    );
    ''')

    # Index على اسم المدينة
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_cities_name
    ON cities(name);
    ''')

    # مرافق المدينة
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS city_facilities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id INTEGER NOT NULL,
        facility_type_id INTEGER NOT NULL,
        level INTEGER DEFAULT 1,
        count INTEGER DEFAULT 1,
        FOREIGN KEY (city_id) REFERENCES cities(id) ON DELETE CASCADE,
        FOREIGN KEY (facility_type_id) REFERENCES facility_types(id) ON DELETE CASCADE
    );
    ''')

    # الوحدات العسكرية
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS city_military_units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id INTEGER NOT NULL,
        unit_type TEXT NOT NULL,
        quantity INTEGER DEFAULT 0,
        power_per_unit INTEGER DEFAULT 1,
        population_effect INTEGER DEFAULT 1,
        area_effect REAL DEFAULT 1.0,
        FOREIGN KEY (city_id) REFERENCES cities(id) ON DELETE CASCADE
    );
    ''')

    # ميزانية المدن
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS city_budget (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER,
        city_id INTEGER,
        current_budget INTEGER DEFAULT 0,
        last_update_time INTEGER,
        FOREIGN KEY (city_id) REFERENCES cities(id) ON DELETE CASCADE,
        FOREIGN KEY (country_id) REFERENCES countries(id) ON DELETE CASCADE
    );
    ''')

    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_city_budget_country
    ON city_budget(country_id);
    ''')

    # سجل ملكية المدن
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS city_ownership_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id INTEGER,
        previous_owner_id INTEGER,
        new_owner_id INTEGER,
        transaction_time INTEGER,
        price INTEGER
    );
    ''')

    conn.commit()