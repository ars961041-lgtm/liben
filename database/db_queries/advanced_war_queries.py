import time
from ..connection import get_db_conn


# ══════════════════════════════════════════
# ⚔️ المعارك
# ══════════════════════════════════════════

def create_country_battle(attacker_country_id, defender_country_id,
                          attacker_user_id, defender_user_id,
                          travel_seconds=1200, battle_type="normal"):
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    travel_end = now + travel_seconds
    cursor.execute("""
        INSERT INTO country_battles
        (attacker_country_id, defender_country_id, attacker_user_id, defender_user_id,
         status, travel_end_time, battle_type, created_at)
        VALUES (?, ?, ?, ?, 'traveling', ?, ?, ?)
    """, (attacker_country_id, defender_country_id,
          attacker_user_id, defender_user_id,
          travel_end, battle_type, now))
    conn.commit()
    return cursor.lastrowid


def get_battle_by_id(battle_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM country_battles WHERE id = ?", (battle_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_active_battles_for_country(country_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM country_battles
        WHERE (attacker_country_id = ? OR defender_country_id = ?)
          AND status IN ('traveling', 'in_battle')
        ORDER BY created_at DESC
    """, (country_id, country_id))
    return [dict(r) for r in cursor.fetchall()]


def get_traveling_battles_ready():
    """جلب المعارك التي انتهى وقت سفرها"""
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        SELECT * FROM country_battles
        WHERE status = 'traveling' AND travel_end_time <= ?
    """, (now,))
    return [dict(r) for r in cursor.fetchall()]


def get_in_battle_battles_ready():
    """جلب المعارك التي انتهى وقت قتالها"""
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        SELECT * FROM country_battles
        WHERE status = 'in_battle' AND battle_end_time <= ?
    """, (now,))
    return [dict(r) for r in cursor.fetchall()]


def set_battle_in_battle(battle_id, battle_duration=300):
    conn = get_db_conn()
    cursor = conn.cursor()
    battle_end = int(time.time()) + battle_duration
    cursor.execute("""
        UPDATE country_battles
        SET status = 'in_battle', battle_end_time = ?
        WHERE id = ?
    """, (battle_end, battle_id))
    conn.commit()


def finish_battle(battle_id, winner_country_id, loot,
                  attacker_power, defender_power):
    """
    Atomically marks a battle as finished.
    Only updates if status is still 'in_battle' — prevents double-finalization.
    Returns True if the row was actually updated (this call won the race), False otherwise.
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE country_battles
        SET status = 'finished', winner_country_id = ?,
            loot = ?, attacker_power = ?, defender_power = ?
        WHERE id = ? AND status = 'in_battle'
    """, (winner_country_id, loot, attacker_power, defender_power, battle_id))
    conn.commit()
    updated = cursor.rowcount > 0
    if updated:
        print(f"[BATTLE_HISTORY_SYNC] battle_id={battle_id} status→finished winner={winner_country_id}")
    return updated


def finish_fake_battle(battle_id):
    """Finishes a fake/traveling battle — only allowed from 'traveling' status."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE country_battles
        SET status = 'finished', winner_country_id = NULL, loot = 0,
            attacker_power = 0, defender_power = 0
        WHERE id = ? AND status = 'traveling'
    """, (battle_id,))
    conn.commit()
    if cursor.rowcount > 0:
        print(f"[BATTLE_HISTORY_SYNC] battle_id={battle_id} status→finished (fake/traveling)")


def get_battle_history_for_country(country_id, limit=10):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM country_battles
        WHERE (attacker_country_id = ? OR defender_country_id = ?)
          AND status = 'finished'
        ORDER BY created_at DESC LIMIT ?
    """, (country_id, country_id, limit))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# 🤝 الداعمون
# ══════════════════════════════════════════

