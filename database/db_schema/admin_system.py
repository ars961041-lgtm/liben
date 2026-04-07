from ..connection import get_db_conn
from core.config import developers_id
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME


def create_admin_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─── ثوابت البوت ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_constants (
        name TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        description TEXT DEFAULT '',
        updated_at INTEGER DEFAULT (strftime('%s','now'))
    )
    """)

    # ─── مطورو البوت ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_developers (
        user_id INTEGER PRIMARY KEY,
        role TEXT DEFAULT 'secondary',
        added_at INTEGER DEFAULT (strftime('%s','now'))
    )
    """)

    # ─── كتم عالمي ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS global_mutes (
        user_id INTEGER PRIMARY KEY,
        reason TEXT DEFAULT '',
        muted_by INTEGER,
        muted_at INTEGER DEFAULT (strftime('%s','now'))
    )
    """)

    # ─── كتم في مجموعة محددة ───
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS group_mutes (
        user_id INTEGER NOT NULL,
        group_id INTEGER NOT NULL,
        reason TEXT DEFAULT '',
        muted_by INTEGER,
        muted_at INTEGER DEFAULT (strftime('%s','now')),
        PRIMARY KEY (user_id, group_id)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_global_mutes ON global_mutes(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_group_mutes ON group_mutes(user_id, group_id)")

    conn.commit()
    _seed_defaults(conn)


def _seed_defaults(conn):
    cursor = conn.cursor()

    # ─── إضافة المطور الأساسي ───
    for dev_id in developers_id:
        cursor.execute("""
            INSERT OR IGNORE INTO bot_developers (user_id, role) VALUES (?, 'primary')
        """, (dev_id,))

    # ─── الثوابت الافتراضية ───
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
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO bot_constants (name, value, description)
        VALUES (?, ?, ?)
    """, defaults)

    conn.commit()
