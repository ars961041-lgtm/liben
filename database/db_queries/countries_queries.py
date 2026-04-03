# database/db_queries/countries_queries.py

import sqlite3
from ..connection import get_db_conn
from utils.helpers import send_error

# -------------------------
# تحويل صف إلى dict
# -------------------------
def dict_from_row(cursor, row):
    return {description[0]: row[idx] for idx, description in enumerate(cursor.description)}

# -------------------------
# الحصول على كل الدول
# -------------------------
def get_all_countries():
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, owner_id FROM countries ORDER BY id ASC")
    rows = cursor.fetchall()
    return rows

# -------------------------
# التحقق من وجود دولة بالاسم
# -------------------------
def country_exists(name: str) -> bool:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM countries WHERE name = ?', (name.strip(),))
    exists = bool(cursor.fetchone())
    return exists

# -------------------------
# إنشاء دولة جديدة
# -------------------------
def create_country(name: str, owner_id: int) -> int:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO countries (name, owner_id) VALUES (?, ?)',
        (name.strip(), owner_id)
    )
    country_id = cursor.lastrowid
    cursor.execute(
        'INSERT OR IGNORE INTO country_stats (country_id) VALUES (?)',
        (country_id,)
    )
    conn.commit()
    return country_id

# -------------------------
# الحصول على الدولة الخاصة بالمستخدم
# -------------------------
def get_user_country(user_id: int):
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name FROM countries WHERE owner_id = ?', (user_id,))
        row = cursor.fetchone()

        return row
    except Exception as e:
        print(send_error("get_user_country", e))
        return None

def get_user_country_name(user_id: int):
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM countries WHERE owner_id = ?', (user_id,))
        row = cursor.fetchone()

        return row["name"] if row else None
    except Exception as e:
        print(send_error("get_user_country_name", e))
        return None

# -------------------------
# الحصول على معرف الدولة من خلال المستخدم عن طريق مدينته
# -------------------------
def get_user_country_id(user_id: int):
    conn = get_db_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT country_id
        FROM cities
        WHERE owner_id = ?
        LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()
    return row["country_id"] if row else None

# -------------------------
# إحصائيات الدولة
# -------------------------
def get_country_stats(country_id: int):
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM country_stats WHERE country_id = ?', (country_id,))
        row = cursor.fetchone()

        return dict(row) if row else None
    except Exception as e:
        print(send_error("get_country_stats", e))
        return None

def update_country_stats(country_id: int, economy_score=0, health_level=0, education_level=0,
                         military_power=0, infrastructure_level=0):
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO country_stats (
                country_id, economy_score, health_level, education_level, military_power, infrastructure_level
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(country_id) DO UPDATE SET
                economy_score=excluded.economy_score,
                health_level=excluded.health_level,
                education_level=excluded.education_level,
                military_power=excluded.military_power,
                infrastructure_level=excluded.infrastructure_level
        ''', (country_id, economy_score, health_level, education_level, military_power, infrastructure_level))
        conn.commit()

    except Exception as e:
        print(send_error("update_country_stats", e))
        
# -------------------------
# حساب الميزانية الإجمالية للدولة من جميع المدن
# -------------------------
def get_country_budget(country_id: int) -> float:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT SUM(cb.current_budget)
        FROM city_budget cb
        JOIN cities c ON cb.city_id = c.id
        WHERE c.country_id = ?
    ''', (country_id,))
    row = cursor.fetchone()
    return float(row[0]) if row and row[0] else 0.0

# -------------------------
# الحصول على الدولة أو المدن التابعة
# -------------------------
def get_country_by_user(user_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM countries WHERE owner_id = ?", (user_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

def get_cities_by_country(country_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cities WHERE country_id = ?", (country_id,))
    rows = cursor.fetchall()
    return [dict(r) for r in rows]

# -------------------------
# أفضل الدول حسب مجموع الإحصائيات
# -------------------------
def get_top_countries(limit=10):
    conn = get_db_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT 
            id,
            name,
            (
                economy_score +
                health_level +
                education_level +
                military_power +
                infrastructure_level
            ) AS value
        FROM countries
        ORDER BY value DESC
        LIMIT ?
        ''',
        (limit,)
    )
    result = [dict(row) for row in cursor.fetchall()]
    return result



# ─────────────────────────────
# 🔎 جلب مدينة بالآي دي
# ─────────────────────────────
def get_city_by_id(city_id):
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM cities
        WHERE id = ?
    """, (city_id,))

    return cursor.fetchone()

def get_all_cities_of_country_by_country_id(country_id):
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM cities
        WHERE country_id = ?
    """, (country_id,))

    return cursor.fetchall()

def get_country_by_owner(user_id):
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM countries
        WHERE owner_id = ?
    """, (user_id,))

    return cursor.fetchone()

def get_capital_city(user_id):

    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM cities
        WHERE owner_id = ?
        LIMIT 1
    """, (user_id,))

    return cursor.fetchone()



# ------------------------ Invite
def create_invite(from_user_id, to_user_id, country_id, city_name):
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO country_invites (from_user_id, to_user_id, country_id, city_name)
        VALUES (?, ?, ?, ?)
    """, (from_user_id, to_user_id, country_id, city_name.strip()))

    conn.commit()
    return cursor.lastrowid

def get_pending_invite(to_user_id):
    conn = get_db_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM country_invites
        WHERE to_user_id = ? AND status = 'pending'
    """, (to_user_id,))

    return cursor.fetchone()

def update_invite_status(invite_id, status):
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE country_invites
        SET status = ?
        WHERE id = ?
    """, (status, invite_id))

    conn.commit()
    
def attach_user_to_country(user_id: int, city_id: int, country_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET city_id = ?, country_id = ?
        WHERE user_id = ?
    """, (city_id, country_id, user_id))

    conn.commit()

def has_pending_invite(to_user_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM country_invites WHERE to_user_id=? AND status='pending'", (to_user_id,))
    return bool(cursor.fetchone())

def delete_rejected_invites():
    """حذف كل الدعوات المرفوضة"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM country_invites WHERE status='rejected'")
    conn.commit()