def add_supporter(battle_id, country_id, user_id, side, power):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO battle_supporters
        (battle_id, country_id, user_id, side, power_contributed)
        VALUES (?, ?, ?, ?, ?)
    """, (battle_id, country_id, user_id, side, power))
    conn.commit()
    return cursor.rowcount > 0


def get_supporters(battle_id, side=None):
    conn = get_db_conn()
    cursor = conn.cursor()
    if side:
        cursor.execute("""
            SELECT * FROM battle_supporters
            WHERE battle_id = ? AND side = ?
        """, (battle_id, side))
    else:
        cursor.execute("SELECT * FROM battle_supporters WHERE battle_id = ?", (battle_id,))
    return [dict(r) for r in cursor.fetchall()]


def get_total_support_power(battle_id, side):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COALESCE(SUM(power_contributed), 0)
        FROM battle_supporters
        WHERE battle_id = ? AND side = ?
    """, (battle_id, side))
    row = cursor.fetchone()
    return float(row[0]) if row else 0.0


# ══════════════════════════════════════════
# 🕵️ الجواسيس
# ══════════════════════════════════════════

def get_spy_units(country_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM spy_units WHERE country_id = ?", (country_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def ensure_spy_units(country_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO spy_units (country_id) VALUES (?)
    """, (country_id,))
    conn.commit()


def upgrade_spy_level(country_id, field="spy_level"):
    conn = get_db_conn()
    cursor = conn.cursor()
    ensure_spy_units(country_id)
    cursor.execute(f"""
        UPDATE spy_units SET {field} = {field} + 1
        WHERE country_id = ?
    """, (country_id,))
    conn.commit()


def add_spy_operation(attacker_country_id, target_country_id, result, info):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO spy_operations
        (attacker_country_id, target_country_id, result, info_obtained)
        VALUES (?, ?, ?, ?)
    """, (attacker_country_id, target_country_id, result, info))
    conn.commit()


# ══════════════════════════════════════════
# 🃏 البطاقات
# ══════════════════════════════════════════

def get_all_cards():
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cards ORDER BY category, price")
    return [dict(r) for r in cursor.fetchall()]


def get_card_by_id(card_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_card_by_name(name):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cards WHERE name = ?", (name,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_user_cards(user_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT uc.id, uc.quantity, c.*
        FROM user_cards uc
        JOIN cards c ON uc.card_id = c.id
        WHERE uc.user_id = ? AND uc.quantity > 0
        ORDER BY c.category
    """, (user_id,))
    return [dict(r) for r in cursor.fetchall()]


def add_user_card(user_id, card_id, quantity=1):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_cards (user_id, card_id, quantity)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, card_id) DO UPDATE SET quantity = quantity + ?
    """, (user_id, card_id, quantity, quantity))
    conn.commit()


def use_user_card(user_id, card_id):
    """يستهلك بطاقة واحدة، يرجع True إذا نجح"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT quantity FROM user_cards
        WHERE user_id = ? AND card_id = ?
    """, (user_id, card_id))
    row = cursor.fetchone()
    if not row or row[0] <= 0:
        return False
    cursor.execute("""
        UPDATE user_cards SET quantity = quantity - 1
        WHERE user_id = ? AND card_id = ?
    """, (user_id, card_id))
    conn.commit()
    return True


def get_user_card_count(user_id, card_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT quantity FROM user_cards WHERE user_id = ? AND card_id = ?
    """, (user_id, card_id))
    row = cursor.fetchone()
    return row[0] if row else 0


# ══════════════════════════════════════════
# 🏆 السمعة
# ══════════════════════════════════════════

def get_reputation(user_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM player_reputation WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def ensure_reputation(user_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    # يبدأ بـ loyalty_score=0 — لا سمعة إيجابية قبل بناء سجل حقيقي
    cursor.execute("""
        INSERT OR IGNORE INTO player_reputation (user_id, loyalty_score) VALUES (?, 0)
    """, (user_id,))
    conn.commit()


def update_reputation(user_id, helped=0, ignored=0, betrayed=0):
    ensure_reputation(user_id)
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE player_reputation
        SET battles_helped  = battles_helped  + ?,
            battles_ignored = battles_ignored + ?,
            betrayals       = betrayals       + ?,
            loyalty_score   = MIN(100, MAX(0,
                loyalty_score + (? * 5) - (? * 3) - (? * 10)
            ))
        WHERE user_id = ?
    """, (helped, ignored, betrayed, helped, ignored, betrayed, user_id))
    conn.commit()
    _recalc_title(user_id)


