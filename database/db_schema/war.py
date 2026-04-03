from ..connection import get_db_conn

def create_war_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─── أنواع الجنود ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS troop_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        name_ar TEXT,
        emoji TEXT,
        attack REAL,
        defense REAL,
        hp REAL DEFAULT 100,
        speed REAL DEFAULT 1.0,
        base_cost REAL
    )
    """)

    # ─── جنود المدن ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS city_troops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id INTEGER NOT NULL,
        troop_type_id INTEGER NOT NULL,
        quantity INTEGER DEFAULT 0,
        maintenance_cost REAL DEFAULT 1.0,
        FOREIGN KEY (city_id) REFERENCES cities(id),
        FOREIGN KEY (troop_type_id) REFERENCES troop_types(id),
        UNIQUE(city_id, troop_type_id)
    )
    """)

    # ─── أنواع المعدات ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS equipment_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        name_ar TEXT,
        emoji TEXT,
        attack_bonus REAL DEFAULT 0,
        defense_bonus REAL DEFAULT 0,
        special_effect TEXT,
        base_cost REAL,
        maintenance_cost REAL DEFAULT 1.0
    )
    """)

    # ─── معدات المدن ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS city_equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id INTEGER NOT NULL,
        equipment_type_id INTEGER NOT NULL,
        quantity INTEGER DEFAULT 0,
        FOREIGN KEY (city_id) REFERENCES cities(id),
        FOREIGN KEY (equipment_type_id) REFERENCES equipment_types(id),
        UNIQUE(city_id, equipment_type_id)
    )
    """)

    # ─── المعارك ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attacker_city_id INTEGER,
        defender_city_id INTEGER,
        attacker_power REAL,
        defender_power REAL,
        winner TEXT,
        loot REAL DEFAULT 0,
        created_at INTEGER DEFAULT (strftime('%s','now'))
    )
    """)

    # ─── خسائر المعركة (متقدمة) ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battle_losses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        battle_id INTEGER NOT NULL,
        city_id INTEGER NOT NULL,
        loss_type TEXT NOT NULL, -- troop / equipment
        troop_type_id INTEGER,
        equipment_type_id INTEGER,
        lost_quantity INTEGER DEFAULT 0,
        lost_value REAL DEFAULT 0, -- قيمة الخسارة بالموارد
        FOREIGN KEY (battle_id) REFERENCES battles(id),
        FOREIGN KEY (troop_type_id) REFERENCES troop_types(id),
        FOREIGN KEY (equipment_type_id) REFERENCES equipment_types(id)
    )
    """)

    # ─── تحسين الأداء ───
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_city_troops_city ON city_troops(city_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_city_equipment_city ON city_equipment(city_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_losses_battle ON battle_losses(battle_id)")

    conn.commit()
    _seed_war_data_advanced(conn)

def _seed_war_data_advanced(conn):
    cursor = conn.cursor()

    troops = [
        ("infantry", "مشاة", "🪖", 5, 6, 100, 1.0, 10),
        ("archer", "رماة", "🏹", 7, 3, 80, 1.2, 15),
        ("cavalry", "فرسان", "🐎", 10, 5, 120, 1.5, 30),
        ("elite_special_forces", "قوات خاصة", "🔥", 12, 10, 150, 1.0, 50),
        ("berserker", "غاضبون", "⚔️", 15, 4, 130, 1.3, 60),
        ("pikeman", "رماة الرماح", "🗡", 8, 7, 90, 0.9, 20),
        ("sniper", "قناصة", "🎯", 18, 2, 70, 1.4, 80),
        ("heavy_cavalry", "فرسان ثقيلون", "🐴", 20, 15, 180, 1.1, 100),
        ("engineer", "مهندس", "🛠", 2, 3, 80, 1.0, 25),
        ("medic", "مسعف", "💉", 1, 2, 60, 1.0, 20),
        ("shock_troops", "فرق صاعقة", "⚡", 14, 8, 110, 1.6, 70),
        ("grenadier", "قاذف قنابل", "💣", 16, 6, 100, 1.0, 65),
        ("lancer", "حامل الرمح", "🪓", 12, 7, 120, 1.3, 55),
        ("mounted_archer", "فرسان رماة", "🏇", 11, 6, 100, 1.5, 50),
        ("heavy_infantry", "مشاة ثقيلون", "🛡", 9, 12, 150, 0.8, 45),
        ("scout", "كشافة", "🕵️", 4, 3, 60, 2.0, 20),
        ("assassin", "قاتل متخفي", "🗡️", 20, 2, 70, 1.8, 90),
        ("siege_engineer", "مهندس محاصر", "🏗", 3, 5, 120, 0.7, 60),
        ("drone_operator", "مشغل طائرات بدون طيار", "🤖", 10, 4, 80, 1.2, 70),
        ("tank_commander", "قائد دبابة", "🪖", 25, 20, 300, 0.6, 150),
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO troop_types
        (name, name_ar, emoji, attack, defense, hp, speed, base_cost)
        VALUES (?,?,?,?,?,?,?,?)
    """, troops)

    equipment = [
        ("rifles", "أسلحة نارية", "🔫", 2, 0, None, 20, 1.0),
        ("armor", "دروع", "🛡", 0, 3, None, 25, 1.0),
        ("missiles", "صواريخ", "🚀", 0, 0, "missile", 100, 1.0),
        ("anti_air", "دفاع جوي", "📡", 0, 5, "anti_missile", 120, 1.0),
        ("command_center", "مركز قيادة", "🧠", 5, 5, "boost", 200, 1.0),
        ("tank", "دبابة", "🛡️", 15, 10, "armor_boost", 150, 2.0),
        ("artillery", "مدفعية", "🎯", 20, 2, "siege", 180, 1.5),
        ("drone", "طائرة بدون طيار", "🤖", 10, 3, "recon", 120, 1.2),
        ("helicopter", "هليكوبتر هجوم", "🚁", 18, 5, "air_support", 200, 1.5),
        ("medical_kit", "معدات طبية", "💊", 0, 0, "heal", 50, 0.5),
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO equipment_types
        (name, name_ar, emoji, attack_bonus, defense_bonus, special_effect, base_cost, maintenance_cost)
        VALUES (?,?,?,?,?,?,?,?)
    """, equipment)

    conn.commit()