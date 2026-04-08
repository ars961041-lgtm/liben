from ..connection import get_db_conn
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME


def create_progression_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─── تعريف الإنجازات ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        name_ar TEXT NOT NULL,
        emoji TEXT DEFAULT '🏅',
        category TEXT NOT NULL,
        condition_type TEXT NOT NULL,
        condition_value INTEGER DEFAULT 1,
        reward_conis REAL DEFAULT 0,
        reward_card_name TEXT,
        reward_reputation INTEGER DEFAULT 0,
        description_ar TEXT,
        is_hidden INTEGER DEFAULT 0
    )
    """)

    # ─── إنجازات المستخدمين ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(user_id),
        achievement_id INTEGER NOT NULL,
        unlocked_at INTEGER DEFAULT (strftime('%s','now')),
        UNIQUE(user_id, achievement_id),
        FOREIGN KEY (achievement_id) REFERENCES achievements(id)
    )
    """)

    # ─── المواسم ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS seasons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        started_at INTEGER NOT NULL,
        ends_at INTEGER NOT NULL,
        status TEXT DEFAULT 'active',
        rewards_distributed INTEGER DEFAULT 0
    )
    """)

    # ─── سجل المواسم ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS season_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        season_id INTEGER NOT NULL REFERENCES seasons(id),
        category TEXT NOT NULL,
        rank INTEGER NOT NULL,
        user_id INTEGER REFERENCES users(user_id),
        country_id INTEGER REFERENCES countries(id),
        alliance_id INTEGER,
        score REAL DEFAULT 0,
        reward_given TEXT,
        title_awarded TEXT,
        created_at INTEGER DEFAULT (strftime('%s','now'))
    )
    """)

    # ─── ألقاب المواسم ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS season_titles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(user_id),
        season_id INTEGER NOT NULL REFERENCES seasons(id),
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        rank INTEGER NOT NULL,
        awarded_at INTEGER DEFAULT (strftime('%s','now')),
        UNIQUE(user_id, season_id, category)
    )
    """)

    # ─── نقاط التأثير والنفوذ ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS country_influence (
        country_id INTEGER PRIMARY KEY,
        influence_points INTEGER DEFAULT 0,
        income_bonus_pct REAL DEFAULT 0,
        war_advantage_pct REAL DEFAULT 0,
        last_updated INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (country_id) REFERENCES countries(id)
    )
    """)

    # ─── الأحداث العالمية ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS global_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        name_ar TEXT NOT NULL,
        emoji TEXT DEFAULT '🌍',
        event_type TEXT NOT NULL,
        effect_key TEXT NOT NULL,
        effect_value REAL DEFAULT 0,
        duration_hours INTEGER DEFAULT 24,
        started_at INTEGER,
        ends_at INTEGER,
        status TEXT DEFAULT 'pending',
        description_ar TEXT
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_achievements ON user_achievements(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_seasons_status ON seasons(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_country_influence ON country_influence(country_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_global_events_status ON global_events(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_season_titles_user ON season_titles(user_id)")

    conn.commit()
    _seed_achievements(conn)
    _seed_season_constants(conn)


def _seed_achievements(conn):
    cursor = conn.cursor()
    achievements = [
        # ─── معارك ───
        ("first_battle",    "أول معركة",        "⚔️", "battle",  "battles_won",    1,   100,  None,           5,  "فز بأول معركة"),
        ("warrior_5",       "محارب",             "🗡", "battle",  "battles_won",    5,   300,  None,           10, "فز بـ 5 معارك"),
        ("conqueror_20",    "فاتح",              "🏆", "battle",  "battles_won",    20,  1000, "power_boost",  20, "فز بـ 20 معركة"),
        ("defender",        "المدافع الصامد",    "🛡", "battle",  "battles_defended",5,  300,  "iron_shield",  10, "دافع عن دولتك 5 مرات"),
        ("no_retreat",      "لا تراجع",          "💪", "battle",  "no_retreat_wins",10,  500,  None,           15, "فز بـ 10 معارك دون انسحاب"),

        # ─── تجسس ───
        ("first_spy",       "أول تجسس",          "🕵️","spy",    "spy_success",    1,   50,   None,           3,  "نجح أول تجسس"),
        ("spy_master",      "سيد الجواسيس",      "🔍", "spy",    "spy_success",    20,  500,  "spy_boost",    15, "نجح 20 عملية تجسس"),
        ("assassin_ace",    "القاتل المحترف",    "☠️", "spy",    "assassinations", 5,   400,  None,           10, "نفّذ 5 عمليات اغتيال"),

        # ─── دعم ───
        ("first_support",   "أول دعم",           "🤝", "support","battles_helped", 1,   50,   None,           5,  "ساعد في أول معركة"),
        ("loyal_ally",      "الحليف الوفي",      "🏅", "support","battles_helped", 10,  400,  None,           20, "ساعد في 10 معارك"),
        ("top_supporter",   "أفضل داعم",         "🌟", "support","battles_helped", 30,  1000, "berserker_rage",30,"ساعد في 30 معركة"),

        # ─── اقتصاد ───
        ("rich_1k",         "ثري",               "💰", "economy","balance",        1000, 0,   None,           5,  f"اجمع 1000 {CURRENCY_ARABIC_NAME}"),
        ("rich_10k",        "مليونير",           "💎", "economy","balance",        10000,500, None,           10, f"اجمع 10,000 {CURRENCY_ARABIC_NAME}"),
        ("investor",        "المستثمر",          "📈", "economy","investments",    10,  200,  None,           5,  "استثمر 10 مرات"),

        # ─── تحالف ───
        ("alliance_founder","مؤسس التحالف",      "🏰", "alliance","alliances_created",1,200, None,           10, "أنشئ تحالفاً"),
        ("alliance_veteran","قديم التحالف",      "⭐", "alliance","alliance_days",  30,  300,  None,           15, "ابقَ في تحالف 30 يوماً"),

        # ─── نفوذ ───
        ("influencer_100",  "مؤثر",              "🌍", "influence","influence_points",100,300,None,           10, "اجمع 100 نقطة نفوذ"),
        ("influencer_500",  "قوة إقليمية",       "🌐", "influence","influence_points",500,1000,"satellite",  25, "اجمع 500 نقطة نفوذ"),
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO achievements
        (name, name_ar, emoji, category, condition_type, condition_value,
         reward_conis, reward_card_name, reward_reputation, description_ar)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, achievements)
    conn.commit()

    # ─── إنجازات مخفية ───
    hidden = [
        ("ghost_spy",    "الشبح",           "👻", "spy",     "spy_success",    50,  2000, "satellite",    50, "نجح 50 عملية تجسس"),
        ("iron_will",    "إرادة حديدية",    "🔩", "battle",  "battles_won",    50,  3000, "double_strike", 60, "فز بـ 50 معركة"),
        ("lone_wolf",    "الذئب المنفرد",   "🐺", "battle",  "no_retreat_wins",10,  800,  None,            20, "فز بـ 10 معارك بدون دعم"),
        ("economist",    "الاقتصادي",       "🏦", "economy", "balance",        50000,2000, None,           30, f"اجمع 50,000 {CURRENCY_ARABIC_NAME}"),
        ("spy_betrayal", "الخيانة المزدوجة","🎭", "spy",     "detected",       3,   0,    None,           -10, "اكتُشف 3 جواسيس"),
        ("influencer_1k","قوة عظمى",        "🌟", "influence","influence_points",1000,5000,"satellite",   50, "اجمع 1000 نقطة نفوذ"),
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO achievements
        (name, name_ar, emoji, category, condition_type, condition_value,
         reward_conis, reward_card_name, reward_reputation, description_ar, is_hidden)
        VALUES (?,?,?,?,?,?,?,?,?,?,1)
    """, hidden)
    conn.commit()


def _seed_season_constants(conn):
    """يُضيف ثوابت المواسم والنفوذ — يتجاهل إذا bot_constants غير موجود"""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='bot_constants'"
        )
        if not cursor.fetchone():
            return
        constants = [
        ("season_duration_days",  "30",  "مدة الموسم بالأيام"),
        ("season_top_rewards",    "3",   "عدد الفائزين بمكافآت الموسم"),
        ("season_reward_conis_1", "5000",f"مكافأة المركز الأول ({CURRENCY_ARABIC_NAME})"),
        ("season_reward_conis_2", "3000",f"مكافأة المركز الثاني ({CURRENCY_ARABIC_NAME})"),
        ("season_reward_conis_3", "1500",f"مكافأة المركز الثالث ({CURRENCY_ARABIC_NAME})"),
        ("influence_per_win",     "10",  "نقاط نفوذ لكل انتصار"),
        ("influence_per_defense", "5",   "نقاط نفوذ لكل دفاع ناجح"),
        ("influence_income_rate", "0.08","معدل الدخل اللوغاريتمي"),
        ("influence_war_rate",    "0.05","معدل الحرب اللوغاريتمي"),
        ("influence_income_cap",  "0.40","الحد الأقصى لمكافأة الدخل من النفوذ"),
        ("influence_war_cap",     "0.20","الحد الأقصى لميزة الحرب من النفوذ"),
        ("maintenance_debt_block","200", "حد الدين الذي يمنع الهجوم"),
        ("event_check_interval",  "3600","فترة فحص الأحداث العالمية (ثانية)"),
        ("late_game_upgrade_cost","10000",f"تكلفة الترقية المتأخرة ({CURRENCY_ARABIC_NAME})"),
        ("economy_sink_rate",     "0.05","نسبة الضريبة على الأرصدة الكبيرة"),
        ]
        cursor.executemany("""
            INSERT OR IGNORE INTO bot_constants (name, value, description)
            VALUES (?, ?, ?)
        """, constants)
        conn.commit()
    except Exception as e:
        print(f"[progression] تجاهل seed constants: {e}")
