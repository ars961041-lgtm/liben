import random

from database.db_queries.bank_queries import (
    can_use_cooldown,
    get_user_balance,
    set_cooldown,
    update_bank_balance,
    create_bank_account as db_create_bank_account,
    check_bank_account
)

from modules.bank.utils.constants import (
    SALARY_COOLDOWN_SEC,
    DAILY_COOLDOWN_SEC,
    SMALL_TASK_COOLDOWN_SEC,
    LIGHT_RISK_COOLDOWN_SEC,
    INVEST_COOLDOWN_SEC,
    JOBS,
    SMALL_TASKS,
)

from modules.economy.services.economy_service import (
    compute_inflation_index, 
    get_inflation_index, 
    adapt_salary_amount, 
    adapt_investment_outcome, 
    soft_cap_multiplier, 
    event_generator, money_sink
)
from utils.helpers import format_remaining_time


# -------------------------------
# Ensure bank account
# -------------------------------

def ensure_bank_account(user_id):
    has_account, msg = check_bank_account(user_id)
    if not has_account:
        return False, msg
    return True, None


# -------------------------------
# Create bank account
# -------------------------------

def create_bank_account(user_id):

    has_account, msg = check_bank_account(user_id)

    if has_account:
        return False, "❌ لديك بالفعل حساب بنكي"

    success = db_create_bank_account(user_id, initial_balance=1000.0)

    if not success:
        return False, "❌ حدث خطأ أثناء إنشاء الحساب"

    return True, "🏦 تم إنشاء حساب بنكي بنجاح!\n💰 رصيدك الابتدائي: 1000 Liben"


# -------------------------------
# Salary
# -------------------------------

def salary(user_id, username):

    ok, msg = ensure_bank_account(user_id)
    if not ok:
        return False, msg

    can_use, remaining = can_use_cooldown(user_id, 'salary', SALARY_COOLDOWN_SEC)

    if not can_use:
        time_text = format_remaining_time(int(remaining))
        return False, f"⏳ يمكنك استلام راتبك بعد {time_text}"

    job, emoji = random.choice(JOBS)

    compute_inflation_index()

    base_amount = random.randint(200, 600)
    amount = adapt_salary_amount(base_amount, user_id)

    update_bank_balance(user_id, amount)

    set_cooldown(user_id, 'salary')

    balance = get_user_balance(user_id)

    text = (
        f"📥 إشعار إيداع\n"
        f"👤 {username}\n"
        f"💰 المبلغ: {amount:.2f} Liben\n"
        f"💼 الوظيفة: {job} {emoji}\n"
        f"🏦 رصيدك الحالي: {balance:.2f} Liben"
    )

    return True, text


# -------------------------------
# Daily reward
# -------------------------------

def daily_reward(user_id):

    ok, msg = ensure_bank_account(user_id)
    if not ok:
        return False, msg

    can_use, remaining = can_use_cooldown(user_id, 'daily', DAILY_COOLDOWN_SEC)

    if not can_use:
        time_text = format_remaining_time(int(remaining))
        return False, f"⏳ الجائزة اليومية بعد {time_text}"

    amount = random.randint(150, 400)

    update_bank_balance(user_id, amount)

    set_cooldown(user_id, 'daily')

    balance = get_user_balance(user_id)

    text = (
        f"🎁 الجائزة اليومية\n"
        f"💰 ربحت: {amount} Liben\n"
        f"🏦 رصيدك: {balance:.2f} Liben"
    )

    return True, text


# -------------------------------
# Small task
# -------------------------------

def small_task(user_id):

    ok, msg = ensure_bank_account(user_id)
    if not ok:
        return False, msg

    can_use, remaining = can_use_cooldown(user_id, 'small_task', SMALL_TASK_COOLDOWN_SEC)

    if not can_use:
        time_text = format_remaining_time(int(remaining))
        return False, f"⏳ يمكنك تنفيذ مهمة بعد {time_text}"

    task = random.choice(SMALL_TASKS)
    reward = random.randint(50, 150)

    update_bank_balance(user_id, reward)

    set_cooldown(user_id, 'small_task')

    balance = get_user_balance(user_id)

    text = (
        f"🛠 مهمة صغيرة\n"
        f"{task}\n"
        f"💰 المكافأة: {reward} Liben\n"
        f"🏦 رصيدك: {balance:.2f} Liben"
    )

    return True, text


# -------------------------------
# Light risk
# -------------------------------

def light_risk(user_id):

    ok, msg = ensure_bank_account(user_id)
    if not ok:
        return False, msg

    can_use, remaining = can_use_cooldown(user_id, 'light_risk', LIGHT_RISK_COOLDOWN_SEC)

    if not can_use:
        time_text = format_remaining_time(int(remaining))
        return False, f"⏳ حاول لاحقًا بعد {time_text}"

    win = random.choice([True, False])

    amount = random.randint(100, 300)

    if win:
        update_bank_balance(user_id, amount)
        result = f"🎲 ربحت {amount} Liben!"
    else:
        update_bank_balance(user_id, -amount)
        result = f"💸 خسرت {amount} Liben!"

    set_cooldown(user_id, 'light_risk')

    balance = get_user_balance(user_id)

    text = (
        f"⚡ مخاطرة بسيطة\n"
        f"{result}\n"
        f"🏦 رصيدك: {balance:.2f} Liben"
    )

    return True, text


# -------------------------------
# Invest
# -------------------------------
def invest(user_id, amount):
    ok, msg = ensure_bank_account(user_id)
    if not ok:
        return False, msg

    can_use, remaining = can_use_cooldown(user_id, 'invest', INVEST_COOLDOWN_SEC)
    if not can_use:
        time_text = format_remaining_time(int(remaining))
        return False, f"⏳ يمكنك الاستثمار بعد {time_text}"

    balance = get_user_balance(user_id)

    if amount is None or amount <= 0:
        return False, "❌ اكتب المبلغ الذي تريد استثماره بشكل صحيح"

    if amount > balance:
        return False, "❌ ليس لديك رصيد كافٍ"

    # حساب الربح أو الخسارة
    profit = round(amount * random.uniform(-0.3, 0.6), 2)
    update_bank_balance(user_id, profit)
    set_cooldown(user_id, 'invest')
    new_balance = get_user_balance(user_id)

    # رسالة ذكية حسب النتيجة
    if profit > 0:
        result_text = f"🎉 مبروك! ربحت {profit:.2f} Liben من استثمارك 💰"
    elif profit < 0:
        result_text = f"😢 للأسف خسرت {abs(profit):.2f} Liben. لا تيأس، حاول مرة أخرى!"
    else:
        result_text = "😐 لم تربح أو تخسر شيئًا هذه المرة، حاول مرة أخرى!"

    # نص كامل للمستخدم
    text = (
        f"📊 نتيجة الاستثمار\n"
        f"{result_text}\n"
        f"🏦 رصيدك الحالي: {new_balance:.2f} Liben"
    )

    return True, text