def _recalc_title(user_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT loyalty_score, betrayals, battles_helped, battles_ignored
        FROM player_reputation WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    if not row:
        return
    score, betrayals, helped, ignored = row[0], row[1], row[2], row[3]
    total_interactions = helped + ignored

    if betrayals >= 3:
        title = "🐍 خائن"
    elif total_interactions < 3:
        # لا يكفي السجل لتحديد السمعة — محايد دائماً
        title = "😶 محايد"
    elif score >= 80:
        title = "🤝 وفي"
    elif score >= 50:
        title = "⚔️ مقاتل"
    else:
        title = "😶 محايد"

    cursor.execute(
        "UPDATE player_reputation SET reputation_title = ? WHERE user_id = ?",
        (title, user_id)
    )
    conn.commit()


# ══════════════════════════════════════════
# 📣 طلبات الدعم
# ══════════════════════════════════════════

def create_support_request(battle_id, requesting_country_id, target_user_id, side):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO support_requests
        (battle_id, requesting_country_id, target_user_id, side)
        VALUES (?, ?, ?, ?)
    """, (battle_id, requesting_country_id, target_user_id, side))
    conn.commit()
    return cursor.lastrowid


def get_pending_support_requests(battle_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM support_requests
        WHERE battle_id = ? AND status = 'pending'
    """, (battle_id,))
    return [dict(r) for r in cursor.fetchall()]


def update_support_request_status(request_id, status):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE support_requests SET status = ? WHERE id = ?
    """, (status, request_id))
    conn.commit()


# ══════════════════════════════════════════
# 🔄 نقل ملكية الدولة
# ══════════════════════════════════════════

def create_country_transfer(country_id, from_user_id, to_user_id, penalty):
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    expires = now + 86400  # 24 ساعة للتراجع
    cursor.execute("""
        INSERT INTO country_transfers
        (country_id, from_user_id, to_user_id, penalty_applied, transferred_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (country_id, from_user_id, to_user_id, penalty, now, expires))
    conn.commit()
    return cursor.lastrowid


def get_active_transfer(country_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        SELECT * FROM country_transfers
        WHERE country_id = ? AND status = 'active' AND expires_at > ?
        ORDER BY transferred_at DESC LIMIT 1
    """, (country_id, now))
    row = cursor.fetchone()
    return dict(row) if row else None


def complete_transfer(transfer_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE country_transfers SET status = 'completed' WHERE id = ?", (transfer_id,))
    conn.commit()


def rollback_transfer(transfer_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE country_transfers SET status = 'rolled_back' WHERE id = ?", (transfer_id,))
    conn.commit()


def get_transfer_cooldown(from_user_id):
    """يتحقق إذا مضت 24 ساعة على آخر نقل"""
    conn = get_db_conn()
    cursor = conn.cursor()
    day_ago = int(time.time()) - 86400
    cursor.execute("""
        SELECT transferred_at FROM country_transfers
        WHERE from_user_id = ? AND transferred_at > ?
        ORDER BY transferred_at DESC LIMIT 1
    """, (from_user_id, day_ago))
    row = cursor.fetchone()
    if row:
        remaining = 86400 - (int(time.time()) - row[0])
        return True, remaining
    return False, 0


# ══════════════════════════════════════════
# 🧊 تجميد الدولة
# ══════════════════════════════════════════

def freeze_country(country_id, duration=86400, reason="transfer"):
    conn = get_db_conn()
    cursor = conn.cursor()
    frozen_until = int(time.time()) + duration
    cursor.execute("""
        INSERT INTO country_freeze (country_id, frozen_until, reason)
        VALUES (?, ?, ?)
        ON CONFLICT(country_id) DO UPDATE SET frozen_until = ?, reason = ?
    """, (country_id, frozen_until, reason, frozen_until, reason))
    conn.commit()


def unfreeze_country(country_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM country_freeze WHERE country_id = ?", (country_id,))
    conn.commit()


def is_country_frozen(country_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        SELECT frozen_until FROM country_freeze
        WHERE country_id = ? AND frozen_until > ?
    """, (country_id, now))
    row = cursor.fetchone()
    if row:
        return True, row[0] - now
    return False, 0


