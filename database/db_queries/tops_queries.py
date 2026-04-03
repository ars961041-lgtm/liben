import sqlite3
import time as _time

from database.connection import get_db_conn


# ══════════════════════════════════════════
# 💰 توب الأغنى
# ══════════════════════════════════════════

def get_top_richest(limit=10):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            ua.user_id AS id,
            COALESCE(un.name, 'مجهول') AS name,
            COALESCE(ua.balance, 0) AS value
        FROM user_accounts ua
        LEFT JOIN users_name un ON ua.user_id = un.user_id
        ORDER BY ua.balance DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# 🏙 توب المدن — يجمع من city_assets + city_budget
# ══════════════════════════════════════════

def get_top_cities(limit=10):
    """توب المدن بالميزانية الحالية"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            c.id,
            c.name,
            COALESCE(cb.current_budget, 0) AS value
        FROM cities c
        LEFT JOIN city_budget cb ON c.id = cb.city_id
        ORDER BY value DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


def get_top_cities_by(metric, limit=10):
    """
    توب المدن حسب مقياس محدد.
    يجمع التأثيرات الحقيقية من city_aspects أو city_budget.
    """
    conn = get_db_conn()
    cursor = conn.cursor()

    # مقاييس مبنية على city_aspects (القيم الحقيقية المحسوبة)
    aspect_metrics = {
        "economy":    "economy",
        "health":     "health",
        "education":  "education",
        "infra":      "infrastructure",
        "infrastructure": "infrastructure",
    }

    if metric == "population":
        cursor.execute("""
            SELECT c.id, c.name, COALESCE(c.population, 0) AS value
            FROM cities c
            ORDER BY value DESC LIMIT ?
        """, (limit,))
    elif metric in aspect_metrics:
        aspect_type = aspect_metrics[metric]
        cursor.execute("""
            SELECT c.id, c.name,
                   COALESCE(ca.value, 0) AS value
            FROM cities c
            LEFT JOIN city_aspects ca
                ON c.id = ca.city_id AND ca.aspect_type = ?
            ORDER BY value DESC LIMIT ?
        """, (aspect_type, limit))
    else:
        # fallback: ميزانية المدينة
        cursor.execute("""
            SELECT c.id, c.name, COALESCE(cb.current_budget, 0) AS value
            FROM cities c
            LEFT JOIN city_budget cb ON c.id = cb.city_id
            ORDER BY value DESC LIMIT ?
        """, (limit,))

    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# 🌍 توب الدول — يجمع من مدن الدولة
# ══════════════════════════════════════════

def get_top_countries(limit=10):
    """توب الدول بمجموع إحصائيات مدنها"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            co.id,
            co.name,
            COALESCE(SUM(
                COALESCE(ci.economy_score, 0) +
                COALESCE(ci.health_level, 0) +
                COALESCE(ci.education_level, 0) +
                COALESCE(ci.military_power, 0) +
                COALESCE(ci.infrastructure_level, 0)
            ), 0) AS value
        FROM countries co
        LEFT JOIN cities ci ON ci.country_id = co.id
        GROUP BY co.id, co.name
        ORDER BY value DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


def get_top_countries_by(metric, limit=10):
    """توب الدول حسب مقياس محدد — يجمع من مدن الدولة"""
    conn = get_db_conn()
    cursor = conn.cursor()

    # خريطة المقاييس إلى أعمدة جدول cities
    column_map = {
        "economy":    "COALESCE(ci.economy_score, 0)",
        "health":     "COALESCE(ci.health_level, 0)",
        "education":  "COALESCE(ci.education_level, 0)",
        "military":   "COALESCE(ci.military_power, 0)",
        "infra":      "COALESCE(ci.infrastructure_level, 0)",
        "infrastructure": "COALESCE(ci.infrastructure_level, 0)",
    }
    col = column_map.get(metric, "COALESCE(ci.economy_score, 0)")

    cursor.execute(f"""
        SELECT
            co.id,
            co.name,
            COALESCE(SUM({col}), 0) AS value
        FROM countries co
        LEFT JOIN cities ci ON ci.country_id = co.id
        GROUP BY co.id, co.name
        ORDER BY value DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# 🏰 توب التحالفات
# ══════════════════════════════════════════

def get_top_alliances_db(limit=10):
    """توب التحالفات بالقوة المحسوبة"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            a.id,
            a.name,
            COALESCE(a.power, 0) AS value,
            (SELECT COUNT(*) FROM alliance_members am WHERE am.alliance_id = a.id) AS member_count
        FROM alliances a
        ORDER BY a.power DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# 👥 توب المتفاعلين
# ══════════════════════════════════════════

def get_group_members_stats(chat_id, limit=10):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            gm.user_id,
            COALESCE(un.name, 'مجهول') AS name,
            COALESCE(gm.messages_count, 0) AS messages_count
        FROM group_members gm
        LEFT JOIN users_name un ON gm.user_id = un.user_id
        WHERE gm.group_id = ?
        ORDER BY gm.messages_count DESC
        LIMIT ?
    """, (chat_id, limit))
    return [dict(r) for r in cursor.fetchall()]


def get_global_top_activity(limit=10):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            gm.user_id AS id,
            COALESCE(un.name, 'مجهول') AS name,
            SUM(COALESCE(gm.messages_count, 0)) AS value
        FROM group_members gm
        LEFT JOIN users_name un ON gm.user_id = un.user_id
        GROUP BY gm.user_id
        ORDER BY value DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# 📊 ترتيب المستخدم في المجموعة
# ══════════════════════════════════════════

def get_group_stats(user_id, group_id):
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(messages_count, 0)
        FROM group_members
        WHERE user_id = ? AND group_id = ?
    """, (user_id, group_id))
    row = cursor.fetchone()
    messages_count = row[0] if row else 0

    cursor.execute("""
        SELECT COUNT(*) + 1 AS rank
        FROM group_members
        WHERE group_id = ? AND messages_count > (
            SELECT COALESCE(messages_count, 0)
            FROM group_members
            WHERE user_id = ? AND group_id = ?
        )
    """, (group_id, user_id, group_id))
    row = cursor.fetchone()
    rank = row[0] if row else 1

    return {"messages_count": messages_count, "rank": rank}


# ══════════════════════════════════════════
# 🏆 توب السمعة
# ══════════════════════════════════════════

def get_top_reputation(limit=10):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            pr.user_id AS id,
            COALESCE(un.name, 'مجهول') AS name,
            pr.loyalty_score AS value,
            pr.reputation_title
        FROM player_reputation pr
        LEFT JOIN users_name un ON pr.user_id = un.user_id
        ORDER BY pr.loyalty_score DESC
        LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]