"""
نظام حوكمة التحالفات — مخطط قاعدة البيانات
Alliance Governance System — Database Schema

Tables:
  alliance_treasury        — الخزينة المشتركة للتحالف
  alliance_treasury_log    — سجل كل المعاملات المالية
  alliance_reputation      — سمعة التحالف العالمية
  alliance_reputation_log  — سجل أحداث السمعة
  alliance_titles          — الألقاب الديناميكية المكتسبة
  alliance_role_permissions— صلاحيات كل دور
  alliance_tax_config      — إعدادات نظام الضرائب
"""
from ..connection import get_db_conn


def create_alliance_governance_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_treasury
    # PURPOSE: Shared treasury for each alliance. Funded by member
    #          contributions, war loot shares, and taxation.
    #          Spent on upgrades, war funding, and member rewards.
    #
    # COLUMNS:
    #   alliance_id      — PK. References alliances.id.
    #   balance          — Current treasury balance.
    #   total_deposited  — Lifetime total deposited.
    #   total_withdrawn  — Lifetime total withdrawn.
    #   last_updated     — Unix timestamp of last change.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_treasury (
        alliance_id     INTEGER PRIMARY KEY,
        balance         REAL    DEFAULT 0,
        total_deposited REAL    DEFAULT 0,
        total_withdrawn REAL    DEFAULT 0,
        last_updated    INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (alliance_id) REFERENCES alliances(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_treasury_log
    # PURPOSE: Immutable ledger of every treasury transaction.
    #
    # COLUMNS:
    #   id           — Internal autoincrement PK.
    #   alliance_id  — Which alliance treasury.
    #   user_id      — Who performed the action (NULL = system).
    #   tx_type      — 'deposit' | 'withdraw' | 'loot_share' |
    #                  'upgrade_cost' | 'war_fund' | 'reward' | 'tax'
    #   amount       — Positive = deposit, negative = withdrawal.
    #   note         — Optional description.
    #   created_at   — When the transaction occurred.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_treasury_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        alliance_id INTEGER NOT NULL,
        user_id     INTEGER,
        tx_type     TEXT    NOT NULL,
        amount      REAL    NOT NULL,
        note        TEXT    DEFAULT '',
        created_at  INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (alliance_id) REFERENCES alliances(id),
        FOREIGN KEY (user_id)     REFERENCES users(user_id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_reputation
    # PURPOSE: Global reputation score for each alliance.
    #          Affects recruitment, war voting weight, and bonuses.
    #
    # COLUMNS:
    #   alliance_id       — PK. References alliances.id.
    #   score             — Overall reputation score (0–1000). Starts 100.
    #   wars_won          — Total political wars won.
    #   wars_lost         — Total political wars lost.
    #   allies_helped     — Times supported another alliance in war.
    #   betrayals         — Times withdrew from a war mid-battle.
    #   inactive_wars     — Times ignored a war vote entirely.
    #   diplomatic_bonus  — Bonus from diplomatic relations (future).
    #   title             — Current reputation title (computed).
    #   last_updated      — When score was last recalculated.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_reputation (
        alliance_id      INTEGER PRIMARY KEY,
        score            REAL    DEFAULT 100,
        wars_won         INTEGER DEFAULT 0,
        wars_lost        INTEGER DEFAULT 0,
        allies_helped    INTEGER DEFAULT 0,
        betrayals        INTEGER DEFAULT 0,
        inactive_wars    INTEGER DEFAULT 0,
        diplomatic_bonus REAL    DEFAULT 0,
        title            TEXT    DEFAULT '😶 غير معروف',
        last_updated     INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (alliance_id) REFERENCES alliances(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_reputation_log
    # PURPOSE: Audit trail for every reputation change event.
    #
    # COLUMNS:
    #   id          — Internal autoincrement PK.
    #   alliance_id — Which alliance.
    #   event_type  — 'war_won' | 'war_lost' | 'helped_ally' |
    #                 'betrayal' | 'inactive' | 'diplomatic' | 'weekly_decay'
    #   delta       — Score change (positive or negative).
    #   note        — Context description.
    #   created_at  — When the event occurred.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_reputation_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        alliance_id INTEGER NOT NULL,
        event_type  TEXT    NOT NULL,
        delta       REAL    NOT NULL,
        note        TEXT    DEFAULT '',
        created_at  INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (alliance_id) REFERENCES alliances(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_titles
    # PURPOSE: Dynamic titles earned by alliances based on their
    #          stats. Multiple titles can be held simultaneously.
    #          Refreshed weekly by the scheduler.
    #
    # COLUMNS:
    #   id          — Internal autoincrement PK.
    #   alliance_id — Which alliance holds this title.
    #   title_key   — Unique key: 'season_empire' | 'strongest_military' |
    #                 'richest' | 'spy_master' | 'most_supportive'
    #   title_ar    — Arabic display name.
    #   emoji       — Display emoji.
    #   earned_at   — When the title was earned.
    #   expires_at  — When the title expires (NULL = permanent until replaced).
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_titles (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        alliance_id INTEGER NOT NULL,
        title_key   TEXT    NOT NULL,
        title_ar    TEXT    NOT NULL,
        emoji       TEXT    DEFAULT '🏆',
        earned_at   INTEGER DEFAULT (strftime('%s','now')),
        expires_at  INTEGER,
        UNIQUE(title_key),
        FOREIGN KEY (alliance_id) REFERENCES alliances(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_role_permissions
    # PURPOSE: Defines what each role (leader/officer/member) can do.
    #          One row per (alliance_id, role, permission).
    #
    # COLUMNS:
    #   id          — Internal autoincrement PK.
    #   alliance_id — Which alliance (NULL = global default).
    #   role        — 'leader' | 'officer' | 'member'
    #   permission  — 'manage_treasury' | 'invite_members' | 'kick_members' |
    #                 'buy_upgrades' | 'declare_war' | 'assign_roles' |
    #                 'reward_members' | 'set_tax'
    #   granted     — 1 = allowed, 0 = denied.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_role_permissions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        alliance_id INTEGER,
        role        TEXT    NOT NULL,
        permission  TEXT    NOT NULL,
        granted     INTEGER DEFAULT 1,
        UNIQUE(alliance_id, role, permission),
        FOREIGN KEY (alliance_id) REFERENCES alliances(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_tax_config
    # PURPOSE: Per-alliance taxation settings. When enabled, a
    #          percentage of each member's income is auto-deposited
    #          into the alliance treasury.
    #
    # COLUMNS:
    #   alliance_id  — PK. References alliances.id.
    #   tax_rate     — Percentage (0.0–0.20). Default 0 = disabled.
    #   enabled      — 1 = active, 0 = disabled.
    #   last_collect — Unix timestamp of last tax collection.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_tax_config (
        alliance_id  INTEGER PRIMARY KEY,
        tax_rate     REAL    DEFAULT 0.0,
        enabled      INTEGER DEFAULT 0,
        last_collect INTEGER DEFAULT 0,
        FOREIGN KEY (alliance_id) REFERENCES alliances(id)
    )
    """)

    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_atl_log_alliance  ON alliance_treasury_log(alliance_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_atl_log_user      ON alliance_treasury_log(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_arep_log_alliance ON alliance_reputation_log(alliance_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_atitles_alliance  ON alliance_titles(alliance_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_arole_perm        ON alliance_role_permissions(alliance_id, role)")

    conn.commit()
    _seed_default_permissions(conn)
    print("✅ [alliance_governance] تم إنشاء جداول حوكمة التحالفات.")


def _seed_default_permissions(conn):
    """يُنشئ الصلاحيات الافتراضية لكل دور (alliance_id=NULL = عالمي)."""
    cursor = conn.cursor()
    defaults = [
        # (role, permission, granted)
        # القائد — كل الصلاحيات
        ("leader", "manage_treasury", 1),
        ("leader", "invite_members",  1),
        ("leader", "kick_members",    1),
        ("leader", "buy_upgrades",    1),
        ("leader", "declare_war",     1),
        ("leader", "assign_roles",    1),
        ("leader", "reward_members",  1),
        ("leader", "set_tax",         1),
        # الضابط — صلاحيات متوسطة
        ("officer", "manage_treasury", 1),
        ("officer", "invite_members",  1),
        ("officer", "kick_members",    1),
        ("officer", "buy_upgrades",    1),
        ("officer", "declare_war",     0),
        ("officer", "assign_roles",    0),
        ("officer", "reward_members",  1),
        ("officer", "set_tax",         0),
        # العضو — صلاحيات محدودة
        ("member", "manage_treasury", 0),
        ("member", "invite_members",  0),
        ("member", "kick_members",    0),
        ("member", "buy_upgrades",    0),
        ("member", "declare_war",     0),
        ("member", "assign_roles",    0),
        ("member", "reward_members",  0),
        ("member", "set_tax",         0),
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO alliance_role_permissions
        (alliance_id, role, permission, granted)
        VALUES (NULL, ?, ?, ?)
    """, defaults)
    conn.commit()
