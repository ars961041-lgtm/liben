from ..connection import get_db_conn

def create_countries_tables():
    conn = get_db_conn()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS countries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        owner_id INTEGER,
        population INTEGER DEFAULT 0,
        area REAL DEFAULT 1000.0,
        level INTEGER DEFAULT 1,
        development INTEGER DEFAULT 0,
        max_officials INTEGER DEFAULT 10,
        max_cities INTEGER DEFAULT 10,
        stability INTEGER DEFAULT 100,
        happiness INTEGER DEFAULT 100,
        last_owner_time INTEGER,
        last_active INTEGER,
        FOREIGN KEY (owner_id) REFERENCES users(user_id) ON DELETE SET NULL
    );
    ''')
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_countries_owner
    ON countries(owner_id);
    """)
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS country_state (
        country_id INTEGER PRIMARY KEY,
        income INTEGER DEFAULT 0,
        expenses INTEGER DEFAULT 0,
        military_power INTEGER DEFAULT 0,
        defense_level INTEGER DEFAULT 0,
        is_at_war INTEGER DEFAULT 0,
        is_protected INTEGER DEFAULT 0,
        FOREIGN KEY (country_id) REFERENCES countries(id) ON DELETE CASCADE
    );
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS country_stats (
        country_id INTEGER PRIMARY KEY,
        economy_score INTEGER DEFAULT 0,
        health_level INTEGER DEFAULT 0,
        education_level INTEGER DEFAULT 0,
        infrastructure_level INTEGER DEFAULT 0,
        total_score INTEGER DEFAULT 0,
        rank INTEGER,
        updated_at INTEGER,
        FOREIGN KEY (country_id) REFERENCES countries(id) ON DELETE CASCADE
    );
    ''')
    
    conn.commit()