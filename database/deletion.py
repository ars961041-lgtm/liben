"""
نظام الحذف المركزي — بديل آمن عن ON DELETE CASCADE.

كل دالة تحذف البيانات المرتبطة يدوياً بالترتيب الصحيح
(الأبناء أولاً ثم الأب) داخل معاملة واحدة.
"""
from database.connection import get_db_conn


# ══════════════════════════════════════════
# حذف مدينة وكل ما يتعلق بها
# ══════════════════════════════════════════

def delete_city(city_id: int) -> bool:
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        cur.execute("BEGIN")
        cur.execute("DELETE FROM daily_tasks        WHERE city_id = ?",           (city_id,))
        cur.execute("DELETE FROM city_troops        WHERE city_id = ?",           (city_id,))
        cur.execute("DELETE FROM city_equipment     WHERE city_id = ?",           (city_id,))
        cur.execute("DELETE FROM city_assets        WHERE city_id = ?",           (city_id,))
        cur.execute("DELETE FROM city_budget        WHERE city_id = ?",           (city_id,))
        cur.execute("DELETE FROM city_aspects       WHERE city_id = ?",           (city_id,))
        cur.execute("DELETE FROM city_spending      WHERE city_id = ?",           (city_id,))
        cur.execute("DELETE FROM injured_troops     WHERE city_id = ?",           (city_id,))
        cur.execute("DELETE FROM damaged_equipment  WHERE city_id = ?",           (city_id,))
        cur.execute("DELETE FROM repair_queue       WHERE city_id = ?",           (city_id,))
        cur.execute("DELETE FROM asset_log          WHERE city_id = ?",           (city_id,))
        cur.execute("DELETE FROM cities             WHERE id      = ?",           (city_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"[deletion] delete_city({city_id}) failed: {e}")
        return False


# ══════════════════════════════════════════
# حذف دولة وكل ما يتعلق بها
# ══════════════════════════════════════════

def delete_country(country_id: int) -> bool:
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        cur.execute("BEGIN")

        # احذف كل مدن الدولة أولاً
        cur.execute("SELECT id FROM cities WHERE country_id = ?", (country_id,))
        city_ids = [row[0] for row in cur.fetchall()]
        for cid in city_ids:
            cur.execute("DELETE FROM daily_tasks        WHERE city_id = ?", (cid,))
            cur.execute("DELETE FROM city_troops        WHERE city_id = ?", (cid,))
            cur.execute("DELETE FROM city_equipment     WHERE city_id = ?", (cid,))
            cur.execute("DELETE FROM city_assets        WHERE city_id = ?", (cid,))
            cur.execute("DELETE FROM city_budget        WHERE city_id = ?", (cid,))
            cur.execute("DELETE FROM city_aspects       WHERE city_id = ?", (cid,))
            cur.execute("DELETE FROM city_spending      WHERE city_id = ?", (cid,))
            cur.execute("DELETE FROM injured_troops     WHERE city_id = ?", (cid,))
            cur.execute("DELETE FROM damaged_equipment  WHERE city_id = ?", (cid,))
            cur.execute("DELETE FROM repair_queue       WHERE city_id = ?", (cid,))
            cur.execute("DELETE FROM asset_log          WHERE city_id = ?", (cid,))

        cur.execute("DELETE FROM cities              WHERE country_id = ?", (country_id,))

        # بيانات الدولة نفسها
        cur.execute("DELETE FROM country_influence   WHERE country_id = ?", (country_id,))
        cur.execute("DELETE FROM country_visibility  WHERE country_id = ?", (country_id,))
        cur.execute("DELETE FROM country_freeze      WHERE country_id = ?", (country_id,))
        cur.execute("DELETE FROM country_recovery    WHERE country_id = ?", (country_id,))
        cur.execute("DELETE FROM army_fatigue        WHERE country_id = ?", (country_id,))
        cur.execute("DELETE FROM army_maintenance    WHERE country_id = ?", (country_id,))
        cur.execute("DELETE FROM spy_units           WHERE country_id = ?", (country_id,))
        cur.execute("DELETE FROM spy_agents          WHERE country_id = ?", (country_id,))
        cur.execute("DELETE FROM exploration_log     WHERE country_id = ?", (country_id,))
        cur.execute("DELETE FROM alliance_members    WHERE country_id = ?", (country_id,))
        cur.execute("DELETE FROM countries           WHERE id         = ?", (country_id,))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"[deletion] delete_country({country_id}) failed: {e}")
        return False


# ══════════════════════════════════════════
# حذف تحالف وكل ما يتعلق به
# ══════════════════════════════════════════

def delete_alliance(alliance_id: int) -> bool:
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        cur.execute("BEGIN")
        cur.execute("DELETE FROM alliance_members       WHERE alliance_id = ?", (alliance_id,))
        cur.execute("DELETE FROM alliance_invites       WHERE alliance_id = ?", (alliance_id,))
        cur.execute("DELETE FROM alliance_upgrades      WHERE alliance_id = ?", (alliance_id,))
        cur.execute("DELETE FROM alliance_support_stats WHERE alliance_id = ?", (alliance_id,))
        cur.execute("DELETE FROM alliances              WHERE id          = ?", (alliance_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"[deletion] delete_alliance({alliance_id}) failed: {e}")
        return False


# ══════════════════════════════════════════
# حذف مستخدم وكل بياناته
# ══════════════════════════════════════════

def delete_user(user_id: int) -> bool:
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        cur.execute("BEGIN")
        cur.execute("DELETE FROM user_accounts       WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM bank_cooldowns      WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM loans               WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM user_achievements   WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM season_titles       WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM user_cards          WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM player_reputation   WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM azkar_progress      WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM azkar_reminders     WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM user_timezone       WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM group_members       WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM action_cooldowns    WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM global_mutes        WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM users               WHERE user_id = ?", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"[deletion] delete_user({user_id}) failed: {e}")
        return False
