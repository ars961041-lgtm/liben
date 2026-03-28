from database.connection import get_db_conn

# الأعمدة المسموحة (للحماية)
ALLOWED_FIELDS = {"is_muted", "is_banned", "is_restricted"}

# ---------------------------------- SET (عام)

def set_user_status(user_id, group_id, field, value):
    if field not in ALLOWED_FIELDS:
        raise ValueError("Invalid field")

    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute(f"""
    UPDATE group_members
    SET {field} = ?
    WHERE user_id = ? AND group_id = ?
    """, (value, user_id, group_id))

    conn.commit()


# ---------------------------------- IS (عام)
def is_user_status(user_id, group_id, field):
    if field not in ALLOWED_FIELDS:
        raise ValueError("Invalid field")

    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute(f"""
    SELECT {field}
    FROM group_members
    WHERE user_id = ? AND group_id = ?
    """, (user_id, group_id))

    result = cursor.fetchone()
    return result and result[0] == 1


# ---------------------------------- GET (عام)

def get_users_by_status(group_id, field):
    if field not in ALLOWED_FIELDS:
        raise ValueError("Invalid field")

    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute(f"""
    SELECT user_id
    FROM group_members
    WHERE group_id = ? AND {field} = 1
    """, (group_id,))

    return cursor.fetchall()