# database/db_queries/groups_queries.py

from ..connection import get_db_conn
import sqlite3


# ══════════════════════════════════════════
# 🔧 Internal helpers
# ══════════════════════════════════════════

def _get_or_create_group(cursor, tg_group_id: int, group_name: str) -> int:
    """
    Returns the internal groups.id for a Telegram group_id.
    Inserts the group if it doesn't exist yet.
    """
    cursor.execute("SELECT id FROM groups WHERE group_id = ?", (tg_group_id,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        "INSERT INTO groups (group_id, name) VALUES (?, ?)",
        (tg_group_id, group_name or "Unknown")
    )
    return cursor.lastrowid


def get_internal_group_id(tg_group_id: int) -> int | None:
    """Returns groups.id for a Telegram group_id, or None if not found."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM groups WHERE group_id = ?", (tg_group_id,))
    row = cursor.fetchone()
    return row[0] if row else None


# ══════════════════════════════════════════
# 👤 User identity
# ══════════════════════════════════════════

def upsert_user_identity(user_id: int, full_name: str, username: str = None):
    """Ensures user exists in users table and keeps name/username current."""
    conn   = get_db_conn()
    cursor = conn.cursor()

    full_name = (full_name or "").strip() or "Unknown"
    username  = (username  or "").strip() or None

    cursor.execute(
        """
        INSERT INTO users (user_id, name, username)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            name     = excluded.name,
            username = excluded.username
        """,
        (user_id, full_name, username)
    )
    conn.commit()


# ══════════════════════════════════════════
# 👥 Group membership
# ══════════════════════════════════════════

def upsert_group_member(tg_group_id: int, user_id: int, full_name: str,
                        group_name: str, username: str = None):
    """Upserts group + user + member row, increments message count."""
    conn   = get_db_conn()
    cursor = conn.cursor()

    internal_id = _get_or_create_group(cursor, tg_group_id, group_name)
    upsert_user_identity(user_id, full_name, username)

    cursor.execute(
        """
        INSERT INTO group_members (user_id, group_id, messages_count, is_active)
        VALUES (?, ?, 1, 1)
        ON CONFLICT(user_id, group_id)
        DO UPDATE SET
            messages_count = messages_count + 1,
            is_active      = 1
        """,
        (user_id, internal_id)
    )
    conn.commit()


def set_member_active(tg_group_id: int, user_id: int, full_name: str = None,
                      group_name: str = None, username: str = None):
    """Registers member as active (is_active=1)."""
    conn   = get_db_conn()
    cursor = conn.cursor()

    internal_id = _get_or_create_group(cursor, tg_group_id, group_name or "Unknown")
    upsert_user_identity(user_id, full_name or "", username)

    cursor.execute(
        """
        INSERT INTO group_members (user_id, group_id, is_active)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, group_id) DO UPDATE SET is_active = 1
        """,
        (user_id, internal_id)
    )
    conn.commit()


def set_member_inactive(tg_group_id: int, user_id: int):
    """Sets is_active=0 when member leaves or is kicked."""
    internal_id = get_internal_group_id(tg_group_id)
    if not internal_id:
        return
    conn = get_db_conn()
    conn.execute(
        "UPDATE group_members SET is_active = 0 WHERE user_id = ? AND group_id = ?",
        (user_id, internal_id)
    )
    conn.commit()


# ══════════════════════════════════════════
# 📊 Stats
# ══════════════════════════════════════════

def get_group_total_messages(tg_group_id: int) -> int:
    internal_id = get_internal_group_id(tg_group_id)
    if not internal_id:
        return 0
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT SUM(messages_count) FROM group_members WHERE group_id = ?",
        (internal_id,)
    )
    return cursor.fetchone()[0] or 0


def get_group_stats(user_id: int, tg_group_id: int) -> dict:
    internal_id = get_internal_group_id(tg_group_id)
    if not internal_id:
        return {"messages_count": 0, "rank": 1}

    conn = get_db_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT messages_count FROM group_members WHERE user_id = ? AND group_id = ?",
        (user_id, internal_id)
    )
    row = cursor.fetchone()
    messages_count = row["messages_count"] if row else 0

    cursor.execute(
        """
        SELECT COUNT(*) + 1 AS rank
        FROM group_members
        WHERE group_id = ? AND messages_count > (
            SELECT messages_count FROM group_members
            WHERE user_id = ? AND group_id = ?
        )
        """,
        (internal_id, user_id, internal_id)
    )
    row = cursor.fetchone()
    return {"messages_count": messages_count, "rank": row["rank"] if row else 1}
