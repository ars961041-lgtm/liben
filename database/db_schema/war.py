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
        # ── مشاة (Infantry) ──
        ("infantry",            "مشاة خفيفة",              "🪖", 5,  6,  100, 1.0,  10),
        ("heavy_infantry",      "مشاة ثقيلة",              "🛡", 9,  12, 150, 0.8,  45),
        ("elite_special_forces","قوات خاصة",               "🔥", 12, 10, 150, 1.0,  50),
        ("shock_troops",        "فرق صاعقة",               "⚡", 14, 8,  110, 1.6,  70),
        ("berserker",           "غاضبون",                  "⚔️", 15, 4,  130, 1.3,  60),
        ("grenadier",           "قاذف قنابل",              "💣", 16, 6,  100, 1.0,  65),
        ("assassin",            "قاتل متخفي",              "🗡️", 20, 2,  70,  1.8,  90),
        # ── رماة (Ranged) ──
        ("archer",              "رماة",                    "🏹", 7,  3,  80,  1.2,  15),
        ("pikeman",             "رماة الرماح",             "🗡", 8,  7,  90,  0.9,  20),
        ("sniper",              "قناصة",                   "🎯", 18, 2,  70,  1.4,  80),
        # ── فرسان (Cavalry) ──
        ("cavalry",             "فرسان",                   "🐎", 10, 5,  120, 1.5,  30),
        ("heavy_cavalry",       "فرسان ثقيلون",            "🐴", 20, 15, 180, 1.1, 100),
        ("mounted_archer",      "فرسان رماة",              "🏇", 11, 6,  100, 1.5,  50),
        ("lancer",              "حامل الرمح",              "🪓", 12, 7,  120, 1.3,  55),
        # ── مدرعات (Armored) ──
        ("tank_commander",      "قائد دبابة",              "🪖", 25, 20, 300, 0.6, 150),
        ("armored_unit",        "وحدة مدرعة",              "🛡️", 22, 18, 280, 0.7, 130),
        ("artillery_crew",      "طاقم مدفعية",             "🎯", 28, 5,  200, 0.8, 160),
        # ── وحدات جوية (Air) ──
        ("drone_operator",      "مشغل طائرات بدون طيار",  "🤖", 10, 4,  80,  1.2,  70),
        ("jet_pilot",           "طيار مقاتلة",             "✈️", 30, 8,  120, 1.0, 200),
        ("helicopter_crew",     "طاقم هليكوبتر",           "🚁", 18, 6,  100, 1.1, 140),
        # ── دعم (Support) ──
        ("medic",               "مسعف",                    "💉", 1,  2,  60,  1.0,  20),
        ("engineer",            "مهندس",                   "🛠", 2,  3,  80,  1.0,  25),
        ("siege_engineer",      "مهندس محاصر",             "🏗", 3,  5,  120, 0.7,  60),
        ("scout",               "كشافة",                   "🕵️", 4,  3,  60,  2.0,  20),
        ("logistics_officer",   "ضابط لوجستي",             "📦", 2,  4,  70,  1.0,  30),
        ("comms_officer",       "ضابط اتصالات",            "📡", 3,  4,  70,  1.0,  35),
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO troop_types
        (name, name_ar, emoji, attack, defense, hp, speed, base_cost)
        VALUES (?,?,?,?,?,?,?,?)
    """, troops)

    equipment = [
        # ── أسلحة (Weapons) ──
        ("rifles",          "أسلحة نارية",          "🔫", 2,  0,  None,           20,  1.0),
        ("heavy_weapons",   "أسلحة ثقيلة",          "💥", 5,  0,  None,           60,  1.2),
        ("sniper_rifles",   "بنادق قنص",            "🎯", 4,  0,  None,           45,  1.0),
        ("explosives",      "متفجرات",              "💣", 6,  0,  "siege",        80,  1.0),
        ("missiles",        "صواريخ",               "🚀", 0,  0,  "missile",     100,  1.0),
        # ── دروع (Armor) ──
        ("armor",           "دروع خفيفة",           "🛡", 0,  3,  None,           25,  1.0),
        ("heavy_armor",     "دروع ثقيلة",           "🛡️", 0,  6,  None,           55,  1.2),
        ("tank",            "دبابة",                "🛡️", 15, 10, "armor_boost",  150, 2.0),
        ("armored_vehicle", "مركبة مدرعة",          "🚗", 8,  8,  "armor_boost",  90,  1.5),
        # ── جوية (Air) ──
        ("drone",           "طائرة بدون طيار",      "🤖", 10, 3,  "recon",       120,  1.2),
        ("helicopter",      "هليكوبتر هجوم",        "🚁", 18, 5,  "air_support", 200,  1.5),
        ("jet_fighter",     "مقاتلة نفاثة",         "✈️", 30, 8,  "air_strike",  350,  2.0),
        ("surveillance_drone","طائرة مراقبة",       "📷", 2,  2,  "recon",        80,  1.0),
        # ── مدفعية (Artillery) ──
        ("artillery",       "مدفعية",               "🎯", 20, 2,  "siege",       180,  1.5),
        ("rocket_launcher", "قاذف صواريخ",          "🚀", 22, 1,  "siege",       200,  1.5),
        # ── دفاع (Defense) ──
        ("anti_air",        "دفاع جوي",             "📡", 0,  5,  "anti_missile",120,  1.0),
        ("bunker",          "بنكر دفاعي",           "🏰", 0,  8,  "fortify",     160,  1.2),
        ("minefield",       "حقل ألغام",            "💥", 0,  6,  "trap",        100,  1.0),
        # ── تكتيكية (Tactical) ──
        ("command_center",  "مركز قيادة",           "🧠", 5,  5,  "boost",       200,  1.0),
        ("comms_system",    "نظام اتصالات",         "📡", 3,  3,  "boost",       130,  1.0),
        ("radar_system",    "نظام رادار",           "📡", 2,  4,  "recon",       150,  1.0),
        ("cyber_unit",      "وحدة إلكترونية",       "💻", 4,  4,  "hack",        180,  1.0),
        # ── دعم (Support) ──
        ("medical_kit",     "معدات طبية",           "💊", 0,  0,  "heal",         50,  0.5),
        ("supply_truck",    "شاحنة إمداد",          "🚛", 0,  2,  "supply",       70,  0.8),
        ("field_hospital",  "مستشفى ميداني",        "🏥", 0,  0,  "heal",        120,  0.8),
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO equipment_types
        (name, name_ar, emoji, attack_bonus, defense_bonus, special_effect, base_cost, maintenance_cost)
        VALUES (?,?,?,?,?,?,?,?)
    """, equipment)

    conn.commit()