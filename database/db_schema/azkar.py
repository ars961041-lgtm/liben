from database.connection import get_db_conn


def create_azkar_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # TABLE: azkar
    # PURPOSE: Master list of all zikr (remembrance) texts.
    #          Seeded once at startup. Players read through these
    #          in order during an azkar session.
    #
    # COLUMNS:
    #   id           — Internal autoincrement PK.
    #   text         — The full Arabic text of the zikr.
    #   repeat_count — How many times the user should repeat it.
    #   zikr_type    — Which session: 0=morning, 1=evening,
    #                  2=sleep, 3=wakeup.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS azkar (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        text         TEXT    NOT NULL,
        repeat_count INTEGER NOT NULL DEFAULT 1,
        zikr_type    INTEGER NOT NULL DEFAULT 0
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: azkar_progress
    # PURPOSE: Tracks where each user is in their current azkar
    #          session so they can pause and resume.
    #
    # COLUMNS:
    #   id         — Internal autoincrement PK.
    #   user_id    — References users.user_id.
    #   zikr_type  — Which session type (morning/evening/etc.).
    #   zikr_index — Index of the current zikr in the ordered list.
    #   remaining  — Repetitions left for the current zikr.
    #                -1 means the session hasn't started yet.
    #
    # UNIQUE: (user_id, zikr_type) — one progress row per session per user.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS azkar_progress (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        zikr_type  INTEGER NOT NULL,
        zikr_index INTEGER NOT NULL DEFAULT 0,
        remaining  INTEGER NOT NULL DEFAULT -1,
        UNIQUE(user_id, zikr_type),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: azkar_reminders
    # PURPOSE: Scheduled daily reminders that fire a private message
    #          to the user at their chosen local time.
    #          Timezone is NOT stored here — always fetched live
    #          from user_timezone.tz_offset via a JOIN.
    #
    # COLUMNS:
    #   id         — Internal autoincrement PK.
    #   user_id    — References users.user_id. Who gets the reminder.
    #   azkar_type — Which session to remind about (same codes as azkar.zikr_type).
    #   hour       — Local hour (0–23) to send the reminder.
    #   minute     — Local minute (0–59) to send the reminder.
    #   created_at — Datetime string when the reminder was created.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS azkar_reminders (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        azkar_type INTEGER NOT NULL,
        hour       INTEGER NOT NULL,
        minute     INTEGER NOT NULL,
        created_at TEXT    NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_azkar_type     ON azkar(zikr_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_azkar_rem_user ON azkar_reminders(user_id)")

    conn.commit()