# ══════════════════════════════════════════
# 📨 دعوات المدن
# ══════════════════════════════════════════

def create_city_invite(from_user_id, to_user_id, city_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    # إلغاء الدعوات القديمة لنفس المدينة
    cursor.execute("""
        UPDATE city_invites SET status = 'cancelled'
        WHERE city_id = ? AND status = 'pending'
    """, (city_id,))
    cursor.execute("""
        INSERT INTO city_invites (from_user_id, to_user_id, city_id)
        VALUES (?, ?, ?)
    """, (from_user_id, to_user_id, city_id))
    conn.commit()
    return cursor.lastrowid


def get_pending_city_invites(to_user_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ci.*, c.name as city_name
        FROM city_invites ci
        JOIN cities c ON ci.city_id = c.id
        WHERE ci.to_user_id = ? AND ci.status = 'pending'
        ORDER BY ci.created_at DESC
    """, (to_user_id,))
    return [dict(r) for r in cursor.fetchall()]


def update_city_invite_status(invite_id, status):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE city_invites SET status = ? WHERE id = ?", (status, invite_id))
    conn.commit()


# ══════════════════════════════════════════
# 🗳️ تصويت حل التحالف
# ══════════════════════════════════════════

def cast_dissolve_vote(alliance_id, voter_user_id, vote):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alliance_dissolve_votes (alliance_id, voter_user_id, vote)
        VALUES (?, ?, ?)
        ON CONFLICT(alliance_id, voter_user_id) DO UPDATE SET vote = ?
    """, (alliance_id, voter_user_id, vote, vote))
    conn.commit()


def get_dissolve_votes(alliance_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT vote, COUNT(*) as count FROM alliance_dissolve_votes
        WHERE alliance_id = ? GROUP BY vote
    """, (alliance_id,))
    rows = cursor.fetchall()
    result = {"accept": 0, "reject": 0}
    for r in rows:
        result[r[0]] = r[1]
    return result


def clear_dissolve_votes(alliance_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM alliance_dissolve_votes WHERE alliance_id = ?", (alliance_id,))
    conn.commit()


# ══════════════════════════════════════════
# 👁️ نظام الرؤية والاكتشاف
# ══════════════════════════════════════════

import random as _random
import string as _string


def _gen_code():
    return ''.join(_random.choices(_string.digits, k=5))


def ensure_visibility(country_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO country_visibility (country_id, visibility_mode, daily_attack_code, code_generated_at)
        VALUES (?, 'public', ?, ?)
    """, (country_id, _gen_code(), int(time.time())))
    conn.commit()


def get_visibility(country_id):
    ensure_visibility(country_id)
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM country_visibility WHERE country_id = ?", (country_id,))
    row = cursor.fetchone()
    if not row:
        return None
    v = dict(row)
    # تجديد الكود إذا مضى 24 ساعة
    if int(time.time()) - v["code_generated_at"] >= 86400:
        new_code = _gen_code()
        cursor.execute("""
            UPDATE country_visibility SET daily_attack_code = ?, code_generated_at = ?
            WHERE country_id = ?
        """, (new_code, int(time.time()), country_id))
        conn.commit()
        v["daily_attack_code"] = new_code
        v["code_generated_at"] = int(time.time())
    return v


def set_visibility_mode(country_id, mode):
    """mode: 'public' أو 'hidden'"""
    ensure_visibility(country_id)
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE country_visibility SET visibility_mode = ?, hidden_cost_paid_at = ?
        WHERE country_id = ?
    """, (mode, int(time.time()), country_id))
    conn.commit()


def verify_attack_code(country_id, code):
    """يتحقق من صحة كود الهجوم"""
    v = get_visibility(country_id)
    if not v:
        return False
    return v["daily_attack_code"] == str(code).strip()


def add_discovered_country(attacker_country_id, target_country_id, duration=86400 * 3):
    """يضيف دولة لقائمة الأهداف المكتشفة (تنتهي بعد 3 أيام)"""
    conn = get_db_conn()
    cursor = conn.cursor()
    expires = int(time.time()) + duration
    cursor.execute("""
        INSERT INTO discovered_countries (attacker_country_id, target_country_id, expires_at)
        VALUES (?, ?, ?)
        ON CONFLICT(attacker_country_id, target_country_id)
        DO UPDATE SET discovered_at = ?, expires_at = ?
    """, (attacker_country_id, target_country_id, expires,
          int(time.time()), expires))
    conn.commit()


def get_discovered_countries(attacker_country_id):
    """يرجع الدول المكتشفة غير المنتهية الصلاحية"""
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        SELECT dc.target_country_id, c.name, c.owner_id
        FROM discovered_countries dc
        JOIN countries c ON dc.target_country_id = c.id
        WHERE dc.attacker_country_id = ? AND (dc.expires_at IS NULL OR dc.expires_at > ?)
    """, (attacker_country_id, now))
    return [dict(r) for r in cursor.fetchall()]


