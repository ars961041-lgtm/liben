from ..connection import get_db_conn


def create_asset_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─── القطاعات ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS asset_sectors (
        id   INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        emoji TEXT DEFAULT '🏗'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assets (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL UNIQUE,
        name_ar     TEXT NOT NULL,
        emoji       TEXT DEFAULT '🏗',
        sector_id   INTEGER NOT NULL REFERENCES asset_sectors(id),
        base_price  REAL NOT NULL,
        base_value  REAL NOT NULL DEFAULT 1.0,
        cost_scale  REAL NOT NULL DEFAULT 1.5,
        maintenance REAL NOT NULL DEFAULT 0,
        income      REAL NOT NULL DEFAULT 0,
        max_level   INTEGER NOT NULL DEFAULT 10,
        build_time  INTEGER DEFAULT 0,
        required_level INTEGER DEFAULT 1,
        stat_economy      REAL DEFAULT 0,
        stat_health       REAL DEFAULT 0,
        stat_education    REAL DEFAULT 0,
        stat_military     REAL DEFAULT 0,
        stat_infrastructure REAL DEFAULT 0,
        pop_effect    REAL DEFAULT 0,
        eco_effect    REAL DEFAULT 0,
        prot_effect   REAL DEFAULT 0
    )
    """)

    # ─── الفروع (مثلاً مصنع → سيارات، هواتف) ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS asset_branches (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id  INTEGER NOT NULL REFERENCES assets(id),
        name      TEXT NOT NULL,
        name_ar   TEXT NOT NULL,
        emoji     TEXT DEFAULT '📦',
        bonus_pct REAL DEFAULT 0.1,
        UNIQUE(asset_id, name)
    )
    """)

    # ─── مشتريات المدينة ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS city_assets (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id   INTEGER NOT NULL REFERENCES cities(id),
        asset_id  INTEGER NOT NULL REFERENCES assets(id),
        branch_id INTEGER REFERENCES asset_branches(id),
        level     INTEGER NOT NULL DEFAULT 1,
        quantity  INTEGER NOT NULL DEFAULT 0,
        UNIQUE(city_id, asset_id, branch_id, level)
    )
    """)

    # ─── سجل العمليات ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS asset_log (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id    INTEGER NOT NULL REFERENCES cities(id),
        user_id    INTEGER NOT NULL REFERENCES users(user_id),
        asset_id   INTEGER NOT NULL REFERENCES assets(id),
        action     TEXT NOT NULL,   -- 'buy' | 'upgrade'
        quantity   INTEGER DEFAULT 0,
        from_level INTEGER DEFAULT 1,
        to_level   INTEGER DEFAULT 1,
        cost       REAL DEFAULT 0,
        ts         INTEGER DEFAULT (strftime('%s','now'))
    )
    """)

    conn.commit()
    _seed_default_assets(conn)


