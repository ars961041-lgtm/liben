"""
نظام صيانة الجيش — تكلفة ساعية، تأثير على القوة عند التأخر
منفصل تماماً — يُستدعى من الـ live_battle_engine والـ daily_tasks
"""
import time

from database.connection import get_db_conn
from database.db_queries.countries_queries import get_all_cities_of_country_by_country_id
from modules.war.power_calculator import get_country_power


def _c(name: str, default):
    try:
        from core.admin import get_const_float, get_const_int
        if isinstance(default, float):
            return get_const_float(name, default)
        return get_const_int(name, int(default))
    except Exception:
        return default


# ══════════════════════════════════════════
# 💰 حساب تكلفة الصيانة
# ══════════════════════════════════════════

def calculate_maintenance_cost(country_id: int) -> float:
    """
    يحسب التكلفة الساعية للصيانة:
    cost = army_power × maintenance_rate
    """
    power = get_country_power(country_id)
    rate  = _c("maintenance_rate", 0.01)

    # تخفيض من المستشفيات
    hospital_reduction = _get_hospital_reduction(country_id)

    # تخفيض من ترقيات التحالف
    alliance_reduction = _get_alliance_maintenance_reduction(country_id)

    effective_rate = max(0.001, rate * (1 - hospital_reduction) * (1 - alliance_reduction))
    return max(0.0, power * effective_rate)


def _get_hospital_reduction(country_id: int) -> float:
    """تخفيض من المستشفيات (حتى 20%)"""
    try:
        from database.db_queries.assets_queries import get_city_assets
        cities = get_all_cities_of_country_by_country_id(country_id)
        total_hospitals = 0
        for city in cities:
            cid = city["id"] if isinstance(city, dict) else city[0]
            assets = get_city_assets(cid)
            for a in assets:
                if a.get("name", "").lower() in ("hospital", "clinic"):
                    total_hospitals += a.get("quantity", 0) * a.get("level", 1)
        return min(0.20, total_hospitals * 0.01)
    except Exception:
        return 0.0


def _get_alliance_maintenance_reduction(country_id: int) -> float:
    """تخفيض من ترقيات التحالف (حتى 15%)"""
    try:
        from database.db_queries.alliances_queries import get_alliance_by_country, get_alliance_effect
        alliance = get_alliance_by_country(country_id)
        if not alliance:
            return 0.0
        # ترقية الإمداد تُقلل الصيانة
        loot_bonus = get_alliance_effect(alliance["id"], "loot_bonus")
        return min(0.15, loot_bonus * 0.5)
    except Exception:
        return 0.0


# ══════════════════════════════════════════
# 💳 دفع الصيانة
# ══════════════════════════════════════════

