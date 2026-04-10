"""
groups.py — Group tables, feature flags, mutes

How to add a new group feature:
  1. Add it to FEATURES with its default value.
  2. Add the column inside CREATE TABLE below.
  3. The safe migration loop handles existing databases automatically.

Default values: 1 = enabled by default, 0 = disabled.
"""

from ..connection import get_db_conn


FEATURES = {
    "enable_games":         1,   # 🎮 Games (bank, countries, war, alliances)
    "enable_admin":         1,   # 🛠 Admin tools (mute, ban, restrict, promote)
    "enable_replies":       1,   # 💬 Auto-replies
    "enable_welcome":       1,   # 👋 Welcome / farewell messages
    "enable_profile":       1,   # 👤 User profile (about me / about them)
    "enable_media":         1,   # 🎨 Media commands (stickers, interactive media)
    "enable_lock_stickers": 0,   # 🎭 Delete stickers from non-admins
    "enable_lock_media":    0,   # 🖼 Delete media from non-admins (photos/video/files)
    "quotes_enabled":       0,   # 💬 Periodic quotes/wisdom sent to the group
    "enable_whispers":      1,   # 💌 Whisper system (private messages between members)
    "enable_leave_notify":  1,   # 🚪 Leave/kick/ban notifications

    # ── Future features (add here) ────────────────────────────
    # "enable_azkar":   1,
    # "enable_quran":   1,
    # "enable_economy": 1,
}


def create_groups_tables():
    conn   = get_db_conn()
    cursor = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # TABLE: groups
    # PURPOSE: One row per Telegram group the bot is active in.
    #          Stores the group's identity and all per-group feature
    #          flags that control which bot modules are active.
    #
    # COLUMNS:
    #   id                   — Internal autoincrement PK. Used in all FK relations.
    #   group_id             — Telegram chat ID. The external identifier.
    #   name                 — Group name at the time of registration.
    #   joined_at            — Unix timestamp when the bot first joined.
    #   enable_games         — 1 = games module active (bank, war, countries).
    #   enable_admin         — 1 = admin tools active (mute, ban, restrict).
    #   enable_replies       — 1 = bot responds to trigger words.
    #   enable_welcome       — 1 = bot sends welcome/farewell messages.
    #   enable_profile       — 1 = users can view profiles.
    #   enable_media         — 1 = media/sticker commands active.
    #   enable_lock_stickers — 1 = bot deletes stickers from non-admins.
    #   enable_lock_media    — 1 = bot deletes photos/videos/files from non-admins.
    #   enable_leave_notify  — 1 = bot sends leave/kick/ban notifications.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS groups (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id  INTEGER NOT NULL UNIQUE,
        name      TEXT    NOT NULL,
        joined_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),

        enable_games          INTEGER NOT NULL DEFAULT 1,
        enable_admin          INTEGER NOT NULL DEFAULT 1,
        enable_replies        INTEGER NOT NULL DEFAULT 1,
        enable_welcome        INTEGER NOT NULL DEFAULT 1,
        enable_profile        INTEGER NOT NULL DEFAULT 1,
        enable_media          INTEGER NOT NULL DEFAULT 1,
        enable_lock_stickers  INTEGER NOT NULL DEFAULT 0,
        enable_lock_media     INTEGER NOT NULL DEFAULT 0,
        quotes_enabled        INTEGER NOT NULL DEFAULT 0,
        enable_whispers       INTEGER NOT NULL DEFAULT 1,
        enable_leave_notify   INTEGER NOT NULL DEFAULT 1

        -- Add new feature columns here, e.g.:
        -- enable_azkar  INTEGER NOT NULL DEFAULT 1,
    );
    """)

    # Safe migration: adds any new column from FEATURES to existing databases.
    for col, default in FEATURES.items():
        try:
            cursor.execute(
                f"ALTER TABLE groups ADD COLUMN {col} INTEGER NOT NULL DEFAULT {default}"
            )
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────
    # TABLE: group_members
    # PURPOSE: Tracks each user's membership, activity, and
    #          moderation status inside a specific group.
    #          group_id references groups.id (internal PK).
    #
    # COLUMNS:
    #   id             — Internal autoincrement PK.
    #   user_id        — References users.user_id.
    #   group_id       — References groups.id (NOT the Telegram chat ID).
    #   messages_count — Total messages sent. Used for activity leaderboards.
    #   is_muted       — 1 = user is muted in this group.
    #   is_restricted  — 1 = user has limited permissions.
    #   is_banned      — 1 = user is banned from this group.
    #   is_active      — 1 = user is currently in the group. 0 = left/kicked.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS group_members (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id        INTEGER NOT NULL,
        group_id       INTEGER NOT NULL,
        messages_count INTEGER NOT NULL DEFAULT 0,
        is_muted       INTEGER NOT NULL DEFAULT 0,
        is_restricted  INTEGER NOT NULL DEFAULT 0,
        is_banned      INTEGER NOT NULL DEFAULT 0,
        is_active      INTEGER NOT NULL DEFAULT 1,
        UNIQUE(user_id, group_id),
        FOREIGN KEY (user_id)  REFERENCES users(user_id),
        FOREIGN KEY (group_id) REFERENCES groups(id)
    );
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: group_punishment_log
    # PURPOSE: Immutable audit log of every moderation action
    #          (mute, ban, restrict, and their reversals).
    #          Used for history queries and admin accountability.
    #
    # COLUMNS:
    #   id          — Internal autoincrement PK.
    #   group_id    — References groups.id. Which group the action happened in.
    #   user_id     — The user who was punished.
    #   action_type — Numeric code: 1=mute, 2=ban, 3=restrict,
    #                 4=unmute, 5=unban, 6=unrestrict.
    #   executor_id — The admin who performed the action.
    #   timestamp   — Unix timestamp when the action occurred.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS group_punishment_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id    INTEGER NOT NULL,
        user_id     INTEGER NOT NULL,
        action_type TINYINT NOT NULL,
        executor_id INTEGER NOT NULL,
        timestamp   INTEGER NOT NULL DEFAULT (strftime('%s','now')),
        FOREIGN KEY (group_id)    REFERENCES groups(id),
        FOREIGN KEY (user_id)     REFERENCES users(user_id),
        FOREIGN KEY (executor_id) REFERENCES users(user_id)
    );
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: group_mutes
    # PURPOSE: Active per-group mutes. One row = one user currently
    #          muted in one specific group. Separate from global_mutes.
    #
    # COLUMNS:
    #   id       — Internal autoincrement PK.
    #   user_id  — The muted user.
    #   group_id — References groups.id. Which group the mute applies to.
    #   reason   — Optional reason text for the mute.
    #   muted_by — The admin who issued the mute.
    #   muted_at — Unix timestamp when the mute was applied.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS group_mutes (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id  INTEGER NOT NULL,
        group_id INTEGER NOT NULL,
        reason   TEXT    DEFAULT '',
        muted_by INTEGER,
        muted_at INTEGER DEFAULT (strftime('%s','now')),
        UNIQUE(user_id, group_id),
        FOREIGN KEY (user_id)  REFERENCES users(user_id),
        FOREIGN KEY (group_id) REFERENCES groups(id),
        FOREIGN KEY (muted_by) REFERENCES users(user_id)
    );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_groups_group_id        ON groups(group_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_group_members_group_msg ON group_members(group_id, messages_count DESC);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_group_members_user_group ON group_members(user_id, group_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_group_mutes_user_group  ON group_mutes(user_id, group_id);")

    conn.commit()
