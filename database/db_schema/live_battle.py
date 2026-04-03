from ..connection import get_db_conn


def create_live_battle_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─── حالة المعركة الحية ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battle_state (
        battle_id INTEGER PRIMARY KEY,
        atk_power REAL DEFAULT 0,
        def_power REAL DEFAULT 0,
        atk_initial REAL DEFAULT 0,
        def_initial REAL DEFAULT 0,
        last_tick INTEGER DEFAULT 0,
        tick_count INTEGER DEFAULT 0,
        FOREIGN KEY (battle_id) REFERENCES country_battles(id)
    )
    """)

    # ─── تأثيرات المعركة المؤقتة (بطاقات / تعزيزات) ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battle_effects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        battle_id INTEGER NOT NULL,
        country_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        effect_type TEXT NOT NULL,
        value REAL DEFAULT 0,
        expires_at INTEGER NOT NULL,
        source TEXT DEFAULT 'card',
        created_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (battle_id) REFERENCES country_battles(id)
    )
    """)

    # ─── كولداون أفعال المعركة لكل لاعب ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battle_action_cooldowns (
        battle_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        last_used INTEGER NOT NULL,
        PRIMARY KEY (battle_id, user_id, action)
    )
    """)

    # ─── سجل أحداث المعركة (للتقرير النهائي) ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battle_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        battle_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        description TEXT,
        atk_power_snapshot REAL DEFAULT 0,
        def_power_snapshot REAL DEFAULT 0,
        created_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (battle_id) REFERENCES country_battles(id)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_state ON battle_state(battle_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_effects_battle ON battle_effects(battle_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_events_battle ON battle_events(battle_id)")

    conn.commit()
