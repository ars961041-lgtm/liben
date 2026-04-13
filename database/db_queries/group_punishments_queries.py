# database/db_queries/group_punishments_queries.py

from database.connection import get_db_conn, db_write
from database.db_queries.groups_queries import get_internal_group_id

ALLOWED_FIELDS = {"is_muted", "is_banned", "is_restricted"}


def _resolve(tg_group_id: int) -> int | None:
    return get_internal_group_id(tg_group_id)


def set_user_status(user_id: int, tg_group_id: int, field: str, value: int):
    if field not in ALLOWED_FIELDS:
        raise ValueError("حقل غير صالح")
    internal_id = _resolve(tg_group_id)
    if not internal_id:
        return

    def _write():
        conn = get_db_conn()
        conn.execute(
            f"UPDATE group_members SET {field} = ? WHERE user_id = ? AND group_id = ?",
            (value, user_id, internal_id)
        )
        conn.commit()

    db_write(_write)


def is_user_status(user_id: int, tg_group_id: int, field: str) -> bool:
    if field not in ALLOWED_FIELDS:
        raise ValueError("حقل غير صالح")
    internal_id = _resolve(tg_group_id)
    if not internal_id:
        return False
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        f"SELECT {field} FROM group_members WHERE user_id = ? AND group_id = ?",
        (user_id, internal_id)
    )
    result = cur.fetchone()
    return bool(result and result[0] == 1)


def get_users_by_status(tg_group_id: int, field: str) -> list:
    if field not in ALLOWED_FIELDS:
        raise ValueError("حقل غير صالح")
    internal_id = _resolve(tg_group_id)
    if not internal_id:
        return []
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        f"SELECT user_id FROM group_members WHERE group_id = ? AND {field} = 1",
        (internal_id,)
    )
    return cur.fetchall()


def log_punishment(tg_group_id: int, user_id: int, action_type: int,
                   executor_id: int, reverse: bool = False):
    if reverse:
        action_type += 3
    internal_id = _resolve(tg_group_id)
    if not internal_id:
        return

    def _write():
        conn = get_db_conn()
        conn.execute(
            "INSERT INTO group_punishment_log (group_id, user_id, action_type, executor_id) "
            "VALUES (?, ?, ?, ?)",
            (internal_id, user_id, action_type, executor_id)
        )
        conn.commit()

    db_write(_write)


def get_user_punishments(tg_group_id: int, user_id: int) -> list:
    internal_id = _resolve(tg_group_id)
    if not internal_id:
        return []
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        "SELECT user_id, action_type, executor_id, timestamp "
        "FROM group_punishment_log WHERE group_id = ? AND user_id = ? "
        "ORDER BY timestamp DESC",
        (internal_id, user_id)
    )
    return cur.fetchall()


def get_group_punishments(tg_group_id: int) -> list:
    internal_id = _resolve(tg_group_id)
    if not internal_id:
        return []
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        "SELECT user_id, action_type, executor_id, timestamp "
        "FROM group_punishment_log WHERE group_id = ? ORDER BY timestamp DESC",
        (internal_id,)
    )
    return cur.fetchall()


def get_last_punishment(tg_group_id: int, user_id: int, action_type: int):
    internal_id = _resolve(tg_group_id)
    if not internal_id:
        return None
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(
        "SELECT user_id, action_type, executor_id, timestamp "
        "FROM group_punishment_log "
        "WHERE group_id = ? AND user_id = ? AND action_type = ? "
        "ORDER BY timestamp DESC LIMIT 1",
        (internal_id, user_id, action_type)
    )
    return cur.fetchone()


def delete_group_punishments(tg_group_id: int):
    internal_id = _resolve(tg_group_id)
    if not internal_id:
        return

    def _write():
        conn = get_db_conn()
        conn.execute(
            "DELETE FROM group_punishment_log WHERE group_id = ?", (internal_id,)
        )
        conn.commit()

    db_write(_write)
