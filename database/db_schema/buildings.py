from ..connection import get_db_conn

def create_buildings_table():
    conn = get_db_conn()
    cursor = conn.cursor()

    # جدول المباني
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS buildings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        country_id INTEGER NOT NULL,
        building_type TEXT NOT NULL,
        quantity INTEGER DEFAULT 1,
        level INTEGER DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (country_id) REFERENCES countries(id) ON DELETE CASCADE
    );
    ''')

    # Index على user_id و country_id و building_type
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_buildings_country_type
    ON buildings(country_id, building_type);
    ''')

    conn.commit()