def is_country_discovered(attacker_country_id, target_country_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        SELECT id FROM discovered_countries
        WHERE attacker_country_id = ? AND target_country_id = ?
          AND (expires_at IS NULL OR expires_at > ?)
    """, (attacker_country_id, target_country_id, now))
    return cursor.fetchone() is not None


# ══════════════════════════════════════════
# 🧊 تجميد الدولة
# ══════════════════════════════════════════

def freeze_country(country_id, duration=86400, reason="transfer"):
    conn = get_db_conn()
    cursor = conn.cursor()
    frozen_until = int(time.time()) + duration
    cursor.execute("""
        INSERT INTO country_freeze (country_id, frozen_until, reason)
        VALUES (?, ?, ?)
        ON CONFLICT(country_id) DO UPDATE SET frozen_until = ?, reason = ?
    """, (country_id, frozen_until, reason, frozen_until, reason))
    conn.commit()


def unfreeze_country(country_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM country_freeze WHERE country_id = ?", (country_id,))
    conn.commit()


def is_country_frozen(country_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        SELECT frozen_until FROM country_freeze
        WHERE country_id = ? AND frozen_until > ?
    """, (country_id, now))
    row = cursor.fetchone()
    if row:
        return True, row[0] - now
    return False, 0


# ══════════════════════════════════════════
# 📣 طلبات الدعم — كولداون 60 ثانية
# ══════════════════════════════════════════

def can_send_support_request(battle_id, requesting_country_id, cooldown=60):
    """يتحقق من كولداون طلب الدعم (60 ثانية)"""
    conn = get_db_conn()
    cursor = conn.cursor()
    since = int(time.time()) - cooldown
    cursor.execute("""
        SELECT id FROM support_requests
        WHERE battle_id = ? AND requesting_country_id = ? AND last_sent_at > ?
    """, (battle_id, requesting_country_id, since))
    return cursor.fetchone() is None


