from ..connection import get_db_conn

def create_banks_table():
    conn = get_db_conn()
    cursor = conn.cursor()

    # إنشاء جدول الحسابات البنكية
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        balance INTEGER DEFAULT 1000,
        created_at INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_cooldowns (
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        last_time INTEGER,
        PRIMARY KEY (user_id, action)
    );
    ''')
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_user_accounts_user
    ON user_accounts(user_id);
    ''')
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_user_accounts_balance
    ON user_accounts(balance DESC);
    ''')
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_cooldowns_user
    ON user_cooldowns(user_id);
    ''')

    conn.commit()