"""
استعلامات ميزات المجموعة — تفعيل/تعطيل الوحدات
"""
from database.connection import get_db_conn
from database.db_schema.groups import FEATURES


def _internal_id(tg_group_id: int) -> int | None:
    """Returns groups.id (internal PK) for a Telegram group_id."""
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute("SELECT id FROM groups WHERE group_id = ?", (tg_group_id,))
    row = cur.fetchone()
    return row[0] if row else None


def get_group_features(tg_group_id: int) -> dict:
    """Returns dict of all feature states for the group (1=on, 0=off)."""
    internal_id = _internal_id(tg_group_id)
    if not internal_id:
        return {k: v for k, v in FEATURES.items()}
    conn = get_db_conn()
    cur  = conn.cursor()
    cols = ", ".join(FEATURES.keys())
    cur.execute(f"SELECT {cols} FROM groups WHERE id = ?", (internal_id,))
    row = cur.fetchone()
    if not row:
        return {k: v for k, v in FEATURES.items()}
    return {k: row[i] for i, k in enumerate(FEATURES.keys())}


def is_feature_enabled(tg_group_id: int, feature: str) -> bool:
    """
    Returns True if the feature is enabled for the group.
    Defaults to FEATURES default if group is not registered.
    """
    if feature not in FEATURES:
        return True
    internal_id = _internal_id(tg_group_id)
    if not internal_id:
        return bool(FEATURES[feature])
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(f"SELECT {feature} FROM groups WHERE id = ?", (internal_id,))
    row = cur.fetchone()
    if not row:
        return bool(FEATURES[feature])
    return bool(row[0])


def set_feature(tg_group_id: int, feature: str, enabled: bool):
    """Updates a single feature flag for the group."""
    if feature not in FEATURES:
        return
    internal_id = _internal_id(tg_group_id)
    if not internal_id:
        return
    conn = get_db_conn()
    conn.execute(
        f"UPDATE groups SET {feature} = ? WHERE id = ?",
        (1 if enabled else 0, internal_id),
    )
    conn.commit()


def toggle_feature(tg_group_id: int, feature: str) -> bool:
    """Toggles a feature and returns the new state."""
    current = is_feature_enabled(tg_group_id, feature)
    set_feature(tg_group_id, feature, not current)
    return not current
