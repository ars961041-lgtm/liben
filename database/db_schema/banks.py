from ..connection import get_db_conn

def create_banks_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # TABLE: user_accounts
    # PURPOSE: Each player's bank account. Created when the user
    #          runs "إنشاء حساب بنكي". Holds their current balance.
    #
    # COLUMNS:
    #   id         — Internal autoincrement PK.
    #   user_id    — References users.user_id. One account per user.
    #   balance    — Current balance. Default set by bot_constant
    #                'initial_balance' (fallback: 1000).
    #   created_at — Unix timestamp when the account was opened.
    # ─────────────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_accounts (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL UNIQUE,
        balance    REAL    DEFAULT 1000,
        created_at INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    ''')

    # ─────────────────────────────────────────────────────────────
    # TABLE: loans
    # PURPOSE: Tracks active and historical loans issued to players.
    #          Supports partial repayment and overdue penalties.
    #
    # COLUMNS:
    #   id         — Internal autoincrement PK.
    #   user_id    — The borrower.
    #   amount     — Original loan amount granted.
    #   due_date   — Unix timestamp of the repayment deadline.
    #   repaid     — Amount already repaid so far.
    #   status     — 'active', 'overdue', or 'repaid'.
    #   created_at — When the loan was issued.
    # ─────────────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS loans (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER,
        amount     REAL    NOT NULL,
        due_date   INTEGER,
        repaid     REAL    DEFAULT 0,
        status     TEXT    DEFAULT 'active',
        created_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    ''')

    # ─────────────────────────────────────────────────────────────
    # TABLE: bank_cooldowns
    # PURPOSE: Prevents spamming bank commands (salary, tasks, etc.)
    #          by recording the last time each action was used.
    #
    # COLUMNS:
    #   user_id   — References users.user_id.
    #   type      — Action name (e.g. 'salary', 'daily', 'task').
    #   last_used — Unix timestamp of the last use. Compared against
    #               the cooldown duration to decide if allowed.
    #
    # PRIMARY KEY: (user_id, type) — one entry per user per action.
    # ─────────────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bank_cooldowns (
        user_id   INTEGER NOT NULL,
        type      TEXT    NOT NULL,
        last_used INTEGER,
        PRIMARY KEY (user_id, type),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    ''')

    # ─────────────────────────────────────────────────────────────
    # TABLE: bank_transfers
    # PURPOSE: Immutable log of every currency transfer between two
    #          players. Used for history, auditing, and leaderboards.
    #
    # COLUMNS:
    #   id           — Internal autoincrement PK.
    #   from_user_id — The sender.
    #   to_user_id   — The recipient.
    #   amount       — Amount transferred (before fees).
    #   fee          — Fee deducted from the sender on top of amount.
    #   created_at   — Unix timestamp of the transfer.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bank_transfers (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user_id INTEGER NOT NULL,
        to_user_id   INTEGER NOT NULL,
        amount       REAL    NOT NULL,
        fee          REAL    DEFAULT 0,
        created_at   INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (from_user_id) REFERENCES users(user_id),
        FOREIGN KEY (to_user_id)   REFERENCES users(user_id)
    )
    """)

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_accounts_user    ON user_accounts(user_id);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_accounts_balance ON user_accounts(balance DESC);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_bank_transfers_from   ON bank_transfers(from_user_id);')

    conn.commit()
