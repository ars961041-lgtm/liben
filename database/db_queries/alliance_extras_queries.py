"""
استعلامات نظام الزخم الحربي والقائمة السوداء
Alliance War Momentum + Blacklist — DB Queries
"""
import time
from ..connection import get_db_conn

# ── ثوابت الزخم ──
MOMENTUM_BONUS_PER_WIN = 0.02   # +2% قوة لكل انتصار
MOMENTUM_MAX_BONUS     = 0.10   # سقف +10%
MOMENTUM_MAX_STREAK    = 5      # أقصى سلسلة تُحسب (5 انتصارات)


# ══════════════════════════════════════════
# ⚡ الزخم الحربي
# ══════════════════════════════════════════

def _ensure_momentum(alliance_id: int, cursor=None):
    """يُنشئ صف الزخم إذا لم يكن موجوداً."""
    own_conn = cursor is None
    if own_conn:
        conn = get_db_conn()
        cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO alliance_war_momentum (alliance_id) VALUES (?)
    """, (alliance_id,))
    if own_conn:
        conn.commit()


def get_momentum(alliance_id: int) -> dict:
    """يُعيد بيانات الزخم الحالية للتحالف."""
    conn = get_db_conn()
    cursor = conn.cursor()
    _ensure_momentum(alliance_id, cursor)
    conn.commit()
    cursor.execute(
        "SELECT win_streak, power_bonus FROM alliance_war_momentum WHERE alliance_id=?",
        (alliance_id,)
    )
    row = cursor.fetchone()
    return {"win_streak": row[0], "power_bonus": row[1]} if row else {"win_streak": 0, "power_bonus": 0.0}


def record_war_win(alliance_id: int):
    """
    يُسجّل انتصاراً ويُحدّث سلسلة الانتصارات والبونص.
    win_streak  = min(current + 1, MOMENTUM_MAX_STREAK)
    power_bonus = min(win_streak × MOMENTUM_BONUS_PER_WIN, MOMENTUM_MAX_BONUS)
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        _ensure_momentum(alliance_id, cursor)

        cursor.execute(
            "SELECT win_streak FROM alliance_war_momentum WHERE alliance_id=?",
            (alliance_id,)
        )
        row = cursor.fetchone()
        current_streak = int(row[0]) if row else 0

        new_streak = min(current_streak + 1, MOMENTUM_MAX_STREAK)
        new_bonus  = round(min(new_streak * MOMENTUM_BONUS_PER_WIN, MOMENTUM_MAX_BONUS), 4)

        cursor.execute("""
            UPDATE alliance_war_momentum
            SET win_streak=?, power_bonus=?, last_updated=?
            WHERE alliance_id=?
        """, (new_streak, new_bonus, int(time.time()), alliance_id))
        conn.commit()
        return new_streak, new_bonus
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise


def record_war_loss(alliance_id: int):
    """
    يُسجّل خسارة — يُعيد تعيين السلسلة والبونص إلى صفر.
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        _ensure_momentum(alliance_id, cursor)
        cursor.execute("""
            UPDATE alliance_war_momentum
            SET win_streak=0, power_bonus=0.0, last_updated=?
            WHERE alliance_id=?
        """, (int(time.time()), alliance_id))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise


def get_momentum_bonus(alliance_id: int) -> float:
    """
    يُعيد مضاعف الزخم الحالي للتحالف.
    يُستخدم في حساب القوة: power × (1 + bonus)
    """
    m = get_momentum(alliance_id)
    return float(m.get("power_bonus", 0.0))


# ══════════════════════════════════════════
# 🚫 القائمة السوداء
# ══════════════════════════════════════════

def blacklist_country(alliance_id: int, country_id: int,
                      banned_by: int, reason: str = "") -> tuple[bool, str]:
    """يُضيف دولة للقائمة السوداء. يُعيد (success, msg)."""
    conn = get_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO alliance_blacklist (alliance_id, country_id, banned_by, reason)
            VALUES (?,?,?,?)
        """, (alliance_id, country_id, banned_by, reason))
        conn.commit()
        return True, "✅ تمت إضافة الدولة للقائمة السوداء."
    except Exception as e:
        if "UNIQUE" in str(e):
            return False, "❌ الدولة موجودة بالفعل في القائمة السوداء."
        raise


def unblacklist_country(alliance_id: int, country_id: int) -> tuple[bool, str]:
    """يُزيل دولة من القائمة السوداء."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM alliance_blacklist
        WHERE alliance_id=? AND country_id=?
    """, (alliance_id, country_id))
    conn.commit()
    if cursor.rowcount:
        return True, "✅ تمت إزالة الدولة من القائمة السوداء."
    return False, "❌ الدولة ليست في القائمة السوداء."


def is_country_blacklisted(alliance_id: int, country_id: int) -> bool:
    """يتحقق إذا كانت الدولة محظورة من التحالف."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM alliance_blacklist
        WHERE alliance_id=? AND country_id=?
    """, (alliance_id, country_id))
    return cursor.fetchone() is not None


def get_blacklist(alliance_id: int) -> list[dict]:
    """يُعيد قائمة الدول المحظورة مع التفاصيل."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ab.*, c.name as country_name
        FROM alliance_blacklist ab
        JOIN countries c ON ab.country_id = c.id
        WHERE ab.alliance_id=?
        ORDER BY ab.created_at DESC
    """, (alliance_id,))
    return [dict(r) for r in cursor.fetchall()]


def get_blacklisted_alliances_for_country(country_id: int) -> list[int]:
    """يُعيد قائمة معرّفات التحالفات التي حظرت هذه الدولة."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT alliance_id FROM alliance_blacklist WHERE country_id=?",
        (country_id,)
    )
    return [row[0] for row in cursor.fetchall()]
