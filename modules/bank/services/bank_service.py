# modules/bank/services/bank_services.py
import random
import time
from database.db_queries.bank_queries import (
    check_bank_account, get_user_balance, update_bank_balance,
    can_use_cooldown, set_cooldown,
    create_loan, repay_loan, get_active_loans
)
from modules.bank.utils.constants import (
    SALARY_AMOUNT, SALARY_COOLDOWN,
    TASK_REWARDS, DAILY_REWARD,
    RISK_RANGE, RISK_COOLDOWN,
    INVEST_MIN, INVEST_COOLDOWN
)
from utils.helpers import format_remaining_time
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

# -------------------------------
# ⚡️ الرواتب
# -------------------------------
def salary(user_id, username=None):
    ok, remain = can_use_cooldown(user_id, "salary", SALARY_COOLDOWN)
    if not ok:
        return False, f"⏳ يمكنك أخذ الراتب بعد {format_remaining_time(remain)}"
    amount = SALARY_AMOUNT
    try:
        from modules.progression.global_events import get_event_effect
        bonus = get_event_effect("salary_bonus")
        if bonus > 0:
            amount = round(amount * (1 + bonus))
    except Exception:
        pass
    update_bank_balance(user_id, amount)
    set_cooldown(user_id, "salary")
    return True, f"💰 تم صرف راتبك اليومي: {amount} {CURRENCY_ARABIC_NAME}"

# -------------------------------
# 📝 المهام الصغيرة
# -------------------------------
def small_task(user_id):
    ok, remain = can_use_cooldown(user_id, "small_task", 3600)
    if not ok:
        return False, f"⏳ يمكنك عمل مهمة أخرى بعد {format_remaining_time(remain)}"
    reward = random.choice(TASK_REWARDS)
    update_bank_balance(user_id, reward)
    set_cooldown(user_id, "small_task")
    return True, f"📝 أنهيت المهمة وحصلت على: {reward} {CURRENCY_ARABIC_NAME}"

# -------------------------------
# 🎁 المكافأة اليومية
# -------------------------------
def daily_reward(user_id):
    ok, remain = can_use_cooldown(user_id, "daily", 86400)
    if not ok:
        return False, f"⏳ يمكنك أخذ المكافأة اليومية بعد {format_remaining_time(remain)}"
    reward = random.choice(DAILY_REWARD)
    try:
        from modules.progression.global_events import get_event_effect
        bonus = get_event_effect("salary_bonus")
        if bonus > 0:
            reward = round(reward * (1 + bonus))
    except Exception:
        pass
    update_bank_balance(user_id, reward)
    set_cooldown(user_id, "daily")
    return True, f"🎁 حصلت على مكافأتك اليومية: {reward} {CURRENCY_ARABIC_NAME}"

# -------------------------------
# 🎲 المخاطرة الخفيفة
# -------------------------------
def light_risk(user_id):
    ok, remain = can_use_cooldown(user_id, "light_risk", RISK_COOLDOWN)
    if not ok:
        return False, f"⏳ يمكنك تجربة المخاطرة بعد {format_remaining_time(remain)}"
    change = random.randint(*RISK_RANGE)
    update_bank_balance(user_id, change)
    set_cooldown(user_id, "light_risk")
    if change >= 0:
        return True, f"🎲 نجاح المخاطرة! ربحت {change} {CURRENCY_ARABIC_NAME}"
    return True, f"🎲 فشلت المخاطرة! خسرت {-change} {CURRENCY_ARABIC_NAME}"

# -------------------------------
# 📈 الاستثمار
# -------------------------------
def invest(user_id, amount=None):
    ok, remain = can_use_cooldown(user_id, "invest", INVEST_COOLDOWN)
    if not ok:
        return False, f"⏳ يمكنك الاستثمار بعد {format_remaining_time(remain)}"

    balance = get_user_balance(user_id)
    if amount is None or amount > balance:
        amount = balance
    if amount < INVEST_MIN:
        return False, f"❌ الحد الأدنى للاستثمار {INVEST_MIN} {CURRENCY_ARABIC_NAME}"

    outcome = random.choices(["profit", "loss"], weights=[0.65, 0.35])[0]
    percent = random.uniform(0.05, 0.2)
    change = round(amount * percent, 2)
    if outcome == "loss":
        change = -change
    update_bank_balance(user_id, change)
    set_cooldown(user_id, "invest")
    if change >= 0:
        return True, f"📈 استثمار ناجح! ربحت {change} {CURRENCY_ARABIC_NAME}"
    return True, f"📉 استثمار خاسر! خسرت {-change} {CURRENCY_ARABIC_NAME}"

