"""
جداول نظام التصويت المتقدم.
"""
from ..connection import get_db_conn


def create_polls_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # TABLE: polls
    # show_voters: إذا 1 يمكن عرض قائمة المصوتين لكل خيار
    # lock_before_end: قفل تغيير الصوت قبل X ثانية من الإغلاق
    # max_vote_changes: الحد الأقصى لتغيير الصوت (0 = غير محدود)
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS polls (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id                 INTEGER NOT NULL,
        message_id              INTEGER DEFAULT NULL,
        question                TEXT    NOT NULL,
        question_media_id       TEXT    DEFAULT NULL,
        question_media_type     TEXT    DEFAULT NULL,
        description             TEXT    DEFAULT NULL,
        description_media_id    TEXT    DEFAULT NULL,
        description_media_type  TEXT    DEFAULT NULL,
        poll_type               TEXT    NOT NULL DEFAULT 'normal',
        allow_change            INTEGER NOT NULL DEFAULT 1,
        max_vote_changes        INTEGER NOT NULL DEFAULT 0,
        lock_before_end         INTEGER NOT NULL DEFAULT 0,
        is_hidden               INTEGER NOT NULL DEFAULT 0,
        show_voters             INTEGER NOT NULL DEFAULT 0,
        is_closed               INTEGER NOT NULL DEFAULT 0,
        end_time                INTEGER DEFAULT NULL,
        created_by              INTEGER NOT NULL,
        created_at              INTEGER NOT NULL
    );
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: poll_options
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS poll_options (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        poll_id       INTEGER NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
        text          TEXT    NOT NULL,
        color         TEXT    NOT NULL DEFAULT 'p',
        votes_count   INTEGER NOT NULL DEFAULT 0
    );
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: poll_votes
    # change_count: عدد مرات تغيير الصوت
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS poll_votes (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        poll_id      INTEGER NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
        user_id      INTEGER NOT NULL,
        option_id    INTEGER NOT NULL REFERENCES poll_options(id) ON DELETE CASCADE,
        voted_at     INTEGER NOT NULL,
        change_count INTEGER NOT NULL DEFAULT 0,
        UNIQUE(poll_id, user_id)
    );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_polls_chat ON polls(chat_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_polls_end_time ON polls(end_time) WHERE end_time IS NOT NULL;")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_poll_votes_poll_user ON poll_votes(poll_id, user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_poll_options_poll ON poll_options(poll_id);")

    conn.commit()

    # safe migration for existing databases
    try:
        cursor.execute("ALTER TABLE poll_options ADD COLUMN color TEXT NOT NULL DEFAULT 'p'")
        conn.commit()
    except Exception:
        pass  # column already exists
