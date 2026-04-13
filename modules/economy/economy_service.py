"""
خدمة الاقتصاد — جمع الدخل اليومي وتطبيقه على رصيد اللاعبين.

الدورة الاقتصادية (تُشغَّل يومياً):
  لكل دولة:
    net = income - maintenance
    إذا net > 0  → أضف net لرصيد المالك
    إذا net < 0  → اخصم الفرق (يُسمح بالرصيد السالب)

اللاعب يمكنه أيضاً جمع دخله يدوياً بأمر "دخل".
"""
import time
from database.connection import get_db_conn
from database.db_queries.bank_queries import update_bank_balance, get_user_balance
from database.db_queries.economy_queries import calculate_country_economy
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

# كولداون جمع الدخل اليدوي (ثواني) — 6 ساعات
INCOME_COLLECT_COOLDOWN = 6 * 3600


def collect_income_for_country(country_id: int, owner_user_id: int) -> dict:
    """
    يحسب صافي الدخل (income - maintenance) ويطبقه على رصيد المالك.
    يرجع dict: {net, income, maintenance, applied, message}
    """
    economy = calculate_country_economy(country_id)
    income      = round(economy["income"], 2)
    maintenance = round(economy["maintenance"], 2)
    net         = round(income - maintenance, 2)

    if net == 0:
        return {
            "net": 0, "income": income, "maintenance": maintenance,
            "applied": False,
            "message": "⚖️ الدخل يساوي الصيانة — لا تغيير في الرصيد."
        }

    # تطبيق صافي الدخل (موجب أو سالب)
    update_bank_balance(owner_user_id, net)

    # تحديث last_update_time في city_budget
    _touch_city_budgets(country_id)

    # increment collect_income task counter for each city
    try:
        from database.db_queries.daily_tasks_queries import increment_income_collected
        conn2 = get_db_conn()
        cur2  = conn2.cursor()
        cur2.execute("SELECT id FROM cities WHERE country_id = ?", (country_id,))
        for city_row in cur2.fetchall():
            increment_income_collected(city_row[0])
    except Exception:
        pass

    if net > 0:
        msg = (
            f"💰 <b>دخل المدن:</b> +{income:.0f} {CURRENCY_ARABIC_NAME}\n"
            f"🔧 <b>الصيانة:</b> -{maintenance:.0f} {CURRENCY_ARABIC_NAME}\n"
            f"✅ <b>صافي الدخل:</b> +{net:.0f} {CURRENCY_ARABIC_NAME} أُضيفت لرصيدك!"
        )
    else:
        msg = (
            f"💰 <b>دخل المدن:</b> +{income:.0f} {CURRENCY_ARABIC_NAME}\n"
            f"🔧 <b>الصيانة:</b> -{maintenance:.0f} {CURRENCY_ARABIC_NAME}\n"
            f"⚠️ <b>الصيانة تتجاوز الدخل!</b> خُصم {abs(net):.0f} {CURRENCY_ARABIC_NAME} من رصيدك.\n"
            f"💡 ابنِ مزيداً من المباني الاقتصادية لزيادة الدخل."
        )

    return {
        "net": net, "income": income, "maintenance": maintenance,
        "applied": True, "message": msg
    }


def collect_income_for_all():
    """
    يُشغَّل من daily_tasks — يجمع الدخل لكل الدول.
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, owner_id FROM countries")
    countries = cursor.fetchall()

    for row in countries:
        country_id = row[0] if not isinstance(row, dict) else row["id"]
        owner_id   = row[1] if not isinstance(row, dict) else row["owner_id"]
        try:
            collect_income_for_country(country_id, owner_id)
        except Exception as e:
            print(f"[Economy] خطأ في جمع دخل الدولة {country_id}: {e}")


def can_collect_income(country_id: int) -> tuple[bool, int]:
    """
    يتحقق من كولداون جمع الدخل اليدوي.
    يرجع (True, 0) إذا مسموح، أو (False, ثواني_متبقية).
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT MIN(last_update_time) FROM city_budget WHERE city_id IN "
        "(SELECT id FROM cities WHERE country_id = ?)",
        (country_id,)
    )
    row = cursor.fetchone()
    if not row or row[0] is None:
        return True, 0

    last = int(row[0])
    now  = int(time.time())
    elapsed = now - last

    if elapsed >= INCOME_COLLECT_COOLDOWN:
        return True, 0
    return False, INCOME_COLLECT_COOLDOWN - elapsed


def _touch_city_budgets(country_id: int):
    """يُحدّث last_update_time لكل مدن الدولة بعد جمع الدخل"""
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute(
        "UPDATE city_budget SET last_update_time = ? "
        "WHERE city_id IN (SELECT id FROM cities WHERE country_id = ?)",
        (now, country_id)
    )
    conn.commit()


def get_income_summary(country_id: int) -> dict:
    """يرجع ملخص الاقتصاد للعرض في واجهة المستخدم"""
    economy = calculate_country_economy(country_id)
    income      = round(economy["income"], 2)
    maintenance = round(economy["maintenance"], 2)
    net         = round(income - maintenance, 2)

    can_collect, remaining = can_collect_income(country_id)
    from utils.helpers import format_remaining_time

    return {
        "income":      income,
        "maintenance": maintenance,
        "net":         net,
        "can_collect": can_collect,
        "cooldown_remaining": remaining,
        "cooldown_display": format_remaining_time(remaining) if remaining > 0 else "جاهز",
    }
