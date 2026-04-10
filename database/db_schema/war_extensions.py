from ..connection import get_db_conn


def create_war_extension_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # TABLE: spy_agents
    # PURPOSE: Individual spy agents deployed by a country, each
    #          with their own specialization, level, and experience.
    #          More advanced than spy_units — represents named agents
    #          that can be leveled up and sent on specific missions.
    #
    # COLUMNS:
    #   id          — Internal autoincrement PK.
    #   country_id  — Which country owns this agent.
    #   agent_type  — Specialization: 'scout', 'saboteur', or 'assassin'.
    #   level       — Agent's current level. Affects mission success rate.
    #   experience  — XP accumulated. Reaches a threshold to level up.
    #   status      — 'active', 'deployed', or 'captured'.
    #   deployed_at — Unix timestamp when the agent was last deployed.
    #                 0 = not currently deployed.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS spy_agents (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id  INTEGER NOT NULL,
        agent_type  TEXT    NOT NULL DEFAULT 'scout',
        level       INTEGER DEFAULT 1,
        experience  INTEGER DEFAULT 0,
        status      TEXT    DEFAULT 'active',
        deployed_at INTEGER DEFAULT 0,
        FOREIGN KEY (country_id) REFERENCES countries(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_support_stats
    # PURPOSE: Tracks how much each player has contributed to their
    #          alliance through battle support. Used for leaderboards
    #          and the alliance support ranking command.
    #
    # COLUMNS:
    #   id                      — Internal autoincrement PK.
    #   alliance_id             — Which alliance.
    #   user_id                 — Which member.
    #   battles_supported       — Total battles this member helped in.
    #   total_power_contributed — Total power sent as support across all battles.
    #   resource_sent           — Total currency sent as resource support.
    #   last_support_at         — Unix timestamp of the most recent support action.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_support_stats (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        alliance_id             INTEGER NOT NULL,
        user_id                 INTEGER NOT NULL,
        battles_supported       INTEGER DEFAULT 0,
        total_power_contributed REAL    DEFAULT 0,
        resource_sent           REAL    DEFAULT 0,
        last_support_at         INTEGER DEFAULT 0,
        UNIQUE(alliance_id, user_id),
        FOREIGN KEY (alliance_id) REFERENCES alliances(id),
        FOREIGN KEY (user_id)     REFERENCES users(user_id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: army_maintenance
    # PURPOSE: Tracks the ongoing maintenance cost of a country's
    #          army and any unpaid debt. High debt weakens the army
    #          and eventually blocks the country from attacking.
    #
    # COLUMNS:
    #   country_id   — Primary key. References countries.id.
    #   hourly_cost  — Current hourly maintenance bill based on army size.
    #                  Recalculated when troops/equipment change.
    #   last_paid_at — Unix timestamp when maintenance was last deducted.
    #   debt         — Unpaid maintenance debt. Accumulates if the player
    #                  can't afford the hourly cost.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS army_maintenance (
        country_id   INTEGER PRIMARY KEY,
        hourly_cost  REAL    DEFAULT 0,
        last_paid_at INTEGER DEFAULT (strftime('%s','now')),
        debt         REAL    DEFAULT 0,
        FOREIGN KEY (country_id) REFERENCES countries(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: exploration_log
    # PURPOSE: Records the results of exploration missions.
    #          Exploration is how players discover new countries to
    #          attack. Each mission costs currency and may or may not
    #          find a new target.
    #
    # COLUMNS:
    #   id                    — Internal autoincrement PK.
    #   country_id            — The country that sent the exploration.
    #   result                — 'found', 'nothing', or 'failed'.
    #   discovered_country_id — The country discovered. NULL if nothing found.
    #   cost                  — Currency spent on this exploration.
    #   created_at            — When the exploration was run.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exploration_log (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id            INTEGER NOT NULL,
        result                TEXT    NOT NULL,
        discovered_country_id INTEGER,
        cost                  REAL    DEFAULT 0,
        created_at            INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (country_id)            REFERENCES countries(id),
        FOREIGN KEY (discovered_country_id) REFERENCES countries(id)
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