def _seed_default_assets(conn):
    cursor = conn.cursor()

    # القطاعات — no military sector
    sectors = [
        (1, "صحة",        "🏥"),
        (2, "تعليم",       "📚"),
        (3, "اقتصاد",      "💰"),
        (4, "بنية تحتية",  "🛣"),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO asset_sectors (id, name, emoji) VALUES (?,?,?)", sectors
    )


    assets = [
	# (name, name_ar, emoji, sector_id, base_price, base_value, cost_scale,
        #  maintenance, income, max_level, build_time, required_level,
        #  stat_eco, stat_health, stat_edu, stat_mil, stat_infra,
        #  pop_effect, eco_effect, prot_effect)

    # ───── الصحة ─────
    ("hospital",        "مستشفى","🏥",1,200,5.0,1.5,10,0,10,0,1,0,5,0,0,0,0.05,0,0),
    ("clinic",          "عيادة","🩺",1,80,2.0,1.4,4,0,10,0,1,0,2,0,0,0,0.02,0,0),
    ("pharmacy",        "صيدلية","💊",1,120,2.5,1.4,5,10,10,0,1,0,3,0,0,0,0.02,0,0),
    ("medical_lab",     "مختبر طبي","🧪",1,180,3.5,1.5,8,12,10,0,2,0,4,0,0,0,0.02,0,0),
    ("ambulance_center","مركز إسعاف","🚑",1,220,4.0,1.5,10,0,10,0,2,0,5,0,0,0,0.03,0,0),
    ("research_medical","مركز أبحاث طبية","🔬",1,500,6.0,1.6,18,0,10,0,3,0,8,0,0,0,0.04,0,0),
    ("health_center",   "مركز صحي","🏥",1,160,3.0,1.4,7,0,10,0,1,0,4,0,0,0,0.02,0,0),

    # ───── التعليم ─────
    ("school","مدرسة","🏫",2,300,5.0,1.5,14,0,10,0,1,0,0,5,0,0,0,0.03,0),
    ("university","جامعة","🎓",2,800,12.0,1.6,40,0,10,0,3,0,0,12,0,0,0,0.08,0),
    ("kindergarten","روضة","🧸",2,140,2.5,1.4,6,0,10,0,1,0,0,3,0,0,0,0.02,0),
    ("institute","معهد","🏫",2,260,4.0,1.5,12,0,10,0,2,0,0,6,0,0,0,0.03,0),
    ("research_center","مركز أبحاث","🔬",2,600,7.0,1.6,22,0,10,0,3,0,0,9,0,0,0,0.05,0),
    ("library","مكتبة","📖",2,150,2.5,1.4,5,0,10,0,1,0,0,3,0,0,0,0.02,0),
    ("training_center","مركز تدريب","🎓",2,300,4.5,1.5,10,0,10,0,2,0,0,6,0,0,0,0.03,0),

    # ───── الاقتصاد ─────
    ("factory","مصنع","🏭",3,400,5.0,1.6,20,60,10,0,1,5,0,0,0,0,0,0.05,0),
    ("bank_local","بنك محلي","🏦",3,600,3.0,1.6,30,20,10,0,2,3,0,0,0,0,0,0.04,0),
    ("market","سوق تجاري","🛒",3,160,2.0,1.4,8,30,10,0,1,2,0,0,0,0,0,0.02,0),
    ("tech_company","شركة تقنية","💻",3,700,6.0,1.6,25,80,10,0,2,6,0,0,0,0,0,0.05,0),
    ("logistics_company","شركة لوجستية","🚚",3,350,4.5,1.5,15,40,10,0,1,4,0,0,0,0,0,0.03,0),
    ("insurance_company","شركة تأمين","🛡",3,500,5.0,1.5,18,35,10,0,2,5,0,0,0,0,0,0.04,0),
    ("mall","مول","🏬",3,900,7.0,1.6,30,90,10,0,2,7,0,0,0,0,0,0.06,0),
    ("port","ميناء","⚓️",3,1200,8.0,1.7,40,120,10,0,3,8,0,0,0,0,0,0.07,0),
    ("data_center","مركز بيانات","🖥",3,800,6.0,1.6,28,70,10,0,2,6,0,0,0,0,0,0.05,0),
    ("media_company","شركة إعلام","📺",3,400,4.0,1.5,16,35,10,0,1,4,0,0,0,0,0,0.03,0),
    ("hotel","فندق","🏨",3,600,5.0,1.6,20,50,10,0,2,5,0,0,0,0,0,0.04,0),
    ("tourism_company","شركة سياحة","🗺",3,350,4.0,1.5,14,40,10,0,1,4,0,0,0,0,0,0.03,0),

    # ───── البنية التحتية ─────
    ("infrastructure","بنية تحتية","🛣",4,160,5.0,1.4,6,0,10,0,1,0,0,0,0,5,0.01,0.01,0),
    ("power_plant","محطة طاقة","⚡️",4,700,8.0,1.6,36,40,10,0,2,2,0,0,0,8,0,0.03,0),
    ("airport","مطار","✈️",4,1500,9.0,1.7,50,120,10,0,3,7,0,0,0,9,0,0.05,0),
    ("railway","سكة حديد","🚆",4,1000,7.0,1.6,35,70,10,0,2,6,0,0,0,8,0,0.04,0),
    ("solar_plant","طاقة شمسية","☀️",4,900,6.5,1.6,28,60,10,0,2,5,0,0,0,7,0,0.03,0),
    ("wind_plant","طاقة رياح","🌬",4,850,6.0,1.6,26,55,10,0,2,5,0,0,0,7,0,0.03,0),
    ("water_station","محطة مياه","🚰",4,500,5.0,1.5,20,25,10,0,1,3,0,0,0,6,0,0.02,0),
    ("construction_company","شركة مقاولات","🏗",4,700,6.0,1.6,24,60,10,0,2,5,0,0,0,8,0,0.04,0)
]      
    cursor.executemany("""
        INSERT OR IGNORE INTO assets
        (name, name_ar, emoji, sector_id, base_price, base_value, cost_scale,
         maintenance, income, max_level, build_time, required_level,
         stat_economy, stat_health, stat_education, stat_military, stat_infrastructure,
         pop_effect, eco_effect, prot_effect)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, assets)

    branch_types = [
        # (asset_id_name, branch_name, branch_name_ar, emoji, bonus_pct)
        ("production","production","إنتاج","🏭",0.10),
        ("export","export","تصدير","📦",0.12),
        ("technology","technology","تقنية","💻",0.15),
        ("marketing","marketing","تسويق","📢",0.08),
        ("automation","automation","أتمتة","🤖",0.14),
        ("quality","quality","جودة","⭐",0.09),
        ("research","research","أبحاث","🔬",0.11),
        ("training","training","تدريب","🎓",0.07),
        ("logistics","logistics","لوجستيات","🚚",0.10),
        ("security","security","حماية","🛡",0.06),
        ]

    # إنشاء الفروع لكل asset
    cursor.execute("SELECT id,name FROM assets")
    assets_db = cursor.fetchall()

    for a in assets_db:
        for b in branch_types:
            cursor.execute("""
            INSERT OR IGNORE INTO asset_branches
            (asset_id,name,name_ar,emoji,bonus_pct)
            VALUES (?,?,?,?,?)
            """,(a["id"],b[0],b[2],b[3],b[4]))

    conn.commit()