"""
database/db_queries/whispers_queries.py

جميع استعلامات قاعدة البيانات الخاصة بنظام الهمسات الخاصة.
"""

import time
from ..connection import get_db_conn
from .groups_queries import get_internal_group_id

# ══════════════════════════════════════════
# إدراج وقراءة
# ══════════════════════════════════════════

def save_whisper(from_user: int, to_user: int | None, tg_group_id: int,
                 message: str, reply_to: int = None) -> int | None:
    """
    يحفظ همسة جديدة ويرجع id الصف المُدرَج.
    to_user=None  → همسة عامة (@all) — صف واحد فقط في DB.
    reply_to      → id الهمسة الأصلية إذا كانت رداً.
    """
    conn   = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO whispers (from_user, to_user, group_id, message, created_at, reply_to)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (from_user, to_user, tg_group_id, message, int(time.time()), reply_to)
    )
    conn.commit()
    return cursor.lastrowid


def get_whisper(whisper_id: int) -> dict | None:
    """
    يجلب همسة بـ id مع بيانات المُرسِل.
    to_user قد يكون NULL (همسة @all) — يستخدم LEFT JOIN.
    """
    conn   = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT w.id, w.from_user, w.to_user, w.group_id,
               w.message, w.created_at, w.is_read, w.reply_to,
               u_from.name AS from_name, u_from.username AS from_username,
               u_to.name   AS to_name,   u_to.username   AS to_username
        FROM whispers w
        JOIN      users u_from ON u_from.user_id = w.from_user
        LEFT JOIN users u_to   ON u_to.user_id   = w.to_user
        WHERE w.id = ?
        """,
        (whisper_id,)
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def mark_whisper_read(whisper_id: int):
    """يضع is_read=1 على الهمسة."""
    conn = get_db_conn()
    conn.execute("UPDATE whispers SET is_read = 1 WHERE id = ?", (whisper_id,))
    conn.commit()


# ══════════════════════════════════════════
# التحقق من العضوية
# ══════════════════════════════════════════

def get_active_members(tg_group_id: int, limit: int = 50) -> list[dict]:
    """
    يرجع قائمة بالأعضاء النشطين في المجموعة (حد أقصى 50 لـ @all).
    كل عنصر: {user_id, name, username}
    """
    internal_id = get_internal_group_id(tg_group_id)
    if not internal_id:
        return []
    conn   = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT u.user_id, u.name, u.username
        FROM group_members gm
        JOIN users u ON u.user_id = gm.user_id
        WHERE gm.group_id = ?
          AND gm.is_active = 1
          AND gm.is_banned = 0
          AND gm.is_restricted = 0
        ORDER BY gm.messages_count DESC
        LIMIT ?
        """,
        (internal_id, limit)
    )
    return [dict(r) for r in cursor.fetchall()]


def is_active_member(user_id: int, tg_group_id: int) -> bool:
    """يتحقق إذا كان المستخدم عضواً نشطاً في المجموعة."""
    internal_id = get_internal_group_id(tg_group_id)
    if not internal_id:
        return False
    conn   = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM group_members WHERE user_id = ? AND group_id = ? AND is_active = 1",
        (user_id, internal_id)
    )
    return cursor.fetchone() is not None


def get_user_by_username(username: str, tg_group_id: int) -> dict | None:
    """
    يبحث عن مستخدم بـ username داخل أعضاء المجموعة النشطين.
    يرجع {user_id, name, username} أو None.
    """
    internal_id = get_internal_group_id(tg_group_id)
    if not internal_id:
        return None
    clean = username.lstrip("@").lower()
    conn   = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT u.user_id, u.name, u.username
        FROM group_members gm
        JOIN users u ON u.user_id = gm.user_id
        WHERE gm.group_id = ? AND gm.is_active = 1
          AND LOWER(u.username) = ?
        """,
        (internal_id, clean)
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def get_user_by_id_in_group(user_id: int, tg_group_id: int) -> dict | None:
    """يبحث عن مستخدم بـ user_id داخل أعضاء المجموعة النشطين."""
    internal_id = get_internal_group_id(tg_group_id)
    if not internal_id:
        return None
    conn   = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT u.user_id, u.name, u.username
        FROM group_members gm
        JOIN users u ON u.user_id = gm.user_id
        WHERE gm.group_id = ? AND gm.is_active = 1 AND u.user_id = ?
        """,
        (internal_id, user_id)
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def increment_whisper_sender_count(user_id: int, tg_group_id: int):
    """يزيد messages_count للمُرسِل في group_members (تتبع النشاط)."""
    internal_id = get_internal_group_id(tg_group_id)
    if not internal_id:
        return
    conn = get_db_conn()
    conn.execute(
        """
        UPDATE group_members
        SET messages_count = messages_count + 1
        WHERE user_id = ? AND group_id = ?
        """,
        (user_id, internal_id)
    )
    conn.commit()


# ══════════════════════════════════════════
# تنظيف تلقائي
# ══════════════════════════════════════════

def delete_old_whispers(days: int = 3):
    """يحذف الهمسات غير المقروءة الأقدم من `days` أيام."""
    cutoff = int(time.time()) - (days * 86400)
    conn   = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM whispers WHERE created_at < ? AND is_read = 0",
        (cutoff,)
    )
    deleted = cursor.rowcount
    conn.commit()
    if deleted:
        print(f"🗑️ [whispers] حُذفت {deleted} همسة منتهية الصلاحية (غير مقروءة).")


def delete_read_whispers(days: int = 1):
    """يحذف الهمسات المقروءة الأقدم من `days` يوم."""
    cutoff = int(time.time()) - (days * 86400)
    conn   = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM whispers WHERE created_at < ? AND is_read = 1",
        (cutoff,)
    )
    deleted = cursor.rowcount
    conn.commit()
    if deleted:
        print(f"🗑️ [whispers] حُذفت {deleted} همسة مقروءة منتهية الصلاحية.")
