from ..connection import get_db_conn
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME


def create_progression_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # TABLE: achievements
    # PURPOSE: Master catalog of all achievements players can unlock.
    #          Seeded at startup. Defines the condition, reward, and
    #          display info for each achievement.
    #
    # COLUMNS:
    #   id               — Internal autoincrement PK.
    #   name             — Unique English key (e.g. 'first_battle').
    #   name_ar          — Arabic display name shown to players.
    #   emoji            — Display emoji.
    #   category         — Group: 'battle', 'spy', 'economy', 'alliance', 'influence'.
    #   condition_type   — What must be done (e.g. 'battles_won', 'balance').
    #   condition_value  — The threshold to reach (e.g. 5 wins, 1000 balance).
    #   reward_conis     — Currency reward paid when unlocked.
    #   reward_card_name — Card given on unlock. NULL if no card reward.
    #   reward_reputation— Reputation points added on unlock.
    #   description_ar   — Arabic description shown to the player.
    #   is_hidden        — 1 = hidden achievement (not shown until unlocked).
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS achievements (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        name             TEXT    UNIQUE NOT NULL,
        name_ar          TEXT    NOT NULL,
        emoji            TEXT    DEFAULT '🏅',
        category         TEXT    NOT NULL,
        condition_type   TEXT    NOT NULL,
        condition_value  INTEGER DEFAULT 1,
        reward_conis     REAL    DEFAULT 0,
        reward_card_name TEXT,
        reward_reputation INTEGER DEFAULT 0,
        description_ar   TEXT,
        is_hidden        INTEGER DEFAULT 0
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: user_achievements
    # PURPOSE: Achievements that a player has already unlocked.
    #          One row per (user, achievement). Checked on every
    #          relevant game action to see if a new one was earned.
    #
    # COLUMNS:
    #   id             — Internal autoincrement PK.
    #   user_id        — The player who unlocked it.
    #   achievement_id — References achievements.id.
    #   unlocked_at    — Unix timestamp when the achievement was unlocked.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_achievements (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id        INTEGER NOT NULL REFERENCES users(user_id),
        achievement_id INTEGER NOT NULL,
        unlocked_at    INTEGER DEFAULT (strftime('%s','now')),
        UNIQUE(user_id, achievement_id),
        FOREIGN KEY (achievement_id) REFERENCES achievements(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: seasons
    # PURPOSE: Time-limited competitive seasons. Players compete for
    #          rankings across battles, alliances, and spy categories.
    #          Rewards are distributed when the season ends.
    #
    # COLUMNS:
    #   id                  — Internal autoincrement PK.
    #   name                — Season name (e.g. 'موسم 1').
    #   started_at          — Unix timestamp when the season began.
    #   ends_at             — Unix timestamp when the season ends.
    #   status              — 'active' or 'ended'.
    #   rewards_distributed — 1 = rewards have been sent to winners.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS seasons (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        name                TEXT    NOT NULL,
        started_at          INTEGER NOT NULL,
        ends_at             INTEGER NOT NULL,
        status              TEXT    DEFAULT 'active',
        rewards_distributed INTEGER DEFAULT 0
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: season_history
    # PURPOSE: Final rankings for each category at the end of a season.
    #          Written once when the season ends. Used to display
    #          historical leaderboards and award titles.
    #
    # COLUMNS:
    #   id           — Internal autoincrement PK.
    #   season_id    — Which season.
    #   category     — Ranking category: 'battles', 'alliances', 'spies'.
    #   rank         — Position (1 = first place).
    #   user_id      — The ranked player. NULL for alliance rankings.
    #   country_id   — The ranked country. NULL for spy rankings.
    #   alliance_id  — The ranked alliance. NULL for non-alliance categories.
    #   score        — The score that determined this rank.
    #   reward_given — Description of the reward sent to this player.
    #   title_awarded— Title granted to this player.
    #   created_at   — When this record was saved.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS season_history (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        season_id     INTEGER NOT NULL,
        category      TEXT    NOT NULL,
        rank          INTEGER NOT NULL,
        user_id       INTEGER,
        country_id    INTEGER,
        alliance_id   INTEGER,
        score         REAL    DEFAULT 0,
        reward_given  TEXT,
        title_awarded TEXT,
        created_at    INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (season_id)   REFERENCES seasons(id),
        FOREIGN KEY (user_id)     REFERENCES users(user_id),
        FOREIGN KEY (country_id)  REFERENCES countries(id),
        FOREIGN KEY (alliance_id) REFERENCES alliances(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: season_titles
    # PURPOSE: Titles earned by players at the end of seasons.
    #          Displayed on the player's profile permanently.
    #          One title per (user, season, category).
    #
    # COLUMNS:
    #   id         — Internal autoincrement PK.
    #   user_id    — The player who earned the title.
    #   season_id  — Which season it was earned in.
    #   title      — The title text (e.g. '👑 بطل الموسم').
    #   category   — Which category they won (battles/alliances/spies).
    #   rank       — Their rank in that category (1, 2, or 3).
    #   awarded_at — When the title was granted.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS season_titles (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL REFERENCES users(user_id),
        season_id  INTEGER NOT NULL REFERENCES seasons(id),
        title      TEXT    NOT NULL,
        category   TEXT    NOT NULL,
        rank       INTEGER NOT NULL,
        awarded_at INTEGER DEFAULT (strftime('%s','now')),
        UNIQUE(user_id, season_id, category)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: country_influence
    # PURPOSE: Tracks a country's influence points, which provide
    #          passive income and combat bonuses. Influence grows
    #          by winning battles and defending successfully.
    #
    # COLUMNS:
    #   country_id        — Primary key. References countries.id.
    #   influence_points  — Total influence accumulated.
    #   income_bonus_pct  — Passive income bonus derived from influence (0.0–0.40).
    #   war_advantage_pct — Combat advantage derived from influence (0.0–0.20).
    #   last_updated      — When these values were last recalculated.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS country_influence (
        country_id        INTEGER PRIMARY KEY,
        influence_points  INTEGER DEFAULT 0,
        income_bonus_pct  REAL    DEFAULT 0,
        war_advantage_pct REAL    DEFAULT 0,
        last_updated      INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (country_id) REFERENCES countries(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: global_events
    # PURPOSE: Time-limited world events that affect all players
    #          simultaneously (e.g. double income, attack boost).
    #          Triggered randomly by the interval scheduler.
    #          Players can view the active event with "الأحداث".
    #
    # COLUMNS:
    #   id             — Internal autoincrement PK.
    #   name           — English key.
    #   name_ar        — Arabic display name.
    #   emoji          — Display emoji.
    #   event_type     — Category of event (e.g. 'economy', 'war', 'spy').
    #   effect_key     — Which game mechanic is affected (e.g. 'salary_bonus').
    #   effect_value   — Magnitude of the effect (e.g. 0.20 = +20%).
    #   duration_hours — How long the event lasts in hours.
    #   started_at     — Unix timestamp when the event started. NULL if pending.
    #   ends_at        — Unix timestamp when the event ends.
    #   status         — 'pending', 'active', or 'ended'.
    #   description_ar — Arabic description shown to players.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS global_events (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        name           TEXT    NOT NULL,
        name_ar        TEXT    NOT NULL,
        emoji          TEXT    DEFAULT '🌍',
        event_type     TEXT    NOT NULL,
        effect_key     TEXT    NOT NULL,
        effect_value   REAL    DEFAULT 0,
        duration_hours INTEGER DEFAULT 24,
        started_at     INTEGER,
        ends_at        INTEGER,
        status         TEXT    DEFAULT 'pending',
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
        ("first_battle",    "أول معركة",        "⚔️", "battle",  "battles_won",    1,   100,  None,           5,  "فز بأول معركة"),
        ("warrior_5",       "محارب",             "🗡", "battle",  "battles_won",    5,   300,  None,           10, "فز بـ 5 معارك"),
        ("conqueror_20",    "فاتح",              "🏆", "battle",  "battles_won",    20,  1000, "power_boost",  20, "فز بـ 20 معركة"),
        ("defender",        "المدافع الصامد",    "🛡", "battle",  "battles_defended",5,  300,  "iron_shield",  10, "دافع عن دولتك 5 مرات"),
        ("no_retreat",      "لا تراجع",          "💪", "battle",  "no_retreat_wins",10,  500,  None,           15, "فز بـ 10 معارك دون انسحاب"),
        ("first_spy",       "أول تجسس",          "🕵️","spy",    "spy_success",    1,   50,   None,           3,  "نجح أول تجسس"),
        ("spy_master",      "سيد الجواسيس",      "🔍", "spy",    "spy_success",    20,  500,  "spy_boost",    15, "نجح 20 عملية تجسس"),
        ("assassin_ace",    "القاتل المحترف",    "☠️", "spy",    "assassinations", 5,   400,  None,           10, "نفّذ 5 عمليات اغتيال"),
        ("first_support",   "أول دعم",           "🤝", "support","battles_helped", 1,   50,   None,           5,  "ساعد في أول معركة"),
        ("loyal_ally",      "الحليف الوفي",      "🏅", "support","battles_helped", 10,  400,  None,           20, "ساعد في 10 معارك"),
        ("top_supporter",   "أفضل داعم",         "🌟", "support","battles_helped", 30,  1000, "berserker_rage",30,"ساعد في 30 معركة"),
        ("rich_1k",         "ثري",               "💰", "economy","balance",        1000, 0,   None,           5,  f"اجمع 1000 {CURRENCY_ARABIC_NAME}"),
        ("rich_10k",        "مليونير",           "💎", "economy","balance",        10000,500, None,           10, f"اجمع 10,000 {CURRENCY_ARABIC_NAME}"),
        ("investor",        "المستثمر",          "📈", "economy","investments",    10,  200,  None,           5,  "استثمر 10 مرات"),
        ("alliance_founder","مؤسس التحالف",      "🏰", "alliance","alliances_created",1,200, None,           10, "أنشئ تحالفاً"),
        ("alliance_veteran","قديم التحالف",      "⭐", "alliance","alliance_days",  30,  300,  None,           15, "ابقَ في تحالف 30 يوماً"),
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
