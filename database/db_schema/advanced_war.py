from ..connection import get_db_conn


def create_advanced_war_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─── المعارك المتقدمة ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS country_battles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attacker_country_id INTEGER NOT NULL,
        defender_country_id INTEGER NOT NULL,
        attacker_user_id INTEGER NOT NULL,
        defender_user_id INTEGER NOT NULL,
        status TEXT DEFAULT 'traveling',
        travel_end_time INTEGER,
        battle_end_time INTEGER,
        winner_country_id INTEGER,
        loot REAL DEFAULT 0,
        attacker_power REAL DEFAULT 0,
        defender_power REAL DEFAULT 0,
        battle_type TEXT DEFAULT 'normal',
        created_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (attacker_country_id) REFERENCES countries(id),
        FOREIGN KEY (defender_country_id) REFERENCES countries(id)
    )
    """)

    # ─── داعمو المعركة ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battle_supporters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        battle_id INTEGER NOT NULL,
        country_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        side TEXT NOT NULL,
        power_contributed REAL DEFAULT 0,
        joined_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (battle_id) REFERENCES country_battles(id),
        UNIQUE(battle_id, country_id)
    )
    """)

    # ─── وحدات الجواسيس ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS spy_units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL,
        spy_count INTEGER DEFAULT 0,
        counter_intel INTEGER DEFAULT 0,
        spy_level INTEGER DEFAULT 1,
        defense_level INTEGER DEFAULT 1,
        camouflage_level INTEGER DEFAULT 1,
        FOREIGN KEY (country_id) REFERENCES countries(id),
        UNIQUE(country_id)
    )
    """)

    # ─── سجل عمليات التجسس ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS spy_operations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attacker_country_id INTEGER NOT NULL,
        target_country_id INTEGER NOT NULL,
        result TEXT,
        info_obtained TEXT,
        created_at INTEGER DEFAULT (strftime('%s','now'))
    )
    """)

    # ─── أنواع البطاقات ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        name_ar TEXT NOT NULL,
        emoji TEXT DEFAULT '🃏',
        category TEXT NOT NULL,
        effect_type TEXT NOT NULL,
        effect_value REAL DEFAULT 0,
        description_ar TEXT,
        price REAL DEFAULT 500,
        max_uses INTEGER DEFAULT 1
    )
    """)

    # ─── بطاقات المستخدمين ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        card_id INTEGER NOT NULL,
        quantity INTEGER DEFAULT 1,
        FOREIGN KEY (card_id) REFERENCES cards(id),
        UNIQUE(user_id, card_id)
    )
    """)

    # ─── سمعة اللاعبين ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS player_reputation (
        user_id INTEGER PRIMARY KEY,
        loyalty_score INTEGER DEFAULT 50,
        battles_helped INTEGER DEFAULT 0,
        battles_ignored INTEGER DEFAULT 0,
        betrayals INTEGER DEFAULT 0,
        reputation_title TEXT DEFAULT 'محايد'
    )
    """)

    # ─── طلبات الدعم ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS support_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        battle_id INTEGER NOT NULL,
        requesting_country_id INTEGER NOT NULL,
        target_country_id INTEGER,
        target_user_id INTEGER NOT NULL,
        side TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        last_sent_at INTEGER DEFAULT (strftime('%s','now')),
        created_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (battle_id) REFERENCES country_battles(id)
    )
    """)

    # ─── نظام الاكتشاف والرؤية ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS country_visibility (
        country_id INTEGER PRIMARY KEY,
        visibility_mode TEXT DEFAULT 'public',
        daily_attack_code TEXT,
        code_generated_at INTEGER DEFAULT 0,
        hidden_cost_paid_at INTEGER DEFAULT 0,
        FOREIGN KEY (country_id) REFERENCES countries(id)
    )
    """)

    # ─── الدول المكتشفة (من تجسس ناجح) ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS discovered_countries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attacker_country_id INTEGER NOT NULL,
        target_country_id INTEGER NOT NULL,
        discovered_at INTEGER DEFAULT (strftime('%s','now')),
        expires_at INTEGER,
        UNIQUE(attacker_country_id, target_country_id)
    )
    """)

    # ─── تجميد الدولة ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS country_freeze (
        country_id INTEGER PRIMARY KEY,
        frozen_until INTEGER NOT NULL,
        reason TEXT DEFAULT 'transfer',
        FOREIGN KEY (country_id) REFERENCES countries(id)
    )
    """)

    # ─── فهارس ───
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_country_battles_status ON country_battles(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_country_battles_attacker ON country_battles(attacker_country_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_country_battles_defender ON country_battles(defender_country_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_supporters_battle ON battle_supporters(battle_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_cards_user ON user_cards(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_discovered_attacker ON discovered_countries(attacker_country_id)")

    conn.commit()
    _seed_cards(conn)


def _seed_cards(conn):
    try:
        cursor = conn.cursor()
        cards = [
        ("speed_march",    "زحف سريع",          "⚡",  "time",    "reduce_travel",  600,  "تقلل وقت السفر بـ 10 دقائق",              300,  1),
        ("delay_enemy",    "تأخير العدو",        "⏳",  "time",    "delay_travel",   600,  "تؤخر هجوم العدو بـ 10 دقائق",             400,  1),
        ("instant_march",  "زحف فوري",           "🚀",  "time",    "reduce_travel",  1200, "تقلل وقت السفر بـ 20 دقيقة",              700,  1),
        ("power_boost",    "تعزيز القوة",        "💪",  "combat",  "attack_boost",   0.25, "تزيد قوة الهجوم 25%",                     500,  1),
        ("iron_shield",    "درع حديدي",          "🛡",  "combat",  "defense_boost",  0.30, "تزيد الدفاع 30%",                         500,  1),
        ("berserker_rage", "غضب المحارب",        "🔥",  "combat",  "hp_boost",       0.20, "تزيد نقاط الحياة 20%",                    400,  1),
        ("double_strike",  "ضربة مزدوجة",        "⚔️", "combat",  "attack_boost",   0.50, "تزيد الهجوم 50% لمعركة واحدة",            900,  1),
        ("spy_boost",      "تعزيز الجواسيس",     "🕵️","spy",     "spy_level_boost", 2,   "ترفع مستوى الجواسيس مؤقتاً",              350,  1),
        ("intel_reveal",   "كشف المعلومات",      "📡",  "spy",     "reveal_intel",   1,    "تكشف معلومات دقيقة عن العدو",             600,  1),
        ("counter_spy",    "مضاد التجسس",        "🛡️","spy",     "counter_boost",   2,   "يرفع مستوى مضاد التجسس",                  300,  1),
        ("fake_attack",    "هجوم وهمي",          "🎭",  "special", "fake_attack",    1,    "يبدو كهجوم حقيقي لكن بدون ضرر",           800,  1),
        ("sudden_attack",  "هجوم مباغت",         "💥",  "special", "sudden_attack",  1,    "وصول فوري لكن بقوة أقل 30%",              1000, 1),
        ("sabotage",       "تخريب",              "🧨",  "special", "sabotage",       0.20, "يقلل قوة العدو 20% قبل المعركة",          1200, 1),
        ("satellite",      "قمر صناعي",          "🛰️","special", "satellite",       1,   "يكشف الجيش الحقيقي ويقلل التمويه",        1500, 1),
        ("building_raid",  "غارة على المباني",   "🏚️","special", "building_raid",   1,   "تستهدف المباني بدلاً من الجنود",           700,  1),
        ("reveal_hidden",  "كشف المخفي",         "🔍",  "spy",     "reveal_hidden",  1,    "يكشف الدول المخفية ويضيفها لقائمة أهدافك", 800, 1),
        ]
        cursor.executemany("""
            INSERT OR IGNORE INTO cards
            (name, name_ar, emoji, category, effect_type, effect_value, description_ar, price, max_uses)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, cards)
        conn.commit()
    except Exception as e:
        print(f"[advanced_war] تجاهل seed: {e}")