def create_support_request_targeted(battle_id, requesting_country_id,
                                    target_country_id, target_user_id, side):
    """طلب دعم موجه لدولة محددة"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO support_requests
        (battle_id, requesting_country_id, target_country_id, target_user_id, side, last_sent_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (battle_id, requesting_country_id, target_country_id,
          target_user_id, side, int(time.time())))
    conn.commit()
    return cursor.lastrowid


def get_my_pending_support_requests(user_id):
    """جلب طلبات الدعم المعلقة للمستخدم"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sr.*, c.name as requester_name
        FROM support_requests sr
        LEFT JOIN alliance_members am ON sr.requesting_country_id = am.country_id
        LEFT JOIN countries c ON sr.requesting_country_id = c.id
        WHERE sr.target_user_id = ? AND sr.status = 'pending'
        ORDER BY sr.created_at DESC LIMIT 10
    """, (user_id,))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# 🕵️ نظام التجسس المتقدم — تكلفة + كولداون + نتائج مخزنة
# ══════════════════════════════════════════

def get_spy_cooldown(attacker_country_id: int, target_country_id: int) -> tuple:
    """
    يتحقق من كولداون التجسس على هدف محدد.
    يرجع (can_spy: bool, remaining_seconds: int, cached_result: dict|None)
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT result, info_obtained, created_at
        FROM spy_operations
        WHERE attacker_country_id = ? AND target_country_id = ?
        ORDER BY created_at DESC LIMIT 1
    """, (attacker_country_id, target_country_id))
    row = cursor.fetchone()
    if not row:
        return True, 0, None

    row = dict(row)
    try:
        from core.admin import get_const_int
        cooldown = get_const_int("spy_cooldown_sec", 120)
    except Exception:
        cooldown = 120

    elapsed = int(time.time()) - row["created_at"]
    if elapsed < cooldown:
        remaining = cooldown - elapsed
        # إرجاع النتيجة المخزنة
        cached = {"result": row["result"], "info": row["info_obtained"]}
        return False, remaining, cached

    return True, 0, None


def get_last_spy_result(attacker_country_id: int, target_country_id: int) -> dict | None:
    """يرجع آخر نتيجة تجسس مخزنة"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT result, info_obtained, created_at
        FROM spy_operations
        WHERE attacker_country_id = ? AND target_country_id = ?
        ORDER BY created_at DESC LIMIT 1
    """, (attacker_country_id, target_country_id))
    row = cursor.fetchone()
    return dict(row) if row else None


# ══════════════════════════════════════════
# 🔍 كولداون الاستكشاف (action_cooldowns)
# ══════════════════════════════════════════

EXPLORE_COOLDOWN = 20 * 60  # 20 دقيقة


def get_explore_cooldown(user_id: int) -> tuple:
    """
    يتحقق من كولداون الاستكشاف للمستخدم.
    يرجع (can_explore: bool, remaining_seconds: int)
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT last_time FROM action_cooldowns WHERE user_id = ? AND action = 'explore'",
        (user_id,)
    )
    row = cursor.fetchone()
    if not row:
        return True, 0
    elapsed = int(time.time()) - row[0]
    if elapsed >= EXPLORE_COOLDOWN:
        return True, 0
    return False, EXPLORE_COOLDOWN - elapsed


def set_explore_cooldown(user_id: int):
    """يسجل وقت آخر استكشاف للمستخدم."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO action_cooldowns (user_id, action, last_time)
        VALUES (?, 'explore', ?)
        ON CONFLICT(user_id, action) DO UPDATE SET last_time = excluded.last_time
    """, (user_id, int(time.time())))
    conn.commit()


def clear_explore_cooldown(user_id: int):
    """يمسح كولداون الاستكشاف — يُستخدم عند فشل العملية لإعادة المحاولة."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM action_cooldowns WHERE user_id = ? AND action = 'explore'",
        (user_id,)
    )
    conn.commit()
