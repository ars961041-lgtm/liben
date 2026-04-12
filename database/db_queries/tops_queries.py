"""
استعلامات التوب — 6 فئات رئيسية.
كل دالة ترجع list[dict] بمفاتيح: id, name, value
"""
import sqlite3
from database.connection import get_db_conn


# ══════════════════════════════════════════
# 1. 🔥 توب المتفاعلين (عالمي)
# ══════════════════════════════════════════

def get_top_active_users(limit=10) -> list[dict]:
    """مجموع رسائل كل مستخدم عبر جميع المجموعات"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            gm.user_id AS id,
            COALESCE(NULLIF(un.name, ''), 'مجهول') AS name,
            SUM(COALESCE(gm.messages_count, 0)) AS value
        FROM group_members gm
        LEFT JOIN users un ON gm.user_id = un.user_id
        GROUP BY gm.user_id
        ORDER BY value DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


def get_top_active_in_group(chat_id: int, limit=10) -> list[dict]:
    """توب المتفاعلين في مجموعة محددة"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            gm.user_id AS id,
            COALESCE(NULLIF(un.name, ''), 'مجهول') AS name,
            COALESCE(gm.messages_count, 0) AS value
        FROM group_members gm
        JOIN groups g ON g.id = gm.group_id
        LEFT JOIN users un ON gm.user_id = un.user_id
        WHERE g.group_id = ?
        ORDER BY value DESC
        LIMIT ?
    """, (chat_id, limit))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# 2. 🏙 توب المدن بالإنفاق
# ══════════════════════════════════════════

def get_top_spending_cities(limit=10) -> list[dict]:
    """توب المدن بإجمالي الإنفاق (بالسعر الأصلي)"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            c.id,
            c.name,
            COALESCE(cs.total_spent, 0) AS value
        FROM cities c
        LEFT JOIN city_spending cs ON c.id = cs.city_id
        ORDER BY value DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# 3. 🌍 توب الدول بالإنفاق
# ══════════════════════════════════════════

def get_top_spending_countries(limit=10) -> list[dict]:
    """توب الدول بمجموع إنفاق مدنها"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            co.id,
            co.name,
            COALESCE(SUM(cs.total_spent), 0) AS value
        FROM countries co
        LEFT JOIN cities ci ON ci.country_id = co.id
        LEFT JOIN city_spending cs ON cs.city_id = ci.id
        GROUP BY co.id, co.name
        ORDER BY value DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# 4. 🏰 توب التحالفات
# ══════════════════════════════════════════

def get_top_alliances(limit=10) -> list[dict]:
    """توب التحالفات بمجموع نفوذ دولها + عدد الأعضاء"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            a.id,
            a.name,
            COALESCE(SUM(ci.influence_points), 0) +
            COUNT(DISTINCT am.user_id) * 10 AS value,
            COUNT(DISTINCT am.user_id) AS member_count
        FROM alliances a
        LEFT JOIN alliance_members am ON am.alliance_id = a.id
        LEFT JOIN countries co ON co.owner_id = am.user_id
        LEFT JOIN country_influence ci ON ci.country_id = co.id
        GROUP BY a.id, a.name
        ORDER BY value DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# 5. 👥 توب المجموعات
# ══════════════════════════════════════════

def get_top_groups(limit=10) -> list[dict]:
    """توب المجموعات بمجموع رسائل أعضائها"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            g.group_id AS id,
            COALESCE(g.name, 'مجموعة ' || g.group_id) AS name,
            COALESCE(SUM(gm.messages_count), 0) AS value,
            COUNT(DISTINCT gm.user_id) AS member_count
        FROM groups g
        LEFT JOIN group_members gm ON gm.group_id = g.id
        GROUP BY g.id, g.name
        ORDER BY value DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# 6. 🗡 توب الخيانات
# ══════════════════════════════════════════

def get_top_betrayals(limit=10) -> list[dict]:
    """توب اللاعبين بعدد محاولات الانضمام (الخيانة)"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            ac.user_id AS id,
            COALESCE(NULLIF(un.name, ''), 'مجهول') AS name,
            COUNT(*) AS value
        FROM action_cooldowns ac
        LEFT JOIN users un ON ac.user_id = un.user_id
        WHERE ac.action = 'betray'
        GROUP BY ac.user_id
        ORDER BY value DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# مساعدات (تُستخدم في أماكن أخرى)
# ══════════════════════════════════════════

def get_top_richest(limit=10) -> list[dict]:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            ua.user_id AS id,
            COALESCE(NULLIF(un.name, ''), 'مجهول') AS name,
            COALESCE(ua.balance, 0) AS value
        FROM user_accounts ua
        LEFT JOIN users un ON ua.user_id = un.user_id
        ORDER BY ua.balance DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


def get_group_members_stats(chat_id: int, limit=10) -> list[dict]:
    return get_top_active_in_group(chat_id, limit)


def get_group_stats(user_id: int, group_id: int) -> dict:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COALESCE(messages_count, 0)
        FROM group_members WHERE user_id = ? AND group_id = ?
    """, (user_id, group_id))
    row = cursor.fetchone()
    messages_count = row[0] if row else 0
    cursor.execute("""
        SELECT COUNT(*) + 1 FROM group_members
        WHERE group_id = ? AND messages_count > (
            SELECT COALESCE(messages_count, 0)
            FROM group_members WHERE user_id = ? AND group_id = ?
        )
    """, (group_id, user_id, group_id))
    row = cursor.fetchone()
    return {"messages_count": messages_count, "rank": row[0] if row else 1}


# ══════════════════════════════════════════
# 🏙 ترتيبات المدن والدول الجديدة
# ══════════════════════════════════════════

def get_top_cities_by_population(limit=10) -> list[dict]:
    """أكبر المدن سكاناً"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.name, c.population AS value
        FROM cities c
        ORDER BY c.population DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


