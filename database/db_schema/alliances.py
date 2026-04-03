from ..connection import get_db_conn

MAX_COUNTRIES_PER_ALLIANCE = 10
MAX_CITIES_PER_COUNTRY = 20

def create_alliance_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─── جدول التحالفات ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        leader_id INTEGER,
        power REAL DEFAULT 0,
        is_open INTEGER DEFAULT 1,
        max_countries INTEGER DEFAULT 10,
        description TEXT DEFAULT '',
        created_at INTEGER DEFAULT (strftime('%s','now'))
    )
    """)

    # ─── أعضاء التحالف (دول) ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_members (
        alliance_id INTEGER,
        user_id INTEGER,
        country_id INTEGER,
        role TEXT DEFAULT 'member',
        loyalty_penalty REAL DEFAULT 0,
        joined_at INTEGER DEFAULT (strftime('%s','now')),
        PRIMARY KEY (alliance_id, user_id),
        FOREIGN KEY (alliance_id) REFERENCES alliances(id)
    )
    """)

    # ─── دعوات التحالف مع كولداون ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_invites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alliance_id INTEGER,
        from_user_id INTEGER,
        to_user_id INTEGER,
        status TEXT DEFAULT 'pending',
        created_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (alliance_id) REFERENCES alliances(id)
    )
    """)

    # ─── ترقيات التحالف (أنواع) ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_upgrade_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        name_ar TEXT NOT NULL,
        emoji TEXT DEFAULT '⬆️',
        category TEXT NOT NULL,
        effect_type TEXT NOT NULL,
        effect_value REAL DEFAULT 0,
        description_ar TEXT,
        price REAL DEFAULT 1000,
        max_level INTEGER DEFAULT 5
    )
    """)

    # ─── ترقيات مشتراة لكل تحالف ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_upgrades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alliance_id INTEGER NOT NULL,
        upgrade_type_id INTEGER NOT NULL,
        level INTEGER DEFAULT 1,
        purchased_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (alliance_id) REFERENCES alliances(id),
        FOREIGN KEY (upgrade_type_id) REFERENCES alliance_upgrade_types(id),
        UNIQUE(alliance_id, upgrade_type_id)
    )
    """)

    # ─── حروب التحالفات ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_wars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alliance_1 INTEGER,
        alliance_2 INTEGER,
        status TEXT DEFAULT 'active',
        winner INTEGER,
        started_at INTEGER DEFAULT (strftime('%s','now')),
        ended_at INTEGER
    )
    """)

    # ─── سجل معارك التحالفات ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_battles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        war_id INTEGER,
        attacker_alliance INTEGER,
        defender_alliance INTEGER,
        result TEXT,
        created_at INTEGER DEFAULT (strftime('%s','now'))
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alliance_members_user ON alliance_members(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alliance_members_alliance ON alliance_members(alliance_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alliance_invites_to ON alliance_invites(to_user_id)")

    conn.commit()
    _seed_upgrade_types(conn)


def _seed_upgrade_types(conn):
    try:
        cursor = conn.cursor()
        upgrades = [
        ("military_boost",   "تعزيز عسكري",    "⚔️", "military",     "attack_bonus",   0.10, "يزيد قوة هجوم أعضاء التحالف 10% لكل مستوى",  2000, 5),
        ("defense_shield",   "درع الدفاع",      "🛡", "military",     "defense_bonus",  0.10, "يزيد دفاع أعضاء التحالف 10% لكل مستوى",       2000, 5),
        ("medical_corps",    "الفيلق الطبي",    "💊", "support",      "hp_bonus",       0.10, "يزيد نقاط الحياة 10% لكل مستوى",              1500, 5),
        ("intel_network",    "شبكة الاستخبارات","🕵️","intelligence", "spy_bonus",      1,    "يرفع مستوى الجواسيس بمقدار 1 لكل مستوى",      1800, 5),
        ("logistics",        "الإمداد والتموين","🚛", "support",      "loot_bonus",     0.05, "يزيد الغنائم 5% لكل مستوى",                   1200, 5),
        ("rapid_deployment", "النشر السريع",    "⚡", "military",     "travel_reduce",  120,  "يقلل وقت السفر 2 دقيقة لكل مستوى",            2500, 5),
        ]
        cursor.executemany("""
            INSERT OR IGNORE INTO alliance_upgrade_types
            (name, name_ar, emoji, category, effect_type, effect_value, description_ar, price, max_level)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, upgrades)
        conn.commit()
    except Exception as e:
        print(f"[alliances] تجاهل seed: {e}")