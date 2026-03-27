from ..connection import get_db_conn

def create_facilities_tables():
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # قطاع المنشآت
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sectors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );
    ''')

    # أنواع المنشآت
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS facility_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sector_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        max_level INTEGER DEFAULT 10,
        base_population_effect INTEGER DEFAULT 0,
        base_area_effect REAL DEFAULT 0,
        FOREIGN KEY (sector_id) REFERENCES sectors(id) ON DELETE CASCADE
    );
    ''')

    # Index على sector_id
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_facility_types_sector
    ON facility_types(sector_id);
    ''')

    conn.commit()