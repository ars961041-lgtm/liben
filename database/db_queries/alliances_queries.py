import time
from ..connection import get_db_conn
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME
MAX_COUNTRIES_PER_ALLIANCE = 10


# ══════════════════════════════════════════
# 🏰 إنشاء / حذف تحالف
# ══════════════════════════════════════════

def create_alliance(name, leader_id, country_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alliances (name, leader_id)
        VALUES (?, ?)
    """, (name, leader_id))
    alliance_id = cursor.lastrowid
    cursor.execute("""
        INSERT INTO alliance_members (alliance_id, user_id, country_id, role)
        VALUES (?, ?, ?, 'leader')
    """, (alliance_id, leader_id, country_id))
    conn.commit()
    return alliance_id


def delete_alliance(alliance_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM alliances WHERE id = ?", (alliance_id,))
    cursor.execute("DELETE FROM alliance_members WHERE alliance_id = ?", (alliance_id,))
    cursor.execute("DELETE FROM alliance_invites WHERE alliance_id = ?", (alliance_id,))
    cursor.execute("DELETE FROM alliance_upgrades WHERE alliance_id = ?", (alliance_id,))
    conn.commit()


# ══════════════════════════════════════════
# 🔎 جلب التحالفات
# ══════════════════════════════════════════

def get_alliance_by_id(alliance_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alliances WHERE id = ?", (alliance_id,))
    alliance = cursor.fetchone()
    if not alliance:
        return None
    cursor.execute("""
        SELECT user_id, country_id, role FROM alliance_members WHERE alliance_id = ?
    """, (alliance_id,))
    members = cursor.fetchall()
    a = dict(alliance)
    a["members"] = [dict(m) for m in members]
    return a


def get_alliance_by_user(user_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.* FROM alliances a
        JOIN alliance_members am ON a.id = am.alliance_id
        WHERE am.user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_alliance_by_country(country_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.* FROM alliances a
        JOIN alliance_members am ON a.id = am.alliance_id
        WHERE am.country_id = ?
    """, (country_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_all_active_alliances(exclude_id=None):
    conn = get_db_conn()
    cursor = conn.cursor()
    if exclude_id:
        cursor.execute("SELECT * FROM alliances WHERE id != ? ORDER BY power DESC", (exclude_id,))
    else:
        cursor.execute("SELECT * FROM alliances ORDER BY power DESC")
    return [dict(r) for r in cursor.fetchall()]


def get_alliance_member_count(alliance_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM alliance_members WHERE alliance_id = ?", (alliance_id,))
    return cursor.fetchone()[0]


# ══════════════════════════════════════════
# 📩 الدعوات
# ══════════════════════════════════════════

def send_alliance_invite(alliance_id, from_user_id, to_user_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    # كولداون: دعوة واحدة يومياً لنفس الشخص من نفس التحالف
    day_ago = int(time.time()) - 86400
    cursor.execute("""
        SELECT id FROM alliance_invites
        WHERE alliance_id = ? AND to_user_id = ? AND created_at > ? AND status = 'pending'
    """, (alliance_id, to_user_id, day_ago))
    if cursor.fetchone():
        return False, "⏳ تم إرسال دعوة لهذا الشخص مؤخراً، انتظر 24 ساعة."
    cursor.execute("""
        INSERT INTO alliance_invites (alliance_id, from_user_id, to_user_id)
        VALUES (?, ?, ?)
    """, (alliance_id, from_user_id, to_user_id))
    conn.commit()
    return True, cursor.lastrowid


def get_user_pending_invites(user_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ai.id, ai.alliance_id, a.name, ai.from_user_id, ai.created_at
        FROM alliance_invites ai
        JOIN alliances a ON ai.alliance_id = a.id
        WHERE ai.to_user_id = ? AND ai.status = 'pending'
        ORDER BY ai.created_at DESC
    """, (user_id,))
    return [dict(r) for r in cursor.fetchall()]


def get_invite_by_id(invite_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alliance_invites WHERE id = ?", (invite_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def accept_invite(invite_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alliance_invites WHERE id = ?", (invite_id,))
    invite = cursor.fetchone()
    if not invite:
        return False, "❌ الدعوة غير موجودة."
    invite = dict(invite)

    # التحقق من الحد الأقصى
    count = get_alliance_member_count(invite["alliance_id"])
    if count >= MAX_COUNTRIES_PER_ALLIANCE:
        return False, "❌ التحالف وصل للحد الأقصى من الأعضاء."

    # جلب دولة المدعو
    from database.db_queries.countries_queries import get_country_by_owner
    country = get_country_by_owner(invite["to_user_id"])
    country_id = dict(country)["id"] if country else None

    cursor.execute("""
        INSERT OR IGNORE INTO alliance_members (alliance_id, user_id, country_id, role)
        VALUES (?, ?, ?, 'member')
    """, (invite["alliance_id"], invite["to_user_id"], country_id))
    cursor.execute("UPDATE alliance_invites SET status = 'accepted' WHERE id = ?", (invite_id,))
    conn.commit()
    _recalc_alliance_power(invite["alliance_id"])
    return True, "✅ انضممت للتحالف!"


def reject_invite(invite_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE alliance_invites SET status = 'rejected' WHERE id = ?", (invite_id,))
    conn.commit()


# ══════════════════════════════════════════
# 🚪 الانسحاب من التحالف
# ══════════════════════════════════════════

def leave_alliance(user_id, penalty=True):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT alliance_id FROM alliance_members WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    if not row:
        return False, "❌ لست في أي تحالف."
    alliance_id = row[0]

    # التحقق إذا كان القائد
    cursor.execute("SELECT leader_id FROM alliances WHERE id = ?", (alliance_id,))
    a = cursor.fetchone()
    if a and a[0] == user_id:
        return False, "❌ القائد لا يمكنه الانسحاب. يجب حل التحالف أو نقل القيادة."

    cursor.execute("DELETE FROM alliance_members WHERE user_id = ?", (user_id,))
    conn.commit()
    _recalc_alliance_power(alliance_id)

    if penalty:
        # عقوبة السمعة
        from database.db_queries.advanced_war_queries import update_reputation
        update_reputation(user_id, betrayed=1)
        return True, "⚠️ انسحبت من التحالف. تم خصم نقاط من سمعتك."
    return True, "✅ انسحبت من التحالف."


# ══════════════════════════════════════════
# 💪 قوة التحالف
# ══════════════════════════════════════════

def _recalc_alliance_power(alliance_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT am.country_id FROM alliance_members am WHERE am.alliance_id = ?
    """, (alliance_id,))
    rows = cursor.fetchall()

    total_power = 0.0
    for row in rows:
        cid = row[0]
        if not cid:
            continue
        cursor.execute("""
            SELECT COALESCE(SUM(tt.attack * ct.quantity), 0)
            FROM city_troops ct
            JOIN troop_types tt ON ct.troop_type_id = tt.id
            JOIN cities c ON ct.city_id = c.id
            WHERE c.country_id = ?
        """, (cid,))
        r = cursor.fetchone()
        total_power += float(r[0]) if r else 0

    # إضافة قوة الترقيات
    cursor.execute("""
        SELECT aut.effect_value, au.level
        FROM alliance_upgrades au
        JOIN alliance_upgrade_types aut ON au.upgrade_type_id = aut.id
        WHERE au.alliance_id = ? AND aut.effect_type IN ('attack_bonus','defense_bonus','hp_bonus')
    """, (alliance_id,))
    for upg in cursor.fetchall():
        total_power *= (1 + upg[0] * upg[1])

    cursor.execute("UPDATE alliances SET power = ? WHERE id = ?", (round(total_power, 2), alliance_id))
    conn.commit()
    return total_power


def get_alliance_power(alliance_id):
    return _recalc_alliance_power(alliance_id)


def get_top_alliances(limit=10):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, power, leader_id,
               (SELECT COUNT(*) FROM alliance_members am WHERE am.alliance_id = alliances.id) as member_count
        FROM alliances
        ORDER BY power DESC LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# ⬆️ ترقيات التحالف
# ══════════════════════════════════════════

def get_all_upgrade_types():
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alliance_upgrade_types ORDER BY price")
    return [dict(r) for r in cursor.fetchall()]


def get_alliance_upgrades(alliance_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT au.level, aut.*
        FROM alliance_upgrades au
        JOIN alliance_upgrade_types aut ON au.upgrade_type_id = aut.id
        WHERE au.alliance_id = ?
    """, (alliance_id,))
    return [dict(r) for r in cursor.fetchall()]


def get_alliance_upgrade_level(alliance_id, upgrade_name):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT au.level FROM alliance_upgrades au
        JOIN alliance_upgrade_types aut ON au.upgrade_type_id = aut.id
        WHERE au.alliance_id = ? AND aut.name = ?
    """, (alliance_id, upgrade_name))
    row = cursor.fetchone()
    return row[0] if row else 0


def purchase_alliance_upgrade(alliance_id, upgrade_type_id, buyer_user_id):
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM alliance_upgrade_types WHERE id = ?", (upgrade_type_id,))
    upg_type = cursor.fetchone()
    if not upg_type:
        return False, "❌ الترقية غير موجودة."
    upg_type = dict(upg_type)

    cursor.execute("""
        SELECT level FROM alliance_upgrades
        WHERE alliance_id = ? AND upgrade_type_id = ?
    """, (alliance_id, upgrade_type_id))
    existing = cursor.fetchone()
    current_level = existing[0] if existing else 0

    if current_level >= upg_type["max_level"]:
        return False, f"❌ هذه الترقية وصلت للحد الأقصى (مستوى {upg_type['max_level']})."

    cost = upg_type["price"] * (current_level + 1)

    from database.db_queries.bank_queries import get_user_balance, deduct_user_balance
    balance = get_user_balance(buyer_user_id)
    if balance < cost:
        return False, f"❌ رصيدك غير كافٍ. التكلفة: {cost:.0f} {CURRENCY_ARABIC_NAME}، رصيدك: {balance:.0f} {CURRENCY_ARABIC_NAME}."

    deduct_user_balance(buyer_user_id, cost)

    if existing:
        cursor.execute("""
            UPDATE alliance_upgrades SET level = level + 1
            WHERE alliance_id = ? AND upgrade_type_id = ?
        """, (alliance_id, upgrade_type_id))
    else:
        cursor.execute("""
            INSERT INTO alliance_upgrades (alliance_id, upgrade_type_id, level)
            VALUES (?, ?, 1)
        """, (alliance_id, upgrade_type_id))
    conn.commit()
    _recalc_alliance_power(alliance_id)
    return True, f"✅ تم شراء ترقية {upg_type['name_ar']} (مستوى {current_level + 1})"


# ══════════════════════════════════════════
# 🎖 دور الأعضاء
# ══════════════════════════════════════════

def set_member_role(alliance_id, user_id, role):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE alliance_members SET role = ?
        WHERE alliance_id = ? AND user_id = ?
    """, (role, alliance_id, user_id))
    conn.commit()


def transfer_leadership(alliance_id, old_leader_id, new_leader_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE alliances SET leader_id = ? WHERE id = ?", (new_leader_id, alliance_id))
    cursor.execute("""
        UPDATE alliance_members SET role = 'member'
        WHERE alliance_id = ? AND user_id = ?
    """, (alliance_id, old_leader_id))
    cursor.execute("""
        UPDATE alliance_members SET role = 'leader'
        WHERE alliance_id = ? AND user_id = ?
    """, (alliance_id, new_leader_id))
    conn.commit()


def kick_member(alliance_id, user_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM alliance_members WHERE alliance_id = ? AND user_id = ?
    """, (alliance_id, user_id))
    conn.commit()
    _recalc_alliance_power(alliance_id)


# ══════════════════════════════════════════
# ⚔️ حروب التحالفات
# ══════════════════════════════════════════

def start_alliance_war(alliance_1, alliance_2):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alliance_wars (alliance_1, alliance_2)
        VALUES (?, ?)
    """, (alliance_1, alliance_2))
    conn.commit()
    return cursor.lastrowid


def end_alliance_war(war_id, winner_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE alliance_wars
        SET status = 'ended', winner = ?, ended_at = ?
        WHERE id = ?
    """, (winner_id, int(time.time()), war_id))
    conn.commit()


# ══════════════════════════════════════════
# 🔧 مساعدات
# ══════════════════════════════════════════

def alliance_name_exists(name):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM alliances WHERE name = ?", (name,))
    return cursor.fetchone() is not None


def get_alliance_effect(alliance_id, effect_type):
    """يرجع مجموع تأثير ترقية معينة لتحالف"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COALESCE(SUM(aut.effect_value * au.level), 0)
        FROM alliance_upgrades au
        JOIN alliance_upgrade_types aut ON au.upgrade_type_id = aut.id
        WHERE au.alliance_id = ? AND aut.effect_type = ?
    """, (alliance_id, effect_type))
    row = cursor.fetchone()
    return float(row[0]) if row else 0.0