# -------------------------------
# 💵 القروض
# -------------------------------
def take_loan(user_id, amount):
    return create_loan(user_id, amount)

def repay_user_loan(user_id, loan_id, amount):
    return repay_loan(user_id, loan_id, amount)

def list_loans(user_id):
    loans = get_active_loans(user_id)
    if not loans:
        return "❌ ليس لديك أي قروض نشطة"
    text = "💳 القروض النشطة:\n\n"
    import time as _time
    now = int(_time.time())
    for l in loans:
        loan_id, amount, due_date, repaid, status = l[0], l[1], l[2], l[3], l[4]
        # غرامة التأخير 5% مرة واحدة فقط
        penalty = round(amount * 0.05, 2) if status == 'overdue' else 0
        total_due = round(amount + penalty, 2)
        remaining = round(total_due - repaid, 2)
        status_label = "⚠️ متأخر" if status == 'overdue' else "✅ نشط"
        text += (
            f"🔹 قرض #{loan_id} — {status_label}\n"
            f"   المبلغ الأصلي: {amount} {CURRENCY_ARABIC_NAME}\n"
        )
        if penalty:
            text += f"   غرامة التأخير: {penalty} {CURRENCY_ARABIC_NAME}\n"
        text += (
            f"   إجمالي المستحق: {total_due} {CURRENCY_ARABIC_NAME}\n"
            f"   المسدد: {repaid} {CURRENCY_ARABIC_NAME}\n"
            f"   المتبقي: {remaining} {CURRENCY_ARABIC_NAME}\n"
            f"   الموعد النهائي: {_time.strftime('%Y-%m-%d', _time.localtime(due_date))}\n\n"
        )
    text += "للتسديد: تسديد القرض [رقم القرض] [المبلغ]"
    return text

# -------------------------------
# 🏙 مشتريات حسب المدينة
# -------------------------------
def purchase_in_city(user_id, building_name, price):
    from database.db_queries.cities_queries import get_user_city
    city = get_user_city(user_id)
    if not city:
        return False, "❌ يجب أن تكون داخل مدينة للشراء"
    update_bank_balance(user_id, -price)
    return True, f"🏗 تم شراء {building_name} في {city['name']} مقابل {price} {CURRENCY_ARABIC_NAME}"

# -------------------------------
# ⚡️ Precheck قبل التنفيذ
# -------------------------------
def can_purchase(user_id, price):
    from database.db_queries.cities_queries import get_user_city
    balance = get_user_balance(user_id)
    if balance < price:
        return False, f"❌ رصيدك لا يكفي ({balance:.2f} {CURRENCY_ARABIC_NAME})"
    city = get_user_city(user_id)
    if not city:
        return False, "❌ يجب أن تكون داخل مدينة للشراء"
    return True, ""

def can_risk(user_id):
    balance = get_user_balance(user_id)
    if balance <= 0:
        return False, "❌ لا يمكن المخاطرة برصيد صفر أو أقل"
    return True, ""

def can_invest(user_id, amount):
    balance = get_user_balance(user_id)
    if amount is None:
        amount = balance
    if amount < INVEST_MIN:
        return False, f"❌ الحد الأدنى للاستثمار {INVEST_MIN} {CURRENCY_ARABIC_NAME}"
    if amount > balance:
        return False, f"❌ رصيدك لا يكفي ({balance:.2f} {CURRENCY_ARABIC_NAME})"
    return True, ""

def can_take_loan(user_id, amount):
    if amount < 0:
        return False, "❌ لا يمكن أخذ قرض بالسالب"
    from core.admin import get_const_int
    max_loan = get_const_int("max_loan_amount", 10000)
    if amount > max_loan:
        return False, f"❌ الحد الأقصى للقرض هو {max_loan}"
    return True, ""

def repay_user_loan(user_id, loan_id, amount):
    return repay_loan(user_id, loan_id, amount)
