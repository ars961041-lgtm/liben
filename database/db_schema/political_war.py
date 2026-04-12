"""
نظام الحرب السياسية — مخطط قاعدة البيانات
Political War System — Database Schema

Tables:
  political_wars        — إعلانات الحرب السياسية
  political_war_votes   — تصويت الدول الحليفة
  political_war_members — الدول المشاركة فعلياً
  political_war_log     — سجل كامل لكل الأحداث
  war_cooldowns         — كولداون إعلان الحرب لكل تحالف
"""
import time
from ..connection import get_db_conn


def create_political_war_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS political_wars (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        war_type              TEXT    NOT NULL DEFAULT 'country_vs_country',
        declaration_type      TEXT    NOT NULL DEFAULT 'offensive',
        attacker_country_id   INTEGER,
        attacker_alliance_id  INTEGER,
        defender_country_id   INTEGER,
        defender_alliance_id  INTEGER,
        reason                TEXT    DEFAULT '',
        status                TEXT    NOT NULL DEFAULT 'voting',
        -- مرحلة التصويت
        voting_ends_at        INTEGER NOT NULL,
        vote_threshold        REAL    DEFAULT 0.60,
        vote_support_pct      REAL    DEFAULT 0,
        -- مرحلة التحضير (بعد نجاح التصويت)
        preparation_ends_at   INTEGER,
        -- مرحلة الحرب
        started_at            INTEGER,
        ended_at              INTEGER,
        winner_side           TEXT,
        -- تكلفة الإعلان
        war_cost              REAL    DEFAULT 0,
        declared_by_user_id   INTEGER NOT NULL,
        created_at            INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (attacker_country_id)  REFERENCES countries(id),
        FOREIGN KEY (attacker_alliance_id) REFERENCES alliances(id),
        FOREIGN KEY (defender_country_id)  REFERENCES countries(id),
        FOREIGN KEY (defender_alliance_id) REFERENCES alliances(id),
        FOREIGN KEY (declared_by_user_id)  REFERENCES users(user_id)
    )
    """)

    # إضافة الأعمدة الجديدة إذا لم تكن موجودة (للتوافق مع قواعد بيانات قديمة)
    _add_column_if_missing(cursor, "political_wars", "vote_threshold",       "REAL DEFAULT 0.60")
    _add_column_if_missing(cursor, "political_wars", "vote_support_pct",     "REAL DEFAULT 0")
    _add_column_if_missing(cursor, "political_wars", "preparation_ends_at",  "INTEGER")
    _add_column_if_missing(cursor, "political_wars", "war_cost",             "REAL DEFAULT 0")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS political_war_votes (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        war_id           INTEGER NOT NULL,
        voter_country_id INTEGER NOT NULL,
        voter_user_id    INTEGER NOT NULL,
        alliance_id      INTEGER NOT NULL,
        vote             TEXT    NOT NULL DEFAULT 'neutral',
        vote_weight      REAL    DEFAULT 1.0,
        military_power   REAL    DEFAULT 0,
        economy_score    REAL    DEFAULT 0,
        alliance_rank    INTEGER DEFAULT 1,
        voted_at         INTEGER DEFAULT (strftime('%s','now')),
        UNIQUE(war_id, voter_country_id),
        FOREIGN KEY (war_id)           REFERENCES political_wars(id),
        FOREIGN KEY (voter_country_id) REFERENCES countries(id),
        FOREIGN KEY (voter_user_id)    REFERENCES users(user_id),
        FOREIGN KEY (alliance_id)      REFERENCES alliances(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS political_war_members (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        war_id               INTEGER NOT NULL,
        country_id           INTEGER NOT NULL,
        user_id              INTEGER NOT NULL,
        side                 TEXT    NOT NULL,
        joined_before_start  INTEGER DEFAULT 1,
        withdrew             INTEGER DEFAULT 0,
        withdrew_at          INTEGER,
        power_contributed    REAL    DEFAULT 0,
        reputation_penalty   REAL    DEFAULT 0,
        loyalty_delta        REAL    DEFAULT 0,
        joined_at            INTEGER DEFAULT (strftime('%s','now')),
        UNIQUE(war_id, country_id),
        FOREIGN KEY (war_id)     REFERENCES political_wars(id),
        FOREIGN KEY (country_id) REFERENCES countries(id),
        FOREIGN KEY (user_id)    REFERENCES users(user_id)
    )
    """)

    _add_column_if_missing(cursor, "political_war_members", "loyalty_delta", "REAL DEFAULT 0")
    _add_column_if_missing(cursor, "political_war_votes",   "vote_change_count", "INTEGER DEFAULT 0")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS political_war_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        war_id      INTEGER NOT NULL,
        country_id  INTEGER,
        user_id     INTEGER,
        event_type  TEXT    NOT NULL,
        event_data  TEXT    DEFAULT '{}',
        created_at  INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (war_id)     REFERENCES political_wars(id),
        FOREIGN KEY (country_id) REFERENCES countries(id),
        FOREIGN KEY (user_id)    REFERENCES users(user_id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: war_cooldowns
    # PURPOSE: Prevents an alliance from declaring war too frequently.
    #          One row per alliance, updated after each declaration.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS war_cooldowns (
        alliance_id   INTEGER PRIMARY KEY,
        last_declared INTEGER NOT NULL DEFAULT 0,
        cooldown_sec  INTEGER NOT NULL DEFAULT 43200,
        FOREIGN KEY (alliance_id) REFERENCES alliances(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_loyalty
    # PURPOSE: Per-country loyalty score within their alliance.
    #          Affects voting weight, reward share, and promotions.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_loyalty (
        alliance_id   INTEGER NOT NULL,
        country_id    INTEGER NOT NULL,
        user_id       INTEGER NOT NULL,
        loyalty_score REAL    DEFAULT 50,
        label         TEXT    DEFAULT 'محايد',
        updated_at    INTEGER DEFAULT (strftime('%s','now')),
        PRIMARY KEY (alliance_id, country_id),
        FOREIGN KEY (alliance_id) REFERENCES alliances(id),
        FOREIGN KEY (country_id)  REFERENCES countries(id),
        FOREIGN KEY (user_id)     REFERENCES users(user_id)
    )
    """)

    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_wars_status       ON political_wars(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_wars_attacker_c   ON political_wars(attacker_country_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_wars_defender_c   ON political_wars(defender_country_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_wars_attacker_a   ON political_wars(attacker_alliance_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_wars_defender_a   ON political_wars(defender_alliance_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_votes_war         ON political_war_votes(war_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_votes_voter       ON political_war_votes(voter_country_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_members_war       ON political_war_members(war_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_members_country   ON political_war_members(country_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_log_war           ON political_war_log(war_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_log_user          ON political_war_log(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_loyalty_alliance      ON alliance_loyalty(alliance_id)")

    conn.commit()
    print("✅ [political_war] تم إنشاء جداول نظام الحرب السياسية.")


def _add_column_if_missing(cursor, table: str, column: str, definition: str):
    """يُضيف عموداً إذا لم يكن موجوداً — آمن للترقية."""
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    except Exception:
        pass  # العمود موجود بالفعل
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # TABLE: political_wars
    # PURPOSE: The root record for every political war event.
    #          Supports country-vs-country, alliance-vs-alliance,
    #          and hybrid (country-vs-alliance) war types.
    #
    # COLUMNS:
    #   id                    — Internal autoincrement PK.
    #   war_type              — 'country_vs_country' | 'alliance_vs_alliance' | 'hybrid'
    #   declaration_type      — 'offensive' | 'defensive'
    #   attacker_country_id   — Declaring country (NULL if alliance-only war).
    #   attacker_alliance_id  — Declaring alliance (NULL if country-only war).
    #   defender_country_id   — Target country (NULL if alliance-only war).
    #   defender_alliance_id  — Target alliance (NULL if country-only war).
    #   reason                — Optional reason text (metadata for reputation).
    #   status                — 'voting' → 'active' → 'ended' | 'cancelled'
    #   voting_ends_at        — Unix timestamp when voting phase closes.
    #   started_at            — When the war became active (voting passed).
    #   ended_at              — When the war ended.
    #   winner_side           — 'attacker' | 'defender' | 'draw' | NULL
    #   declared_by_user_id   — The user who declared the war.
    #   created_at            — When the declaration was made.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS political_wars (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        war_type              TEXT    NOT NULL DEFAULT 'country_vs_country',
        declaration_type      TEXT    NOT NULL DEFAULT 'offensive',
        attacker_country_id   INTEGER,
        attacker_alliance_id  INTEGER,
        defender_country_id   INTEGER,
        defender_alliance_id  INTEGER,
        reason                TEXT    DEFAULT '',
        status                TEXT    NOT NULL DEFAULT 'voting',
        voting_ends_at        INTEGER NOT NULL,
        started_at            INTEGER,
        ended_at              INTEGER,
        winner_side           TEXT,
        declared_by_user_id   INTEGER NOT NULL,
        created_at            INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (attacker_country_id)  REFERENCES countries(id),
        FOREIGN KEY (attacker_alliance_id) REFERENCES alliances(id),
        FOREIGN KEY (defender_country_id)  REFERENCES countries(id),
        FOREIGN KEY (defender_alliance_id) REFERENCES alliances(id),
        FOREIGN KEY (declared_by_user_id)  REFERENCES users(user_id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: political_war_votes
    # PURPOSE: Records each allied country's vote on whether to
    #          participate in a declared war. Voting weight is
    #          computed from military power + economy + alliance rank.
    #
    # COLUMNS:
    #   id              — Internal autoincrement PK.
    #   war_id          — References political_wars.id.
    #   voter_country_id— The country casting the vote.
    #   voter_user_id   — The player who cast the vote.
    #   alliance_id     — Which alliance this voter belongs to.
    #   vote            — 'support' | 'reject' | 'neutral'
    #   vote_weight     — Computed weight at time of vote (military+economy+rank).
    #   military_power  — Snapshot of voter's military power at vote time.
    #   economy_score   — Snapshot of voter's economy score at vote time.
    #   alliance_rank   — Voter's role weight: leader=3, member=1.
    #   voted_at        — When the vote was cast.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS political_war_votes (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        war_id           INTEGER NOT NULL,
        voter_country_id INTEGER NOT NULL,
        voter_user_id    INTEGER NOT NULL,
        alliance_id      INTEGER NOT NULL,
        vote             TEXT    NOT NULL DEFAULT 'neutral',
        vote_weight      REAL    DEFAULT 1.0,
        military_power   REAL    DEFAULT 0,
        economy_score    REAL    DEFAULT 0,
        alliance_rank    INTEGER DEFAULT 1,
        voted_at         INTEGER DEFAULT (strftime('%s','now')),
        UNIQUE(war_id, voter_country_id),
        FOREIGN KEY (war_id)           REFERENCES political_wars(id),
        FOREIGN KEY (voter_country_id) REFERENCES countries(id),
        FOREIGN KEY (voter_user_id)    REFERENCES users(user_id),
        FOREIGN KEY (alliance_id)      REFERENCES alliances(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: political_war_members
    # PURPOSE: Countries that are actively participating in a war
    #          after the voting phase resolves. Tracks their side,
    #          contribution, and whether they withdrew.
    #
    # COLUMNS:
    #   id              — Internal autoincrement PK.
    #   war_id          — References political_wars.id.
    #   country_id      — The participating country.
    #   user_id         — The player who owns the country.
    #   side            — 'attacker' | 'defender'
    #   joined_before_start — 1 if joined during voting, 0 if joined after war started.
    #   withdrew        — 1 if the country withdrew from the war.
    #   withdrew_at     — When they withdrew (NULL if still active).
    #   power_contributed — Military power contributed to their side.
    #   reputation_penalty — Penalty applied on withdrawal after war started.
    #   joined_at       — When they joined.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS political_war_members (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        war_id               INTEGER NOT NULL,
        country_id           INTEGER NOT NULL,
        user_id              INTEGER NOT NULL,
        side                 TEXT    NOT NULL,
        joined_before_start  INTEGER DEFAULT 1,
        withdrew             INTEGER DEFAULT 0,
        withdrew_at          INTEGER,
        power_contributed    REAL    DEFAULT 0,
        reputation_penalty   REAL    DEFAULT 0,
        joined_at            INTEGER DEFAULT (strftime('%s','now')),
        UNIQUE(war_id, country_id),
        FOREIGN KEY (war_id)     REFERENCES political_wars(id),
        FOREIGN KEY (country_id) REFERENCES countries(id),
        FOREIGN KEY (user_id)    REFERENCES users(user_id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: political_war_log
    # PURPOSE: Immutable audit log of every significant event in a
    #          political war. Used for reputation, rankings, and
    #          future analytics. Never deleted.
    #
    # COLUMNS:
    #   id          — Internal autoincrement PK.
    #   war_id      — References political_wars.id.
    #   country_id  — The country involved in this event (NULL for system events).
    #   user_id     — The player involved (NULL for system events).
    #   event_type  — 'declared' | 'voted_support' | 'voted_reject' | 'voted_neutral'
    #                 | 'war_started' | 'war_ended' | 'withdrew_before' | 'withdrew_after'
    #                 | 'joined_late' | 'cancelled'
    #   event_data  — JSON metadata for the event (e.g. vote weight, reason).
    #   created_at  — When the event occurred.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS political_war_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        war_id      INTEGER NOT NULL,
        country_id  INTEGER,
        user_id     INTEGER,
        event_type  TEXT    NOT NULL,
        event_data  TEXT    DEFAULT '{}',
        created_at  INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (war_id)     REFERENCES political_wars(id),
        FOREIGN KEY (country_id) REFERENCES countries(id),
        FOREIGN KEY (user_id)    REFERENCES users(user_id)
    )
    """)

    # Indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_wars_status       ON political_wars(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_wars_attacker_c   ON political_wars(attacker_country_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_wars_defender_c   ON political_wars(defender_country_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_wars_attacker_a   ON political_wars(attacker_alliance_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_wars_defender_a   ON political_wars(defender_alliance_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_votes_war         ON political_war_votes(war_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_votes_voter       ON political_war_votes(voter_country_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_members_war       ON political_war_members(war_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_members_country   ON political_war_members(country_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_log_war           ON political_war_log(war_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pol_log_user          ON political_war_log(user_id)")

    conn.commit()
    print("✅ [political_war] تم إنشاء جداول نظام الحرب السياسية.")
