"""
نظام الإدارة المركزي — ثوابت البوت، أدوار المطورين، الكتم العالمي
"""
import time
from database.connection import get_db_conn
from core.config import developers_id as _DEFAULT_DEVS

# ══════════════════════════════════════════
# 🔧 ثوابت البوت
# ══════════════════════════════════════════

_CONST_CACHE: dict[str, str] = {}
_CACHE_TS: float = 0
_CACHE_TTL: float = 60.0   # تحديث الكاش كل دقيقة


def _load_constants():
    global _CONST_CACHE, _CACHE_TS
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT name, value FROM bot_constants")
        _CONST_CACHE = {r[0]: r[1] for r in cursor.fetchall()}
        _CACHE_TS = time.time()
    except Exception:
        pass


def get_const(name: str, default=None):
    """يجلب ثابتاً من الكاش أو قاعدة البيانات"""
    if time.time() - _CACHE_TS > _CACHE_TTL:
        _load_constants()
    val = _CONST_CACHE.get(name)
    if val is None:
        return default
    return val


def get_const_int(name: str, default: int = 0) -> int:
    try:
        return int(get_const(name, default))
    except (ValueError, TypeError):
        return default


def get_const_float(name: str, default: float = 0.0) -> float:
    try:
        return float(get_const(name, default))
    except (ValueError, TypeError):
        return default


def set_const(name: str, value: str) -> bool:
    """يُحدّث ثابتاً في قاعدة البيانات ويُبطل الكاش"""
    global _CACHE_TS
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE bot_constants SET value = ?, updated_at = ?
            WHERE name = ?
        """, (str(value), int(time.time()), name))
        conn.commit()
        _CACHE_TS = 0   # إبطال الكاش
        return cursor.rowcount > 0
    except Exception:
        return False


def get_all_constants() -> list:
    """يرجع كل الثوابت للعرض"""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT name, value, description FROM bot_constants ORDER BY name")
        return [dict(r) for r in cursor.fetchall()]
    except Exception:
        return []


# ══════════════════════════════════════════
# 👨‍💻 أدوار المطورين
# ══════════════════════════════════════════

def is_primary_dev(user_id: int) -> bool:
    """يتحقق إذا كان المستخدم مطوراً أساسياً"""
    if user_id in _DEFAULT_DEVS:
        return True
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role FROM bot_developers WHERE user_id = ? AND role = 'primary'
        """, (user_id,))
        return cursor.fetchone() is not None
    except Exception:
        return False


def is_secondary_dev(user_id: int) -> bool:
    """يتحقق إذا كان المستخدم مطوراً ثانوياً"""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role FROM bot_developers WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        return row is not None and row[0] == "secondary"
    except Exception:
        return False


def is_any_dev(user_id: int) -> bool:
    """يتحقق إذا كان المستخدم أي نوع من المطورين"""
    return is_primary_dev(user_id) or is_secondary_dev(user_id)


def get_all_developers() -> list:
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, role, added_at FROM bot_developers ORDER BY role, added_at")
        return [dict(r) for r in cursor.fetchall()]
    except Exception:
        return []


def add_developer(user_id: int, role: str = "secondary") -> bool:
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO bot_developers (user_id, role)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET role = ?
        """, (user_id, role, role))
        conn.commit()
        return True
    except Exception:
        return False


def remove_developer(user_id: int) -> bool:
    if user_id in _DEFAULT_DEVS:
        return False   # لا يمكن حذف المطور الأساسي الافتراضي
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bot_developers WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        return False


def promote_developer(user_id: int) -> bool:
    """ترقية من ثانوي إلى أساسي"""
    return add_developer(user_id, "primary")


def demote_developer(user_id: int) -> bool:
    """تخفيض من أساسي إلى ثانوي"""
    if user_id in _DEFAULT_DEVS:
        return False
    return add_developer(user_id, "secondary")


# ══════════════════════════════════════════
# 🔇 نظام الكتم
# ══════════════════════════════════════════

def is_globally_muted(user_id: int) -> bool:
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM global_mutes WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None
    except Exception:
        return False


def is_group_muted(user_id: int, group_id: int) -> bool:
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id FROM group_mutes WHERE user_id = ? AND group_id = ?
        """, (user_id, group_id))
        return cursor.fetchone() is not None
    except Exception:
        return False


def is_muted_anywhere(user_id: int, group_id: int = None) -> bool:
    """يتحقق من الكتم العالمي أو في مجموعة محددة"""
    if is_globally_muted(user_id):
        return True
    if group_id and is_group_muted(user_id, group_id):
        return True
    return False


def global_mute(user_id: int, muted_by: int, reason: str = "") -> bool:
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO global_mutes (user_id, reason, muted_by)
            VALUES (?, ?, ?)
        """, (user_id, reason, muted_by))
        conn.commit()
        return True
    except Exception:
        return False


def global_unmute(user_id: int) -> bool:
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM global_mutes WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        return False


def group_mute(user_id: int, group_id: int, muted_by: int, reason: str = "") -> bool:
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO group_mutes (user_id, group_id, reason, muted_by)
            VALUES (?, ?, ?, ?)
        """, (user_id, group_id, reason, muted_by))
        conn.commit()
        return True
    except Exception:
        return False


def group_unmute(user_id: int, group_id: int) -> bool:
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM group_mutes WHERE user_id = ? AND group_id = ?",
                       (user_id, group_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        return False


def get_global_mutes() -> list:
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM global_mutes ORDER BY muted_at DESC")
        return [dict(r) for r in cursor.fetchall()]
    except Exception:
        return []


def get_group_mutes(group_id: int) -> list:
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM group_mutes WHERE group_id = ? ORDER BY muted_at DESC",
                       (group_id,))
        return [dict(r) for r in cursor.fetchall()]
    except Exception:
        return []
