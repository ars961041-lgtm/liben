"""
نظام الإنجازات — يُفعَّل تلقائياً عند أحداث اللعبة
"""
import time
import threading
from database.connection import get_db_conn
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

# ─── حماية من التشغيل المزدوج لنفس الحدث ───
# key: (user_id, event) → last_triggered_timestamp
_trigger_times: dict[tuple, float] = {}
_trigger_lock = threading.Lock()
_TRIGGER_COOLDOWN = 5  # ثوانٍ — يمنع نفس الحدث مرتين في لحظة واحدة


def _c(name, default):
    try:
        from core.admin import get_const_int, get_const_float
        if isinstance(default, float):
            return get_const_float(name, default)
        return get_const_int(name, int(default))
    except Exception:
        return default


# ══════════════════════════════════════════
# 🏅 فحص وإعطاء الإنجازات
# ══════════════════════════════════════════

def check_and_award(user_id: int, condition_type: str, current_value: int):
    """
    يفحص إذا استحق المستخدم إنجازاً جديداً.
    يُستدعى بعد كل حدث مهم.
    """
    conn = get_db_conn()
    cursor = conn.cursor()

    # جلب الإنجازات المطابقة غير المكتسبة
    cursor.execute("""
        SELECT a.* FROM achievements a
        WHERE a.condition_type = ?
          AND a.condition_value <= ?
          AND a.id NOT IN (
              SELECT achievement_id FROM user_achievements WHERE user_id = ?
          )
        ORDER BY a.condition_value ASC
    """, (condition_type, current_value, user_id))

    new_achievements = cursor.fetchall()
    awarded = []

    for ach in new_achievements:
        ach = dict(ach)
        # تسجيل الإنجاز
        cursor.execute("""
            INSERT OR IGNORE INTO user_achievements (user_id, achievement_id)
            VALUES (?, ?)
        """, (user_id, ach["id"]))
        if cursor.rowcount > 0:
            awarded.append(ach)
            _give_rewards(user_id, ach, cursor)

    conn.commit()

    # إرسال إشعار واحد يجمع كل الإنجازات المكتسبة
    if awarded:
        _notify_achievements_batch(user_id, awarded)

    return awarded


