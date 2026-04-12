"""
نظام الزخم الحربي والقائمة السوداء للتحالفات
Alliance War Momentum + Blacklist — Database Schema

Tables:
  alliance_war_momentum — سلسلة الانتصارات المتتالية وبونص القوة المؤقت
  alliance_blacklist    — قائمة الدول المحظورة من الانضمام لتحالف معين
"""
from ..connection import get_db_conn


def create_alliance_extras_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_war_momentum
    # PURPOSE: Tracks consecutive political-war victories per alliance.
    #          Each win increments win_streak and grants a temporary
    #          power bonus (+2% per win, capped at +10%).
    #          A loss resets win_streak to 0 and removes the bonus.
    #
    # COLUMNS:
    #   alliance_id    — PK. References alliances.id.
    #   win_streak     — Current consecutive win count (0–5).
    #   power_bonus    — Active bonus multiplier (0.0–0.10).
    #                    Applied as: power × (1 + power_bonus).
    #   last_updated   — Unix timestamp of last streak change.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_war_momentum (
        alliance_id  INTEGER PRIMARY KEY,
        win_streak   INTEGER DEFAULT 0,
        power_bonus  REAL    DEFAULT 0.0,
        last_updated INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (alliance_id) REFERENCES alliances(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_blacklist
    # PURPOSE: Countries that an alliance has banned from joining.
    #          Enforced during invite sending and invite acceptance.
    #
    # COLUMNS:
    #   id           — Internal autoincrement PK.
    #   alliance_id  — The alliance that issued the ban.
    #   country_id   — The banned country.
    #   banned_by    — user_id of the leader/officer who added the ban.
    #   reason       — Optional reason text.
    #   created_at   — When the ban was added.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_blacklist (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        alliance_id INTEGER NOT NULL,
        country_id  INTEGER NOT NULL,
        banned_by   INTEGER NOT NULL,
        reason      TEXT    DEFAULT '',
        created_at  INTEGER DEFAULT (strftime('%s','now')),
        UNIQUE(alliance_id, country_id),
        FOREIGN KEY (alliance_id) REFERENCES alliances(id),
        FOREIGN KEY (country_id)  REFERENCES countries(id),
        FOREIGN KEY (banned_by)   REFERENCES users(user_id)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_momentum_alliance ON alliance_war_momentum(alliance_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_blacklist_alliance ON alliance_blacklist(alliance_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_blacklist_country  ON alliance_blacklist(country_id)")

    conn.commit()
    print("✅ [alliance_extras] تم إنشاء جداول الزخم والقائمة السوداء.")