def ensure_maintenance_record(country_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO army_maintenance (country_id, hourly_cost, last_paid_at, debt)
        VALUES (?, 0, ?, 0)
    """, (country_id, int(time.time())))
    conn.commit()


def process_maintenance(country_id: int, owner_user_id: int) -> dict:
    """
    يعالج الصيانة المستحقة.
    يرجع dict: {paid, debt, power_penalty, message}
    """
    ensure_maintenance_record(country_id)

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM army_maintenance WHERE country_id = ?", (country_id,))
    row = cursor.fetchone()
    if not row:
        return {"paid": 0, "debt": 0, "power_penalty": 0.0, "message": ""}

    record = dict(row)
    now    = int(time.time())
    hours_elapsed = max(0, (now - record["last_paid_at"]) / 3600)

    if hours_elapsed < 0.1:
        return {"paid": 0, "debt": record["debt"], "power_penalty": 0.0, "message": ""}

    hourly_cost = calculate_maintenance_cost(country_id)
    total_due   = hourly_cost * hours_elapsed + record["debt"]

    if total_due <= 0:
        cursor.execute("UPDATE army_maintenance SET last_paid_at = ? WHERE country_id = ?",
                       (now, country_id))
        conn.commit()
        return {"paid": 0, "debt": 0, "power_penalty": 0.0, "message": ""}

    from database.db_queries.bank_queries import get_user_balance, deduct_user_balance
    balance = get_user_balance(owner_user_id)

    if balance >= total_due:
        # دفع كامل
        deduct_user_balance(owner_user_id, total_due)
        cursor.execute("""
            UPDATE army_maintenance SET last_paid_at = ?, debt = 0, hourly_cost = ?
            WHERE country_id = ?
        """, (now, hourly_cost, country_id))
        conn.commit()
        return {
            "paid": total_due, "debt": 0, "power_penalty": 0.0,
            "message": f"💸 دُفعت صيانة الجيش: {total_due:.0f} Liben"
        }
    else:
        # دفع جزئي — تراكم الدين
        paid = balance
        remaining_debt = total_due - paid
        if paid > 0:
            deduct_user_balance(owner_user_id, paid)

        # حساب عقوبة القوة
        grace_hours = _c("maintenance_grace_h", 6)
        debt_hours  = remaining_debt / max(1, hourly_cost)
        penalty_pct = min(0.40, max(0.0, (debt_hours - grace_hours) * 0.05))

        cursor.execute("""
            UPDATE army_maintenance SET last_paid_at = ?, debt = ?, hourly_cost = ?
            WHERE country_id = ?
        """, (now, remaining_debt, hourly_cost, country_id))
        conn.commit()

        msg = ""
        if penalty_pct > 0:
            msg = (
                f"⚠️ <b>تحذير: دين الصيانة!</b>\n"
                f"الدين: {remaining_debt:.0f} Liben\n"
                f"عقوبة القوة: -{int(penalty_pct*100)}%\n"
                f"ادفع الدين لاستعادة قوتك الكاملة!"
            )

        return {
            "paid": paid, "debt": remaining_debt,
            "power_penalty": penalty_pct, "message": msg
        }


def get_maintenance_penalty(country_id: int) -> float:
    """يرجع نسبة عقوبة القوة بسبب الدين (0.0–0.40)"""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT debt, hourly_cost FROM army_maintenance WHERE country_id = ?",
                       (country_id,))
        row = cursor.fetchone()
        if not row or row[0] <= 0:
            return 0.0
        debt, hourly = row[0], max(1, row[1])
        grace_hours  = _c("maintenance_grace_h", 6)
        debt_hours   = debt / hourly
        return min(0.40, max(0.0, (debt_hours - grace_hours) * 0.05))
    except Exception:
        return 0.0


# ══════════════════════════════════════════
# 📊 إحصائيات دعم التحالف
# ══════════════════════════════════════════

def record_alliance_support(alliance_id: int, user_id: int,
                             power_contributed: float = 0,
                             resource_sent: float = 0):
    """يُسجّل مساهمة الدعم في إحصائيات التحالف"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alliance_support_stats
            (alliance_id, user_id, battles_supported, total_power_contributed,
             resource_sent, last_support_at)
        VALUES (?, ?, 1, ?, ?, ?)
        ON CONFLICT(alliance_id, user_id) DO UPDATE SET
            battles_supported = battles_supported + 1,
            total_power_contributed = total_power_contributed + ?,
            resource_sent = resource_sent + ?,
            last_support_at = ?
    """, (alliance_id, user_id, power_contributed, resource_sent, int(time.time()),
          power_contributed, resource_sent, int(time.time())))
    conn.commit()


def get_alliance_support_leaderboard(alliance_id: int) -> list:
    """يرجع ترتيب الداعمين في التحالف"""
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            ass.user_id,
            ass.battles_supported,
            ass.total_power_contributed,
            ass.resource_sent,
            COALESCE(un.name, 'مجهول') AS name
        FROM alliance_support_stats ass
        LEFT JOIN users_name un ON ass.user_id = un.user_id
        WHERE ass.alliance_id = ?
        ORDER BY ass.total_power_contributed DESC
    """, (alliance_id,))

    return [dict(r) for r in cursor.fetchall()]
# ══════════════════════════════════════════
# 🔔 تحذيرات الصيانة
# ══════════════════════════════════════════

def send_maintenance_warning(country_id: int, owner_user_id: int):
    """يُرسل تحذيراً للمستخدم إذا كان الدين مرتفعاً"""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT debt, hourly_cost FROM army_maintenance WHERE country_id = ?",
                       (country_id,))
        row = cursor.fetchone()
        if not row or row[0] <= 0:
            return

        debt, hourly = row[0], max(1, row[1])
        debt_block = _c("maintenance_debt_block", 200)
        penalty    = get_maintenance_penalty(country_id)

        if debt >= debt_block * 0.7:  # تحذير عند 70% من الحد
            from core.bot import bot
            msg = (
                f"⚠️ <b>تحذير: دين الصيانة!</b>\n\n"
                f"💸 الدين الحالي: {debt:.0f} Liben\n"
                f"⏱️ التكلفة الساعية: {hourly:.0f} Liben\n"
            )
            if penalty > 0:
                msg += f"📉 عقوبة القوة: -{int(penalty*100)}%\n"
            if debt >= debt_block:
                msg += f"\n🚫 <b>الهجوم محظور حتى تسديد الدين!</b>"
            else:
                msg += f"\n⚠️ الهجوم سيُحظر عند {debt_block:.0f} Liben دين."

            try:
                bot.send_message(owner_user_id, msg, parse_mode="HTML")
            except Exception:
                pass
    except Exception:
        pass


def run_maintenance_for_all():
    """يُشغَّل من daily_tasks — يعالج صيانة كل الدول"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT c.id, c.owner_id FROM countries c")
    countries = cursor.fetchall()

    for row in countries:
        country_id, owner_id = row[0], row[1]
        try:
            result = process_maintenance(country_id, owner_id)
            if result.get("debt", 0) > 0:
                send_maintenance_warning(country_id, owner_id)
        except Exception:
            pass
