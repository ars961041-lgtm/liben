"""
قاعدة بيانات نظام إنجاز القرآن — content_hub.db (جداول مشتركة)
"""
import sqlite3
import threading
from typing import Optional

from core.config import DB_CONTENT

_local   = threading.local()

# ── فاصل التحرير الجماعي ──
BULK_SEPARATOR = "---"

# ── أنواع التفسير المدعومة ──
TAFSEER_TYPES = {
    "المختصر":  "tafseer_mukhtasar",
    "السعدي":   "tafseer_saadi",
    "الميسر":   "tafseer_muyassar",
}

# ── أسماء السور (بدون تشكيل) ──
SURAS_NAMES = [
    "الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس",
    "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه",
    "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم",
    "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر",
    "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق",
    "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة",
    "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحريم", "الملك", "القلم", "الحاقة", "المعارج",
    "نوح", "الجن", "المزمل", "المدثر", "القيامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس",
    "التكوير", "الانفطار", "المطففين", "الانشقاق", "البروج", "الطارق", "الأعلى", "الغاشية", "الفجر", "البلد",
    "الشمس", "الليل", "الضحى", "الشرح", "التين", "العلق", "القدر", "البينة", "الزلزلة", "العاديات",
    "القارعة", "التكاثر", "العصر", "الهمزة", "الفيل", "قريش", "الماعون", "الكوثر", "الكافرون", "النصر",
    "المسد", "الإخلاص", "الفلق", "الناس"
]


def _get_conn() -> sqlite3.Connection:
    if getattr(_local, "conn", None) is None:
        import os
        if not os.path.exists(DB_CONTENT):
            directory = os.path.dirname(DB_CONTENT)
            if directory:
                os.makedirs(directory, exist_ok=True)
        conn = sqlite3.connect(DB_CONTENT, check_same_thread=False, timeout=10)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return _local.conn


def auto_insert_suras():
    """إدراج جميع السور تلقائياً إذا لم تكن موجودة."""
    conn = _get_conn()
    cur  = conn.cursor()

    for i, name in enumerate(SURAS_NAMES, 1):
        cur.execute(
            "INSERT OR IGNORE INTO suras (id, name) VALUES (?, ?)",
            (i, name)
        )

    conn.commit()


def create_tables():
    conn = _get_conn()
    cur  = conn.cursor()

    # ── السور ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS suras (
        id   INTEGER PRIMARY KEY,
        name TEXT    NOT NULL UNIQUE
    )
    """)

    # ── الآيات ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ayat (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        sura_id              INTEGER NOT NULL,
        ayah_number          INTEGER NOT NULL,
        text_with_tashkeel   TEXT    NOT NULL,
        text_without_tashkeel TEXT   NOT NULL,
        tafseer_mukhtasar    TEXT    DEFAULT NULL,
        tafseer_saadi        TEXT    DEFAULT NULL,
        tafseer_muyassar     TEXT    DEFAULT NULL,
        FOREIGN KEY (sura_id) REFERENCES suras(id),
        UNIQUE(sura_id, ayah_number)
    )
    """)

    # ── تقدم القراءة ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_quran_progress (
        user_id     INTEGER PRIMARY KEY,
        last_ayah_id INTEGER NOT NULL DEFAULT 1,
        message_id  INTEGER DEFAULT NULL
    )
    """)

    # ── المفضلة ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_favorites (
        user_id  INTEGER NOT NULL,
        ayah_id  INTEGER NOT NULL,
        added_at INTEGER DEFAULT (strftime('%s','now')),
        PRIMARY KEY (user_id, ayah_id),
        FOREIGN KEY (ayah_id) REFERENCES ayat(id)
    )
    """)

    # ── فهارس ──
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ayat_sura ON ayat(sura_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ayat_search ON ayat(text_without_tashkeel)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fav_user ON user_favorites(user_id)")

    # ── تقدم قراءة السور ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS surah_read_progress (
        user_id  INTEGER NOT NULL,
        surah_id INTEGER NOT NULL,
        ayah     INTEGER NOT NULL DEFAULT 1,
        PRIMARY KEY (user_id, surah_id)
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_srp_user ON surah_read_progress(user_id)")

    # ── ختمة القرآن ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS khatma_progress (
        user_id     INTEGER PRIMARY KEY,
        last_surah  INTEGER NOT NULL DEFAULT 1,
        last_ayah   INTEGER NOT NULL DEFAULT 1,
        total_read  INTEGER NOT NULL DEFAULT 0,
        updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ── الهدف اليومي ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS khatma_goals (
        user_id       INTEGER PRIMARY KEY,
        daily_target  INTEGER NOT NULL DEFAULT 10
    )
    """)

    # ── سجل القراءة اليومي (للاقتراح الذكي) ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS khatma_daily_log (
        user_id   INTEGER NOT NULL,
        log_date  TEXT    NOT NULL,
        count     INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (user_id, log_date)
    )
    """)

    # ── الاستمرارية (streak) ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS khatma_streak (
        user_id        INTEGER PRIMARY KEY,
        current_streak INTEGER NOT NULL DEFAULT 0,
        last_read_date TEXT
    )
    """)

    # ── تذكيرات الختمة ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS khatma_reminders (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        hour       INTEGER NOT NULL,
        minute     INTEGER NOT NULL,
        tz_offset  INTEGER NOT NULL DEFAULT 0,
        enabled    INTEGER NOT NULL DEFAULT 1
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_kh_rem_user ON khatma_reminders(user_id)")

    # ── تتبع الآيات المحسوبة (منع التكرار) ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS khatma_counted_ayat (
        user_id  INTEGER NOT NULL,
        ayah_id  INTEGER NOT NULL,
        log_date TEXT    NOT NULL,
        PRIMARY KEY (user_id, ayah_id, log_date)
    )
    """)

    conn.commit()

    # ── إدراج السور تلقائياً ──
    auto_insert_suras()


