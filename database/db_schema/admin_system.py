from ..connection import get_db_conn
from core.config import developers_id
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME


def create_admin_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # TABLE: bot_constants
    # PURPOSE: Key-value store for all runtime-configurable bot
    #          settings. Avoids hardcoding values in code. Admins
    #          can update these without redeploying.
    #
    # COLUMNS:
    #   name        — Unique key (e.g. 'attack_cost', 'initial_balance').
    #                 Acts as the primary key.
    #   value       — The setting's value, always stored as TEXT.
    #                 Cast to int/float at the call site.
    #   description — Human-readable explanation of what this controls.
    #   updated_at  — Unix timestamp of the last change.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_constants (
        name        TEXT PRIMARY KEY,
        value       TEXT NOT NULL,
        description TEXT DEFAULT '',
        updated_at  INTEGER DEFAULT (strftime('%s','now'))
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: bot_developers
    # PURPOSE: List of users with developer-level access to the bot.
    #          Used to gate admin commands and the dev panel.
    #
    # COLUMNS:
    #   id       — Internal autoincrement PK.
    #   user_id  — References users.user_id. The developer's Telegram ID.
    #   role     — 'primary' (full access) or 'secondary' (limited).
    #   added_at — Unix timestamp when this developer was registered.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_developers (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id  INTEGER NOT NULL UNIQUE,
        role     TEXT    DEFAULT 'secondary',
        added_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: global_mutes
    # PURPOSE: Users muted across ALL groups the bot is in.
    #          A global mute overrides any group-level setting.
    #
    # COLUMNS:
    #   id       — Internal autoincrement PK.
    #   user_id  — The globally muted user. Unique — one row per user.
    #   reason   — Why the user was globally muted.
    #   muted_by — The developer/admin who issued the mute.
    #   muted_at — Unix timestamp when the mute was applied.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS global_mutes (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id  INTEGER NOT NULL UNIQUE,
        reason   TEXT    DEFAULT '',
        muted_by INTEGER,
        muted_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (user_id)  REFERENCES users(user_id),
        FOREIGN KEY (muted_by) REFERENCES users(user_id)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_global_mutes ON global_mutes(user_id)")

    conn.commit()
    _seed_defaults(conn)


def _seed_defaults(conn):
    cursor = conn.cursor()

    for dev_id in developers_id:
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (dev_id,)
        )
        cursor.execute("""
            INSERT OR IGNORE INTO bot_developers (user_id, role) VALUES (?, 'primary')
        """, (dev_id,))

    defaults = [
        ("dev_group_id",          "-1003505563946",  "معرف مجموعة المطورين"),
        ("attack_cost",           "500",           f"تكلفة إطلاق هجوم ({CURRENCY_ARABIC_NAME})"),
        ("support_send_cost",     "100",           "تكلفة إرسال طلب دعم"),
        ("card_use_cost",         "50",            "تكلفة استخدام بطاقة في المعركة"),
        ("recovery_minutes",      "30",            "دقائق التعافي بعد المعركة"),
        ("base_heal_time",        "3600",          "ثواني شفاء الجنود المصابين"),
        ("base_repair_time",      "1800",          "ثواني إصلاح المعدات"),
        ("hidden_country_cost",   "200",           "تكلفة إخفاء الدولة يومياً"),
        ("daily_ticket_limit",    "2",             "حد التذاكر اليومي للمستخدم"),
        ("ticket_cooldown_sec",   "10",            "كولداون التذاكر بالثواني"),
        ("max_level_diff",        "3",             "أقصى فارق مستوى مسموح للهجوم"),
        ("fatigue_per_battle",    "0.08",          "نسبة التعب لكل معركة"),
        ("max_loss_pct",          "0.60",          "أقصى نسبة خسارة في المعركة"),
        ("loot_min_pct",          "0.05",          "أدنى نسبة غنائم"),
        ("loot_max_pct",          "0.15",          "أقصى نسبة غنائم"),
        ("travel_time_normal",    "1200",          "وقت السفر العادي (ثانية)"),
        ("travel_time_sudden",    "300",           "وقت الهجوم المباغت (ثانية)"),
        ("country_creation_cost", "100",           "تكلفة إنشاء دولة"),
        ("alliance_creation_cost","500",           "تكلفة إنشاء تحالف"),
        ("bot_name",              "بيلو",          "اسم البوت"),
        ("welcome_msg",           "مرحباً بك في بوت بيلو! 🤖", "رسالة الترحيب"),
        ("spy_cost",              "150",           f"تكلفة عملية التجسس ({CURRENCY_ARABIC_NAME})"),
        ("spy_cooldown_sec",      "120",           "كولداون التجسس على نفس الهدف (ثانية)"),
        ("initial_balance",       "10000",          "رصيد الحساب البنكي الافتراضي"),
        ("transfer_fee_pct",      "0.05",          "رسوم التحويل البنكي (نسبة مئوية)"),
        ("transfer_min_amount",   "10",            "الحد الأدنى للتحويل البنكي"),
        ("transfer_max_amount",   "100000",        "الحد الأقصى للتحويل البنكي"),
        ("max_loan_amount",       "10000",         "الحد الأقصى لمبلغ القرض"),
        ("quotes_interval_minutes", "10",          "فترة إرسال الاقتباسات التلقائية للمجموعات (دقائق)"),
        ("weekly_ranking_reward",   "500",          "مكافأة بطل الأسبوع في المجلة"),
        ("monthly_ranking_reward",  "2000",         "مكافأة بطل الشهر في المجلة"),
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO bot_constants (name, value, description)
        VALUES (?, ?, ?)
    """, defaults)

    conn.commit()
