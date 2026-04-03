import math
import random

from database.connection import get_db_conn
from database.db_queries.economy_queries import get_economy_stat, set_economy_stat
from database.db_queries.bank_queries import get_user_balance


BASELINE_MONEY = 1_000_000.0


# =========================
# 💰 إجمالي فلوس النظام
# =========================
def get_total_system_money():
    try:
        conn = get_db_conn()
        cursor = conn.cursor()

        cursor.execute('SELECT SUM(balance) FROM user_accounts')
        row = cursor.fetchone()

        return float(row[0]) if row and row[0] else 0.0

    except:
        return 0.0


# =========================
# 📈 التضخم
# =========================
def compute_inflation_index():
    current_money = get_total_system_money() or BASELINE_MONEY

    inflation = current_money / BASELINE_MONEY
    inflation = max(0.75, min(inflation, 2.5))

    set_economy_stat('inflation', inflation)
    return inflation


def get_inflation_index():
    return get_economy_stat('inflation', 1.0)


# =========================
# 🧲 تقليل التضخم
# =========================
def money_sink(amount):
    sink = get_economy_stat('sink', 0.0)
    sink += amount
    set_economy_stat('sink', sink)
    return sink


# =========================
# 📉 تقليل قوة الأغنياء
# =========================
def soft_cap_multiplier(balance):
    if balance <= 5000:
        return 1.0

    return max(0.15, 1.0 - math.log1p(balance / 10000.0) * 0.18)


# =========================
# 🎲 أحداث عشوائية
# =========================
def event_generator():
    if random.random() > 0.12:
        return None

    events = [
        ('💰 اكتشاف ذهب', 1.12),
        ('📉 أزمة اقتصادية', 0.82),
        ('📊 ازدهار تجاري', 1.08),
        ('🏛 زيادة ضرائب', 0.90),
    ]

    name, multiplier = random.choice(events)

    set_economy_stat('event_multiplier', multiplier)
    return name, multiplier


def get_event_multiplier():
    return get_economy_stat('event_multiplier', 1.0)


# =========================
# 💵 تعديل الرواتب
# =========================
def adapt_salary_amount(base_amount, user_id):

    balance = get_user_balance(user_id)
    global_money = get_total_system_money()

    inflation = get_inflation_index()
    cap = soft_cap_multiplier(balance)
    event = get_event_multiplier()

    adjusted = base_amount * cap / inflation * event
    adjusted = max(20.0, min(adjusted, base_amount * 2.0))

    return adjusted


# =========================
# 📊 استثمار
# =========================
def adapt_investment_outcome(amount):

    inflation = get_inflation_index()

    risk_increase = max(0.0, min(0.45, (amount - 1000) / 2000))

    if random.random() < (0.40 + risk_increase):

        profit_pct = random.uniform(4, 14) / (1 + inflation * 0.35)
        delta = amount * profit_pct / 100
        result = 'profit'

    else:
        loss_pct = random.uniform(4, 22) + (risk_increase * 15)
        delta = -amount * loss_pct / 100
        result = 'loss'

    delta = max(-amount, min(delta, amount * 0.35))

    return result, delta