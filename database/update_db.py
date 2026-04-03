"""
تشغيل بعد create_all_tables().
يضيف أي أعمدة أو جداول مفقودة في قواعد البيانات القديمة.
قاعدة البيانات الجديدة لا تحتاج هذا — الـ schema صحيح من البداية.
"""
from database.connection import get_db_conn


def _col_exists(cursor, table: str, col: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == col for row in cursor.fetchall())


def _table_exists(cursor, table: str) -> bool:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None


def update_database():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ── users: إضافة city_id و country_id إذا لم تكن موجودة ──
    if _table_exists(cursor, "users"):
        if not _col_exists(cursor, "users", "city_id"):
            cursor.execute("ALTER TABLE users ADD COLUMN city_id INTEGER DEFAULT NULL")
        if not _col_exists(cursor, "users", "country_id"):
            cursor.execute("ALTER TABLE users ADD COLUMN country_id INTEGER DEFAULT NULL")

    # ── achievements: إضافة is_hidden إذا لم تكن موجودة ──
    if _table_exists(cursor, "achievements"):
        if not _col_exists(cursor, "achievements", "is_hidden"):
            cursor.execute("ALTER TABLE achievements ADD COLUMN is_hidden INTEGER DEFAULT 0")

    # ── country_transfers: إنشاء الجدول إذا لم يكن موجوداً ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS country_transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_id INTEGER NOT NULL,
            from_user_id INTEGER NOT NULL,
            to_user_id INTEGER NOT NULL,
            penalty_applied INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            transferred_at INTEGER DEFAULT (strftime('%s','now')),
            expires_at INTEGER NOT NULL
        )
    """)

    # ── bank_transfers: جدول سجل التحويلات ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bank_transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user_id INTEGER NOT NULL,
            to_user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            fee REAL DEFAULT 0,
            created_at INTEGER DEFAULT (strftime('%s','now'))
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_bank_transfers_from ON bank_transfers(from_user_id)"
    )

    # ── global_events: إضافة description_ar إذا لم تكن موجودة ──
    if _table_exists(cursor, "global_events"):
        if not _col_exists(cursor, "global_events", "description_ar"):
            cursor.execute(
                "ALTER TABLE global_events ADD COLUMN description_ar TEXT DEFAULT ''"
            )

    # ── season_titles: إضافة awarded_at إذا لم تكن موجودة ──
    if _table_exists(cursor, "season_titles"):
        if not _col_exists(cursor, "season_titles", "awarded_at"):
            cursor.execute(
                "ALTER TABLE season_titles ADD COLUMN awarded_at INTEGER "
                "DEFAULT (strftime('%s','now'))"
            )

    # ── bot_constants: إضافة ثوابت مفقودة ──
    if _table_exists(cursor, "bot_constants"):
        missing_constants = [
            ("initial_balance",      "1000",  "رصيد الحساب البنكي الافتراضي"),
            ("transfer_fee_pct",     "0.05",  "رسوم التحويل البنكي (نسبة مئوية)"),
            ("transfer_min_amount",  "10",    "الحد الأدنى للتحويل البنكي"),
            ("transfer_max_amount",  "100000","الحد الأقصى للتحويل البنكي"),
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO bot_constants (name, value, description) VALUES (?,?,?)",
            missing_constants
        )

    conn.commit()
    print("✅ تم تحديث قاعدة البيانات بنجاح.")
