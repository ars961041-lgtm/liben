"""
ذاكرة البوت — تتبع حالة المستخدم في الذاكرة مع كتابة اختيارية للـ DB
"""
import time
import threading
from typing import Any

# ══════════════════════════════════════════
# 🧠 هيكل الذاكرة
# ══════════════════════════════════════════

# { user_id: { key: value, ... } }
_MEMORY: dict[int, dict[str, Any]] = {}
_LOCK = threading.Lock()

# مدة انتهاء الصلاحية الافتراضية (ثانية) — 6 ساعات
_DEFAULT_TTL = 6 * 3600

# ══════════════════════════════════════════
# 📝 العمليات الأساسية
# ══════════════════════════════════════════

def remember(user_id: int, key: str, value: Any):
    """يحفظ قيمة في ذاكرة المستخدم"""
    with _LOCK:
        if user_id not in _MEMORY:
            _MEMORY[user_id] = {}
        _MEMORY[user_id][key] = value
        _MEMORY[user_id]["_last_active"] = int(time.time())


def recall(user_id: int, key: str, default=None) -> Any:
    """يسترجع قيمة من ذاكرة المستخدم"""
    with _LOCK:
        return _MEMORY.get(user_id, {}).get(key, default)


def forget(user_id: int, key: str = None):
    """يحذف مفتاحاً أو كل ذاكرة المستخدم"""
    with _LOCK:
        if user_id not in _MEMORY:
            return
        if key:
            _MEMORY[user_id].pop(key, None)
        else:
            _MEMORY.pop(user_id, None)


def get_all(user_id: int) -> dict:
    """يرجع كل ذاكرة المستخدم"""
    with _LOCK:
        return dict(_MEMORY.get(user_id, {}))


# ══════════════════════════════════════════
# 🎯 مفاتيح مُعرَّفة مسبقاً
# ══════════════════════════════════════════

def set_last_command(user_id: int, command: str):
    remember(user_id, "last_command", command)
    remember(user_id, "last_command_time", int(time.time()))


def get_last_command(user_id: int) -> str:
    return recall(user_id, "last_command", "")


def set_last_interaction(user_id: int, context: str):
    remember(user_id, "last_interaction", context)
    remember(user_id, "last_interaction_time", int(time.time()))


def get_last_interaction(user_id: int) -> str:
    return recall(user_id, "last_interaction", "")


def increment_daily_reports(user_id: int) -> int:
    """يزيد عداد التقارير اليومية ويرجع القيمة الجديدة"""
    today = time.strftime("%Y-%m-%d")
    key   = f"daily_reports_{today}"
    current = recall(user_id, key, 0)
    new_val = current + 1
    remember(user_id, key, new_val)
    return new_val


def get_daily_reports(user_id: int) -> int:
    today = time.strftime("%Y-%m-%d")
    return recall(user_id, f"daily_reports_{today}", 0)


def mark_waiting_for(user_id: int, context: str):
    """يُسجّل أن البوت ينتظر رداً من هذا المستخدم"""
    remember(user_id, "waiting_for", context)


def clear_waiting(user_id: int):
    forget(user_id, "waiting_for")


def is_waiting_for(user_id: int, context: str = None) -> bool:
    val = recall(user_id, "waiting_for")
    if context:
        return val == context
    return val is not None


def set_active_battle(user_id: int, battle_id: int):
    remember(user_id, "active_battle", battle_id)


def get_active_battle(user_id: int) -> int:
    return recall(user_id, "active_battle", 0)


def clear_active_battle(user_id: int):
    forget(user_id, "active_battle")


# ══════════════════════════════════════════
# 🧹 تنظيف دوري للذاكرة القديمة
# ══════════════════════════════════════════

def _cleanup_loop():
    while True:
        time.sleep(3600)  # كل ساعة
        now = int(time.time())
        with _LOCK:
            expired = [
                uid for uid, data in _MEMORY.items()
                if now - data.get("_last_active", 0) > _DEFAULT_TTL
            ]
            for uid in expired:
                del _MEMORY[uid]
        if expired:
            print(f"[Memory] تم تنظيف {len(expired)} مستخدم غير نشط")


threading.Thread(target=_cleanup_loop, daemon=True).start()


# ══════════════════════════════════════════
# 💾 كتابة اختيارية للـ DB (للبيانات الحرجة)
# ══════════════════════════════════════════

def persist_to_db(user_id: int, key: str, value: str):
    """يحفظ بيانات حرجة في قاعدة البيانات"""
    try:
        from database.connection import get_db_conn
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_memory (
                user_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                updated_at INTEGER DEFAULT (strftime('%s','now')),
                PRIMARY KEY (user_id, key)
            )
        """)
        cursor.execute("""
            INSERT INTO user_memory (user_id, key, value, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, key) DO UPDATE SET value = ?, updated_at = ?
        """, (user_id, key, str(value), int(time.time()), str(value), int(time.time())))
        conn.commit()
    except Exception as e:
        print(f"[Memory] persist_to_db error: {e}")


def load_from_db(user_id: int, key: str, default=None):
    """يجلب بيانات من قاعدة البيانات"""
    try:
        from database.connection import get_db_conn
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT value FROM user_memory WHERE user_id = ? AND key = ?
        """, (user_id, key))
        row = cursor.fetchone()
        return row[0] if row else default
    except Exception:
        return default