# ══════════════════════════════════════════
# الآيات
# ══════════════════════════════════════════

def get_ayah(ayah_id: int) -> Optional[dict]:
    cur = _get_conn().cursor()
    cur.execute("""
        SELECT a.*, s.name as sura_name
        FROM ayat a
        JOIN suras s ON a.sura_id = s.id
        WHERE a.id=?
    """, (ayah_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_ayah_by_sura_number(sura_id: int, ayah_number: int) -> Optional[dict]:
    cur = _get_conn().cursor()
    cur.execute("""
        SELECT a.*, s.name as sura_name
        FROM ayat a
        JOIN suras s ON a.sura_id = s.id
        WHERE a.sura_id=? AND a.ayah_number=?
    """, (sura_id, ayah_number))
    row = cur.fetchone()
    return dict(row) if row else None


def get_first_ayah() -> Optional[dict]:
    cur = _get_conn().cursor()
    cur.execute("""
        SELECT a.*, s.name as sura_name
        FROM ayat a
        JOIN suras s ON a.sura_id = s.id
        ORDER BY a.id ASC LIMIT 1
    """)
    row = cur.fetchone()
    return dict(row) if row else None


def get_next_ayah(current_id: int) -> Optional[dict]:
    cur = _get_conn().cursor()
    cur.execute("""
        SELECT a.*, s.name as sura_name
        FROM ayat a
        JOIN suras s ON a.sura_id = s.id
        WHERE a.id > ? ORDER BY a.id ASC LIMIT 1
    """, (current_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_prev_ayah(current_id: int) -> Optional[dict]:
    cur = _get_conn().cursor()
    cur.execute("""
        SELECT a.*, s.name as sura_name
        FROM ayat a
        JOIN suras s ON a.sura_id = s.id
        WHERE a.id < ? ORDER BY a.id DESC LIMIT 1
    """, (current_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_total_ayat() -> int:
    cur = _get_conn().cursor()
    cur.execute("SELECT COUNT(*) FROM ayat")
    return cur.fetchone()[0]


def search_ayat(normalized_query: str) -> list[dict]:
    """يبحث في النص بدون تشكيل."""
    cur = _get_conn().cursor()
    cur.execute("""
        SELECT a.*, s.name as sura_name
        FROM ayat a
        JOIN suras s ON a.sura_id = s.id
        WHERE a.text_without_tashkeel LIKE ?
        ORDER BY a.id ASC LIMIT 50
    """, (f"%{normalized_query}%",))
    return [dict(r) for r in cur.fetchall()]


def insert_ayah(sura_id: int, ayah_number: int,
                text_with: str, text_without: str) -> int:
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO ayat (sura_id, ayah_number, text_with_tashkeel, text_without_tashkeel)
        VALUES (?,?,?,?)
    """, (sura_id, ayah_number, text_with.strip(), text_without.strip()))
    conn.commit()
    return cur.lastrowid or 0


def update_ayah_text(ayah_id: int, text_with: str, text_without: str) -> bool:
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute(
        "UPDATE ayat SET text_with_tashkeel=?, text_without_tashkeel=? WHERE id=?",
        (text_with.strip(), text_without.strip(), ayah_id),
    )
    conn.commit()
    return cur.rowcount > 0


def update_tafseer(ayah_id: int, tafseer_col: str, content: str) -> bool:
    if tafseer_col not in TAFSEER_TYPES.values():
        return False
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute(
        f"UPDATE ayat SET {tafseer_col}=? WHERE id=?",
        (content.strip(), ayah_id),
    )
    conn.commit()
    return cur.rowcount > 0


def get_sura(sura_id: int) -> Optional[dict]:
    cur = _get_conn().cursor()
    cur.execute("SELECT * FROM suras WHERE id=?", (sura_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_sura_by_name(name: str) -> Optional[dict]:
    cur = _get_conn().cursor()
    cur.execute("SELECT * FROM suras WHERE name=?", (name,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_all_suras() -> list[dict]:
    cur = _get_conn().cursor()
    cur.execute("SELECT * FROM suras ORDER BY id ASC")
    return [dict(r) for r in cur.fetchall()]


def get_next_tafseer_ayah(sura_id: int, tafseer_col: str) -> int:
    """
    يرجع رقم الآية التالية التي تحتاج تفسيراً في السورة.
    يبحث عن أول آية بدون تفسير بالترتيب.
    إذا كل الآيات لها تفسير → يرجع آخر رقم + 1
    """
    cur = _get_conn().cursor()
    cur.execute(
        f"SELECT ayah_number FROM ayat WHERE sura_id=? AND ({tafseer_col} IS NULL OR {tafseer_col}='') ORDER BY ayah_number ASC LIMIT 1",
        (sura_id,),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    # كل الآيات لها تفسير — رجّع آخر رقم + 1
    cur.execute("SELECT MAX(ayah_number) FROM ayat WHERE sura_id=?", (sura_id,))
    row = cur.fetchone()
    return (row[0] or 0) + 1


def get_ayat_by_sura(sura_id: int) -> list[dict]:
    """
    يرجع رقم الآية التالية للإدراج في السورة.
    إذا لم توجد آيات → 1
    وإلا → آخر رقم + 1
    """
    cur = _get_conn().cursor()
    cur.execute(
        "SELECT MAX(ayah_number) FROM ayat WHERE sura_id=?",
        (sura_id,),
    )
    row = cur.fetchone()
    last = row[0] if row and row[0] else 0
    return last + 1


def get_ayat_by_sura(sura_id: int) -> list[dict]:
    cur = _get_conn().cursor()
    cur.execute("""
        SELECT a.*, s.name as sura_name
        FROM ayat a
        JOIN suras s ON a.sura_id = s.id
        WHERE a.sura_id=? ORDER BY a.ayah_number ASC
    """, (sura_id,))
    return [dict(r) for r in cur.fetchall()]


# ══════════════════════════════════════════
# تقدم المستخدم
# ══════════════════════════════════════════

def get_progress(user_id: int) -> Optional[dict]:
    cur = _get_conn().cursor()
    cur.execute("SELECT * FROM user_quran_progress WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def save_progress(user_id: int, ayah_id: int, message_id: int = None):
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO user_quran_progress (user_id, last_ayah_id, message_id)
        VALUES (?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET last_ayah_id=excluded.last_ayah_id,
                                           message_id=excluded.message_id
    """, (user_id, ayah_id, message_id))
    conn.commit()


def reset_progress(user_id: int):
    first = get_first_ayah()
    first_id = first["id"] if first else 1
    save_progress(user_id, first_id, None)


# ══════════════════════════════════════════
# المفضلة
# ══════════════════════════════════════════

def add_favorite(user_id: int, ayah_id: int) -> bool:
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO user_favorites (user_id, ayah_id) VALUES (?,?)",
        (user_id, ayah_id),
    )
    conn.commit()
    return cur.rowcount > 0


def remove_favorite(user_id: int, ayah_id: int) -> bool:
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute(
        "DELETE FROM user_favorites WHERE user_id=? AND ayah_id=?",
        (user_id, ayah_id),
    )
    conn.commit()
    return cur.rowcount > 0


def is_favorite(user_id: int, ayah_id: int) -> bool:
    cur = _get_conn().cursor()
    cur.execute(
        "SELECT 1 FROM user_favorites WHERE user_id=? AND ayah_id=?",
        (user_id, ayah_id),
    )
    return cur.fetchone() is not None


def get_favorites(user_id: int) -> list[dict]:
    cur = _get_conn().cursor()
    cur.execute("""
        SELECT a.*, s.name as sura_name
        FROM user_favorites f
        JOIN ayat a ON f.ayah_id = a.id
        JOIN suras s ON a.sura_id = s.id
        WHERE f.user_id=?
        ORDER BY f.added_at ASC
    """, (user_id,))
    return [dict(r) for r in cur.fetchall()]


def clear_favorites(user_id: int) -> int:
    """يحذف جميع مفضلات المستخدم. يرجع عدد الصفوف المحذوفة."""
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute("DELETE FROM user_favorites WHERE user_id = ?", (user_id,))
    conn.commit()
    return cur.rowcount


# ══════════════════════════════════════════
# تقدم قراءة السور
# ══════════════════════════════════════════

def get_surah_read_progress(user_id: int, surah_id: int) -> int:
    """Returns last read ayah_number for this surah (1 if not started)."""
    cur = _get_conn().cursor()
    cur.execute(
        "SELECT ayah FROM surah_read_progress WHERE user_id=? AND surah_id=?",
        (user_id, surah_id),
    )
    row = cur.fetchone()
    return row[0] if row else 1


def save_surah_read_progress(user_id: int, surah_id: int, ayah_number: int):
    conn = _get_conn()
    conn.execute(
        """INSERT INTO surah_read_progress (user_id, surah_id, ayah)
           VALUES (?,?,?)
           ON CONFLICT(user_id, surah_id) DO UPDATE SET ayah=excluded.ayah""",
        (user_id, surah_id, ayah_number),
    )
    conn.commit()


def get_suras_with_ayat() -> list[dict]:
    """Returns only suras that have at least one ayah."""
    cur = _get_conn().cursor()
    cur.execute("""
        SELECT s.id, s.name, COUNT(a.id) as ayah_count
        FROM suras s
        JOIN ayat a ON a.sura_id = s.id
        GROUP BY s.id
        ORDER BY s.id ASC
    """)
    return [dict(r) for r in cur.fetchall()]


# ══════════════════════════════════════════
# ختمة القرآن
# ══════════════════════════════════════════

TOTAL_QURAN_AYAT = 6236


def get_khatma(user_id: int) -> dict:
    cur = _get_conn().cursor()
    cur.execute("SELECT * FROM khatma_progress WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    return dict(row) if row else {
        "user_id": user_id, "last_surah": 1, "last_ayah": 1,
        "total_read": 0, "updated_at": None,
    }


def update_khatma(user_id: int, surah_id: int, ayah_number: int):
    """
    Increment total_read only if this ayah hasn't been counted today.
    Updates streak and daily log as well.
    Returns True if a new ayah was counted.
    """
    from datetime import date, timedelta
    today = date.today().isoformat()
    conn  = _get_conn()
    cur   = conn.cursor()

    # Get ayah_id for dedup key
    cur.execute(
        "SELECT id FROM ayat WHERE sura_id=? AND ayah_number=?",
        (surah_id, ayah_number),
    )
    row = cur.fetchone()
    if not row:
        return False
    ayah_id = row[0]

    # Dedup check — only count once per ayah per day
    cur.execute(
        "SELECT 1 FROM khatma_counted_ayat WHERE user_id=? AND ayah_id=? AND log_date=?",
        (user_id, ayah_id, today),
    )
    if cur.fetchone():
        # Already counted today — just update last position
        conn.execute(
            """INSERT INTO khatma_progress (user_id, last_surah, last_ayah, total_read, updated_at)
               VALUES (?,?,?,0, datetime('now'))
               ON CONFLICT(user_id) DO UPDATE SET
                   last_surah=excluded.last_surah,
                   last_ayah=excluded.last_ayah,
                   updated_at=excluded.updated_at""",
            (user_id, surah_id, ayah_number),
        )
        conn.commit()
        return False

    # Mark as counted
    conn.execute(
        "INSERT OR IGNORE INTO khatma_counted_ayat (user_id, ayah_id, log_date) VALUES (?,?,?)",
        (user_id, ayah_id, today),
    )

    # Update progress
    conn.execute(
        """INSERT INTO khatma_progress (user_id, last_surah, last_ayah, total_read, updated_at)
           VALUES (?,?,?,1, datetime('now'))
           ON CONFLICT(user_id) DO UPDATE SET
               last_surah=excluded.last_surah,
               last_ayah=excluded.last_ayah,
               total_read=total_read+1,
               updated_at=excluded.updated_at""",
        (user_id, surah_id, ayah_number),
    )

    # Daily log
    conn.execute(
        """INSERT INTO khatma_daily_log (user_id, log_date, count)
           VALUES (?,?,1)
           ON CONFLICT(user_id, log_date) DO UPDATE SET count=count+1""",
        (user_id, today),
    )

    # Streak update — with 7-day grace period
    cur.execute("SELECT current_streak, last_read_date FROM khatma_streak WHERE user_id=?",
                (user_id,))
    streak_row = cur.fetchone()
    yesterday  = (date.today() - timedelta(days=1)).isoformat()
    if streak_row:
        streak, last_date = streak_row[0], streak_row[1]
        if last_date == today:
            new_streak = streak          # already updated today
        elif last_date == yesterday:
            new_streak = streak + 1      # consecutive day
        else:
            # Grace period: if gap <= 7 days, continue streak; else reset
            try:
                from datetime import datetime as _dt
                last_dt = _dt.fromisoformat(last_date)
                today_dt = _dt.fromisoformat(today)
                gap_days = (today_dt - last_dt).days
                new_streak = streak + 1 if gap_days <= 7 else 1
            except Exception:
                new_streak = 1
    else:
        new_streak = 1

    conn.execute(
        """INSERT INTO khatma_streak (user_id, current_streak, last_read_date)
           VALUES (?,?,?)
           ON CONFLICT(user_id) DO UPDATE SET
               current_streak=excluded.current_streak,
               last_read_date=excluded.last_read_date""",
        (user_id, new_streak, today),
    )

    conn.commit()
    return True


def reset_khatma(user_id: int):
    conn = _get_conn()
    conn.execute(
        """INSERT INTO khatma_progress (user_id, last_surah, last_ayah, total_read, updated_at)
           VALUES (?,1,1,0,datetime('now'))
           ON CONFLICT(user_id) DO UPDATE SET
               last_surah=1, last_ayah=1, total_read=0, updated_at=datetime('now')""",
        (user_id,),
    )
    conn.commit()


def get_khatma_goal(user_id: int) -> int:
    cur = _get_conn().cursor()
    cur.execute("SELECT daily_target FROM khatma_goals WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    return row[0] if row else 10


def set_khatma_goal(user_id: int, target: int):
    conn = _get_conn()
    conn.execute(
        """INSERT INTO khatma_goals (user_id, daily_target) VALUES (?,?)
           ON CONFLICT(user_id) DO UPDATE SET daily_target=excluded.daily_target""",
        (user_id, target),
    )
    conn.commit()


def get_daily_avg(user_id: int, days: int = 3) -> int:
    """Returns average ayat read per day over last N days (0 if no data)."""
    from datetime import date, timedelta
    cur   = _get_conn().cursor()
    dates = [(date.today() - timedelta(days=i)).isoformat() for i in range(1, days + 1)]
    placeholders = ",".join("?" * len(dates))
    cur.execute(
        f"SELECT SUM(count) FROM khatma_daily_log WHERE user_id=? AND log_date IN ({placeholders})",
        [user_id] + dates,
    )
    total = cur.fetchone()[0] or 0
    return total // days


def get_streak(user_id: int) -> int:
    cur = _get_conn().cursor()
    cur.execute("SELECT current_streak FROM khatma_streak WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    return row[0] if row else 0


def get_today_count(user_id: int) -> int:
    from datetime import date
    today = date.today().isoformat()
    cur   = _get_conn().cursor()
    cur.execute(
        "SELECT count FROM khatma_daily_log WHERE user_id=? AND log_date=?",
        (user_id, today),
    )
    row = cur.fetchone()
    return row[0] if row else 0


# ── Khatmah reminders ──

_MAX_KH_REMINDERS = 2


def get_khatma_reminders(user_id: int) -> list:
    cur = _get_conn().cursor()
    cur.execute(
        "SELECT * FROM khatma_reminders WHERE user_id=? AND enabled=1 ORDER BY hour, minute",
        (user_id,),
    )
    return [dict(r) for r in cur.fetchall()]


def count_khatma_reminders(user_id: int) -> int:
    cur = _get_conn().cursor()
    cur.execute(
        "SELECT COUNT(*) FROM khatma_reminders WHERE user_id=? AND enabled=1",
        (user_id,),
    )
    return cur.fetchone()[0]


def add_khatma_reminder(user_id: int, hour: int, minute: int,
                        tz_offset: int = 0) -> int:
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO khatma_reminders (user_id, hour, minute, tz_offset) VALUES (?,?,?,?)",
        (user_id, hour, minute, tz_offset),
    )
    conn.commit()
    return cur.lastrowid


def delete_khatma_reminder(reminder_id: int, user_id: int) -> bool:
    conn = _get_conn()
    cur  = conn.cursor()
    cur.execute(
        "DELETE FROM khatma_reminders WHERE id=? AND user_id=?",
        (reminder_id, user_id),
    )
    conn.commit()
    return cur.rowcount > 0


def get_due_khatma_reminders(utc_hour: int, utc_minute: int) -> list:
    cur = _get_conn().cursor()
    cur.execute("SELECT * FROM khatma_reminders WHERE enabled=1")
    due = []
    for r in cur.fetchall():
        r = dict(r)
        local_total = r["hour"] * 60 + r["minute"]
        utc_total   = (local_total - r["tz_offset"]) % (24 * 60)
        if utc_total == utc_hour * 60 + utc_minute:
            due.append(r)
    return due


# ══════════════════════════════════════════
# إنجازات الختمة
# ══════════════════════════════════════════

_ACHIEVEMENTS = {
    "active_reader": {"total": 1000, "streak": None,  "label": "قارئ نشيط 📖"},
    "week_streak":   {"total": None,  "streak": 7,    "label": "أسبوع متواصل 🔥"},
}


def check_new_achievements(user_id: int) -> list[str]:
    """
    Returns list of newly unlocked achievement labels.
    Marks them as seen so they don't fire again.
    """
    k      = get_khatma(user_id)
    streak = get_streak(user_id)
    conn   = _get_conn()
    cur    = conn.cursor()

    # Ensure seen table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS khatma_achievements_seen (
            user_id INTEGER NOT NULL,
            key     TEXT    NOT NULL,
            PRIMARY KEY (user_id, key)
        )
    """)
    conn.commit()

    new_ones = []
    for key, cond in _ACHIEVEMENTS.items():
        # Already seen?
        cur.execute(
            "SELECT 1 FROM khatma_achievements_seen WHERE user_id=? AND key=?",
            (user_id, key),
        )
        if cur.fetchone():
            continue
        # Check condition
        unlocked = False
        if cond["total"] and k["total_read"] >= cond["total"]:
            unlocked = True
        if cond["streak"] and streak >= cond["streak"]:
            unlocked = True
        if unlocked:
            conn.execute(
                "INSERT OR IGNORE INTO khatma_achievements_seen (user_id, key) VALUES (?,?)",
                (user_id, key),
            )
            new_ones.append(cond["label"])

    if new_ones:
        conn.commit()
    return new_ones


def get_best_day(user_id: int) -> int:
    """Returns the highest single-day ayat count ever recorded."""
    cur = _get_conn().cursor()
    cur.execute(
        "SELECT MAX(count) FROM khatma_daily_log WHERE user_id=?",
        (user_id,),
    )
    row = cur.fetchone()
    return row[0] if row and row[0] else 0


def get_days_since_last_read(user_id: int) -> int:
    """Returns number of days since last khatmah activity (0 = today)."""
    from datetime import date, datetime
    cur = _get_conn().cursor()
    cur.execute("SELECT last_read_date FROM khatma_streak WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row or not row[0]:
        return 999   # never read
    try:
        last = datetime.fromisoformat(row[0]).date()
        return (date.today() - last).days
    except Exception:
        return 999
