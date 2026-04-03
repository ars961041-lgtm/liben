from ..connection import get_db_conn


def create_war_economy_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─── الجنود المصابون ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS injured_troops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id INTEGER NOT NULL,
        troop_type_id INTEGER NOT NULL,
        quantity INTEGER DEFAULT 0,
        heal_time INTEGER NOT NULL,
        created_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (city_id) REFERENCES cities(id),
        FOREIGN KEY (troop_type_id) REFERENCES troop_types(id)
    )
    """)

    # ─── المعدات التالفة ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS damaged_equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id INTEGER NOT NULL,
        equipment_type_id INTEGER NOT NULL,
        quantity INTEGER DEFAULT 0,
        repair_cost REAL DEFAULT 0,
        repair_time INTEGER NOT NULL,
        created_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (city_id) REFERENCES cities(id),
        FOREIGN KEY (equipment_type_id) REFERENCES equipment_types(id)
    )
    """)

    # ─── فترة تعافي الدولة بعد المعركة ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS country_recovery (
        country_id INTEGER PRIMARY KEY,
        recovery_until INTEGER NOT NULL,
        reason TEXT DEFAULT 'battle',
        FOREIGN KEY (country_id) REFERENCES countries(id)
    )
    """)

    # ─── تكاليف الحرب (سجل) ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS war_costs_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        battle_id INTEGER,
        action TEXT NOT NULL,
        amount REAL NOT NULL,
        created_at INTEGER DEFAULT (strftime('%s','now'))
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_injured_city ON injured_troops(city_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_damaged_city ON damaged_equipment(city_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recovery_country ON country_recovery(country_id)")

    conn.commit()