def get_top_countries_by_population(limit=10) -> list[dict]:
    """أكبر الدول سكاناً (مجموع مدنها)"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT co.id, co.name, COALESCE(SUM(ci.population), 0) AS value
        FROM countries co
        LEFT JOIN cities ci ON ci.country_id = co.id
        GROUP BY co.id, co.name
        ORDER BY value DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


def get_top_cities_by_economy(limit=10) -> list[dict]:
    """أقوى المدن اقتصادياً (بالدخل الساعي)"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.name,
               COALESCE(cb.income_per_hour, 0) AS value
        FROM cities c
        LEFT JOIN city_budget cb ON cb.city_id = c.id
        ORDER BY value DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


def get_top_countries_by_economy(limit=10) -> list[dict]:
    """أقوى الدول اقتصادياً (مجموع دخل مدنها)"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT co.id, co.name,
               COALESCE(SUM(cb.income_per_hour), 0) AS value
        FROM countries co
        LEFT JOIN cities ci ON ci.country_id = co.id
        LEFT JOIN city_budget cb ON cb.city_id = ci.id
        GROUP BY co.id, co.name
        ORDER BY value DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


def get_top_cities_by_xp(limit=10) -> list[dict]:
    """أعلى المدن مستوى (XP)"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.name,
               COALESCE(cx.level, 1) AS level,
               COALESCE(cx.xp, 0) AS value
        FROM cities c
        LEFT JOIN city_xp cx ON cx.city_id = c.id
        ORDER BY value DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


def get_military_ranking(limit=10) -> list[dict]:
    """
    ترتيب عسكري — يُظهر الترتيب فقط، لا القوة الفعلية.
    يستخدم عدد الجنود كمؤشر عام (لا يكشف القوة الحقيقية).
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT co.id, co.name,
               COALESCE(SUM(ct.quantity), 0) AS troop_count
        FROM countries co
        LEFT JOIN cities ci ON ci.country_id = co.id
        LEFT JOIN city_troops ct ON ct.city_id = ci.id
        GROUP BY co.id, co.name
        ORDER BY troop_count DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    # Return rank only — no exact power values
    return [
        {"id": r[0], "name": r[1], "rank": i + 1}
        for i, r in enumerate(rows)
    ]


# ══════════════════════════════════════════
# 🌍 ترتيبات الدول الموسّعة
# ══════════════════════════════════════════

def get_top_countries_by_cities(limit=10) -> list[dict]:
    """أكبر الدول بعدد المدن"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT co.id, co.name, COUNT(ci.id) AS value
        FROM countries co
        LEFT JOIN cities ci ON ci.country_id = co.id
        GROUP BY co.id, co.name
        ORDER BY value DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


def get_top_countries_by_xp(limit=10) -> list[dict]:
    """أعلى الدول مستوى (مجموع XP مدنها)"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT co.id, co.name,
               COALESCE(SUM(cx.xp), 0) AS value,
               COALESCE(AVG(cx.level), 1) AS avg_level
        FROM countries co
        LEFT JOIN cities ci ON ci.country_id = co.id
        LEFT JOIN city_xp cx ON cx.city_id = ci.id
        GROUP BY co.id, co.name
        ORDER BY value DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# 🏰 ترتيبات التحالفات الموسّعة
# ══════════════════════════════════════════

def get_top_alliances_by_members(limit=10) -> list[dict]:
    """أكبر التحالفات بعدد الأعضاء"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.name, COUNT(DISTINCT am.user_id) AS value
        FROM alliances a
        LEFT JOIN alliance_members am ON am.alliance_id = a.id
        GROUP BY a.id, a.name
        ORDER BY value DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


def get_top_alliances_by_economy(limit=10) -> list[dict]:
    """أقوى التحالفات اقتصادياً (مجموع دخل دولها)"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.name,
               COALESCE(SUM(cb.income_per_hour), 0) AS value
        FROM alliances a
        LEFT JOIN alliance_members am ON am.alliance_id = a.id
        LEFT JOIN countries co ON co.owner_id = am.user_id
        LEFT JOIN cities ci ON ci.country_id = co.id
        LEFT JOIN city_budget cb ON cb.city_id = ci.id
        GROUP BY a.id, a.name
        ORDER BY value DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


def get_alliance_military_ranking(limit=10) -> list[dict]:
    """
    ترتيب عسكري للتحالفات — يُظهر الترتيب فقط.
    يستخدم مجموع الجنود كمؤشر (لا يكشف القوة الفعلية).
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.name,
               COALESCE(SUM(ct.quantity), 0) AS troop_count
        FROM alliances a
        LEFT JOIN alliance_members am ON am.alliance_id = a.id
        LEFT JOIN countries co ON co.owner_id = am.user_id
        LEFT JOIN cities ci ON ci.country_id = co.id
        LEFT JOIN city_troops ct ON ct.city_id = ci.id
        GROUP BY a.id, a.name
        ORDER BY troop_count DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    return [{"id": r[0], "name": r[1], "rank": i + 1} for i, r in enumerate(rows)]