def _give_rewards(user_id: int, ach: dict, cursor):
    """يُعطي مكافآت الإنجاز"""
    # مكافأة Bito
    if ach.get("reward_conis", 0) > 0:
        try:
            from database.db_queries.bank_queries import update_bank_balance
            update_bank_balance(user_id, ach["reward_conis"])
        except Exception:
            pass

    # مكافأة بطاقة
    if ach.get("reward_card_name"):
        try:
            from database.db_queries.advanced_war_queries import get_card_by_name, add_user_card
            card = get_card_by_name(ach["reward_card_name"])
            if card:
                add_user_card(user_id, card["id"], 1)
        except Exception:
            pass

    # مكافأة سمعة
    if ach.get("reward_reputation", 0) > 0:
        try:
            from database.db_queries.advanced_war_queries import update_reputation
            update_reputation(user_id, helped=ach["reward_reputation"] // 5)
        except Exception:
            pass


def _notify_achievements_batch(user_id: int, achievements: list):
    """
    يُرسل رسالة واحدة تجمع كل الإنجازات المكتسبة حديثاً.
    يجمع المكافآت المالية والسمعة في سطر ملخص واحد.
    """
    try:
        from core.bot import bot

        total_coins = sum(a.get("reward_conis", 0) or 0 for a in achievements)
        total_rep   = sum(a.get("reward_reputation", 0) or 0 for a in achievements)
        cards       = [a["reward_card_name"] for a in achievements if a.get("reward_card_name")]

        # بناء قائمة الإنجازات
        lines = []
        for ach in achievements:
            lines.append(f"{ach['emoji']} <b>{ach['name_ar']}</b>\n   📝 {ach['description_ar']}")

        msg = "🏅 <b>إنجازات جديدة!</b>\n\n" + "\n\n".join(lines)

        # ملخص المكافآت المجمعة
        rewards = []
        if total_coins > 0:
            rewards.append(f"💰 {total_coins:.0f} {CURRENCY_ARABIC_NAME}")
        if cards:
            rewards.append("🃏 " + "، ".join(cards))
        if total_rep > 0:
            rewards.append(f"⭐ +{total_rep} سمعة")

        if rewards:
            msg += "\n\n🎁 <b>المكافآت:</b>\n" + "\n".join(rewards)

        bot.send_message(user_id, msg, parse_mode="HTML")
    except Exception:
        pass


# ══════════════════════════════════════════
# 📊 جلب إنجازات المستخدم
# ══════════════════════════════════════════

def get_user_achievements(user_id: int) -> list:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, ua.unlocked_at
        FROM user_achievements ua
        JOIN achievements a ON ua.achievement_id = a.id
        WHERE ua.user_id = ?
        ORDER BY ua.unlocked_at DESC
    """, (user_id,))
    return [dict(r) for r in cursor.fetchall()]


def get_all_achievements_with_status(user_id: int) -> list:
    """
    يرجع كل الإنجازات مع حالة الاكتساب.
    الإنجازات المخفية تظهر كـ ??? حتى تُكتسب.
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*,
               CASE WHEN ua.id IS NOT NULL THEN 1 ELSE 0 END AS unlocked,
               ua.unlocked_at
        FROM achievements a
        LEFT JOIN user_achievements ua ON a.id = ua.achievement_id AND ua.user_id = ?
        ORDER BY a.category, a.condition_value
    """, (user_id,))
    rows = [dict(r) for r in cursor.fetchall()]

    # إخفاء تفاصيل الإنجازات المخفية غير المكتسبة
    for r in rows:
        if r.get("is_hidden") and not r.get("unlocked"):
            r["name_ar"]      = "🔒 إنجاز مخفي"
            r["description_ar"] = "اكتشفه بنفسك!"
            r["emoji"]        = "❓"
    return rows


def get_achievement_progress(user_id: int) -> list:
    """
    يرجع تقدم المستخدم نحو الإنجازات القادمة (غير المكتسبة).
    """
    conn = get_db_conn()
    cursor = conn.cursor()

    # جلب الإنجازات غير المكتسبة (غير المخفية فقط)
    cursor.execute("""
        SELECT a.* FROM achievements a
        WHERE a.is_hidden = 0
          AND a.id NOT IN (
              SELECT achievement_id FROM user_achievements WHERE user_id = ?
          )
        ORDER BY a.condition_value ASC
        LIMIT 5
    """, (user_id,))

    upcoming = [dict(r) for r in cursor.fetchall()]
    result   = []

    for ach in upcoming:
        current = get_user_stat(user_id, ach["condition_type"])
        target  = ach["condition_value"]
        pct     = min(100, int((current / max(1, target)) * 100))
        bar_len = 8
        filled  = int(bar_len * pct / 100)
        bar     = "█" * filled + "░" * (bar_len - filled)

        result.append({
            **ach,
            "current":  current,
            "target":   target,
            "progress": pct,
            "bar":      bar,
        })

    return result


# ══════════════════════════════════════════
# 🎯 نقاط الإحصاء للفحص
# ══════════════════════════════════════════

def get_user_stat(user_id: int, stat_type: str) -> int:
    """يجلب إحصاء معين للمستخدم"""
    conn = get_db_conn()
    cursor = conn.cursor()

    if stat_type == "battles_won":
        cursor.execute("""
            SELECT COUNT(*) FROM country_battles
            WHERE (attacker_user_id = ? OR defender_user_id = ?)
              AND winner_country_id IN (
                  SELECT id FROM countries WHERE owner_id = ?
              )
              AND status = 'finished'
        """, (user_id, user_id, user_id))

    elif stat_type == "battles_defended":
        cursor.execute("""
            SELECT COUNT(*) FROM country_battles
            WHERE defender_user_id = ?
              AND winner_country_id IN (
                  SELECT id FROM countries WHERE owner_id = ?
              )
              AND status = 'finished'
        """, (user_id, user_id))

    elif stat_type == "battles_helped":
        cursor.execute("""
            SELECT COALESCE(battles_helped, 0) FROM player_reputation WHERE user_id = ?
        """, (user_id,))

    elif stat_type == "spy_success":
        cursor.execute("""
            SELECT COUNT(*) FROM spy_operations so
            JOIN countries c ON so.attacker_country_id = c.id
            WHERE c.owner_id = ? AND so.result IN ('success', 'partial')
        """, (user_id,))

    elif stat_type == "assassinations":
        cursor.execute("""
            SELECT COUNT(*) FROM spy_operations so
            JOIN countries c ON so.attacker_country_id = c.id
            WHERE c.owner_id = ? AND so.result = 'success'
        """, (user_id,))

    elif stat_type == "balance":
        cursor.execute("SELECT COALESCE(balance, 0) FROM user_accounts WHERE user_id = ?", (user_id,))

    elif stat_type == "investments":
        cursor.execute("""
            SELECT COUNT(*) FROM bank_cooldowns WHERE user_id = ? AND type = 'invest'
        """, (user_id,))

    elif stat_type == "alliances_created":
        cursor.execute("SELECT COUNT(*) FROM alliances WHERE leader_id = ?", (user_id,))

    elif stat_type == "alliance_days":
        # أيام العضوية في التحالف الحالي
        cursor.execute("""
            SELECT CAST((strftime('%s','now') - am.joined_at) / 86400 AS INTEGER)
            FROM alliance_members am
            WHERE am.user_id = ?
            ORDER BY am.joined_at ASC LIMIT 1
        """, (user_id,))

    elif stat_type == "influence_points":
        cursor.execute("""
            SELECT COALESCE(ip.influence_points, 0)
            FROM countries c
            LEFT JOIN country_influence ip ON c.id = ip.country_id
            WHERE c.owner_id = ?
        """, (user_id,))

    elif stat_type == "no_retreat_wins":
        # انتصارات المهاجم بدون داعمين
        cursor.execute("""
            SELECT COUNT(*) FROM country_battles cb
            WHERE cb.attacker_user_id = ?
              AND cb.winner_country_id IN (SELECT id FROM countries WHERE owner_id = ?)
              AND cb.status = 'finished'
              AND NOT EXISTS (
                  SELECT 1 FROM battle_supporters bs WHERE bs.battle_id = cb.id
              )
        """, (user_id, user_id))

    elif stat_type == "detected":
        # عدد مرات اكتشاف الجاسوس
        cursor.execute("""
            SELECT COUNT(*) FROM spy_operations so
            JOIN countries c ON so.attacker_country_id = c.id
            WHERE c.owner_id = ? AND so.result = 'detected'
        """, (user_id,))

    else:
        return 0

    row = cursor.fetchone()
    return int(row[0]) if row and row[0] else 0


def trigger_achievement_check(user_id: int, event: str, **kwargs):
    """
    نقطة الدخول الموحدة — يُستدعى بعد كل حدث.
    محمي بكولداون 5 ثوانٍ لمنع التشغيل المزدوج لنفس الحدث.
    event: 'battle_won', 'spy_success', 'support_given', 'balance_updated', إلخ
    """
    # ─── حماية من التكرار السريع ───
    key = (user_id, event)
    now = time.time()
    with _trigger_lock:
        if now - _trigger_times.get(key, 0) < _TRIGGER_COOLDOWN:
            return []
        _trigger_times[key] = now

    event_to_stat = {
        "battle_won":      "battles_won",
        "battle_defended": "battles_defended",
        "support_given":   "battles_helped",
        "spy_success":     "spy_success",
        "assassination":   "assassinations",
        "spy_detected":    "detected",
        "balance_updated": "balance",
        "investment":      "investments",
        "alliance_created":"alliances_created",
        "influence_gained":"influence_points",
        "no_retreat_win":  "no_retreat_wins",
    }

    stat_type = event_to_stat.get(event)
    if not stat_type:
        return []

    current = get_user_stat(user_id, stat_type)
    return check_and_award(user_id, stat_type, current)
