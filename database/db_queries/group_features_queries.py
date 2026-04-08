"""
استعلامات ميزات المجموعة — تفعيل/تعطيل الوحدات
"""
from database.connection import get_db_conn
from database.db_schema.groups import FEATURES


def get_group_features(group_id: int) -> dict:
    """يرجع dict بحالة كل ميزة للمجموعة (1=مفعّل، 0=معطّل)."""
    conn = get_db_conn()
    cur  = conn.cursor()
    cols = ", ".join(FEATURES.keys())
    cur.execute(f"SELECT {cols} FROM groups WHERE id=?", (group_id,))
    row = cur.fetchone()
    if not row:
        return {k: v for k, v in FEATURES.items()}
    return {k: row[i] for i, k in enumerate(FEATURES.keys())}


def is_feature_enabled(group_id: int, feature: str) -> bool:
    """
    يتحقق إذا كانت الميزة مفعّلة في المجموعة.
    يرجع True افتراضياً إذا لم تكن المجموعة مسجّلة.
    """
    if feature not in FEATURES:
        return True
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute(f"SELECT {feature} FROM groups WHERE id=?", (group_id,))
    row = cur.fetchone()
    if not row:
        return bool(FEATURES[feature])
    return bool(row[0])


def set_feature(group_id: int, feature: str, enabled: bool):
    """يحدّث حالة ميزة واحدة للمجموعة."""
    if feature not in FEATURES:
        return
    conn = get_db_conn()
    conn.execute(
        f"UPDATE groups SET {feature}=? WHERE id=?",
        (1 if enabled else 0, group_id),
    )
    conn.commit()


def toggle_feature(group_id: int, feature: str) -> bool:
    """يعكس حالة الميزة ويرجع الحالة الجديدة."""
    current = is_feature_enabled(group_id, feature)
    set_feature(group_id, feature, not current)
    return not current
