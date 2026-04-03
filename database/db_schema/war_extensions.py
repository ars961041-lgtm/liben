from ..connection import get_db_conn


def create_war_extension_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─── عملاء التجسس المتقدمون ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS spy_agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL,
        agent_type TEXT NOT NULL DEFAULT 'scout',
        level INTEGER DEFAULT 1,
        experience INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active',
        deployed_at INTEGER DEFAULT 0,
        FOREIGN KEY (country_id) REFERENCES countries(id)
    )
    """)

    # ─── إحصائيات دعم التحالف ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_support_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alliance_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        battles_supported INTEGER DEFAULT 0,
        total_power_contributed REAL DEFAULT 0,
        resource_sent REAL DEFAULT 0,
        last_support_at INTEGER DEFAULT 0,
        FOREIGN KEY (alliance_id) REFERENCES alliances(id),
        UNIQUE(alliance_id, user_id)
    )
    """)

    # ─── صيانة الجيش ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS army_maintenance (
        country_id INTEGER PRIMARY KEY,
        hourly_cost REAL DEFAULT 0,
        last_paid_at INTEGER DEFAULT (strftime('%s','now')),
        debt REAL DEFAULT 0,
        FOREIGN KEY (country_id) REFERENCES countries(id)
    )
    """)

    # ─── نتائج الاستكشاف ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exploration_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL,
        result TEXT NOT NULL,
        discovered_country_id INTEGER,
        cost REAL DEFAULT 0,
        created_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (country_id) REFERENCES countries(id)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_spy_agents_country ON spy_agents(country_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alliance_support_stats ON alliance_support_stats(alliance_id, user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_army_maintenance ON army_maintenance(country_id)")

    conn.commit()
    _seed_extension_constants(conn)


def _seed_extension_constants(conn):
    """يُضيف ثوابت الامتداد لجدول bot_constants — يتجاهل إذا الجدول غير موجود"""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bot_constants'")
        if not cursor.fetchone():
            return
        new_constants = [
        ("scout_cost",           "150",  "تكلفة إرسال كشاف"),
        ("saboteur_cost",        "400",  "تكلفة إرسال مخرب"),
        ("assassin_cost",        "600",  "تكلفة إرسال قاتل"),
        ("exploration_cost",     "200",  "تكلفة الاستكشاف"),
        ("spy_xp_per_mission",   "10",   "XP لكل عملية تجسس"),
        ("spy_level_up_xp",      "100",  "XP المطلوب للترقية"),
        ("maintenance_rate",     "0.01", "نسبة الصيانة من قوة الجيش/ساعة"),
        ("maintenance_grace_h",  "6",    "ساعات السماح قبل تقليل القوة"),
        ("support_atk_mod",      "0.60", "مضاعف قوة دعم المهاجم"),
        ("support_def_mod",      "0.80", "مضاعف قوة دعم المدافع"),
        ("support_res_amount",   "500",  "مبلغ الدعم المالي الافتراضي"),
        ("reputation_accept_threshold", "60", "حد السمعة لقبول الدعم تلقائياً"),
        ]
        cursor.executemany("""
            INSERT OR IGNORE INTO bot_constants (name, value, description)
            VALUES (?, ?, ?)
        """, new_constants)
        conn.commit()
    except Exception as e:
        print(f"[war_extensions] تجاهل seed: {e}")
