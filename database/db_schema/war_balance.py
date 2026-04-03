from ..connection import get_db_conn


def create_war_balance_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─── طابور الإصلاح (إصلاح مكلف + وقت) ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS repair_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id INTEGER NOT NULL,
        equipment_type_id INTEGER NOT NULL,
        quantity INTEGER DEFAULT 0,
        repair_cost REAL DEFAULT 0,
        repair_ready_at INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (city_id) REFERENCES cities(id)
    )
    """)

    # ─── تعب الجيش ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS army_fatigue (
        country_id INTEGER PRIMARY KEY,
        fatigue_level REAL DEFAULT 0.0,
        last_battle_at INTEGER DEFAULT 0,
        FOREIGN KEY (country_id) REFERENCES countries(id)
    )
    """)

    # ─── سجل الحروب ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battle_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        battle_id INTEGER NOT NULL,
        attacker_country_id INTEGER NOT NULL,
        defender_country_id INTEGER NOT NULL,
        attacker_name TEXT,
        defender_name TEXT,
        winner_country_id INTEGER,
        attacker_losses_pct REAL DEFAULT 0,
        defender_losses_pct REAL DEFAULT 0,
        loot REAL DEFAULT 0,
        battle_type TEXT DEFAULT 'normal',
        duration_seconds INTEGER DEFAULT 0,
        created_at INTEGER DEFAULT (strftime('%s','now'))
    )
    """)

    # ─── عمود disabled_until في city_assets (إذا لم يكن موجوداً) ───
    try:
        cursor.execute("ALTER TABLE city_assets ADD COLUMN disabled_until INTEGER DEFAULT 0")
    except Exception:
        pass  # العمود موجود بالفعل

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_repair_queue_city ON repair_queue(city_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_army_fatigue ON army_fatigue(country_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_history_attacker ON battle_history(attacker_country_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_history_defender ON battle_history(defender_country_id)")

    conn.commit()
