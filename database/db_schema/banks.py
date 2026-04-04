from ..connection import get_db_conn

def create_banks_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # 🧾 حسابات المستخدمين
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        balance REAL DEFAULT 1000,
        last_daily_claim INTEGER DEFAULT 0,
        created_at INTEGER
    );
    ''')

    # ⏱️ نظام التوقيت (Cooldowns)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_cooldowns (
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        last_time INTEGER,
        PRIMARY KEY (user_id, action)
    );
    ''')
    
    # ⏱️ نظام التوقيت (Cooldowns)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL NOT NULL,
        interest REAL DEFAULT 0.15,   -- 15% افتراضياً
        due_date INTEGER,             -- توقيت السداد بالثواني
        repaid REAL DEFAULT 0,        -- المبلغ الذي تم سداده
        status TEXT DEFAULT 'active', -- active / repaid / overdue
        created_at INTEGER DEFAULT (strftime('%s','now'))
    );
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bank_cooldowns (
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        last_used INTEGER,
        PRIMARY KEY (user_id, type)
    );
    ''')
    
    # 📊 إحصائيات مالية مستقبلية (اختياري لكنه مهم)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bank_stats (
        name TEXT PRIMARY KEY,
        value REAL DEFAULT 0
    );
    ''')

    # 💸 سجل التحويلات البنكية
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bank_transfers (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user_id INTEGER NOT NULL,
        to_user_id   INTEGER NOT NULL,
        amount       REAL    NOT NULL,
        fee          REAL    DEFAULT 0,
        created_at   INTEGER DEFAULT (strftime('%s','now'))
    )
    """)

    # 🔎 Indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_accounts_user ON user_accounts(user_id);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_accounts_balance ON user_accounts(balance DESC);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_bank_transfers_from ON bank_transfers(from_user_id);')

    conn.commit()