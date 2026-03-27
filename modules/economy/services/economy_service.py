import math
import random
from database.connection import get_db_conn
from database.db_queries import (
    get_economy_stat,
    set_economy_stat,
    get_user_balance
)

BASELINE_MONEY = 1_000_000.0
TARGET_INFLATION = 1.0


def get_total_system_money():
    liben_bank = 0.0
    liben_user = 0.0

    try:
            conn = get_db_conn()
            cursor = conn.cursor()
            cursor.execute('SELECT SUM(balance) FROM user_accounts')
            row = cursor.fetchone()
            liben_bank = float(row[0]) if row and row[0] is not None else 0.0

            cursor.execute('SELECT SUM(balance) FROM user_accounts')
            row2 = cursor.fetchone()
            liben_user = float(row2[0]) if row2 and row2[0] is not None else 0.0
    except Exception:
        liben_bank = 0.0
        liben_user = 0.0

    return liben_bank + liben_user


def compute_inflation_index():
    current_money = get_total_system_money() or BASELINE_MONEY
    inflation = current_money / BASELINE_MONEY
    inflation = max(0.75, min(inflation, 2.5))
    set_economy_stat('inflation', inflation)
    return inflation


def get_inflation_index():
    return get_economy_stat('inflation', 1.0)


def money_sink(amount):
    # adds a money sink effect by reducing global pool estimate
    # (for deterministic behavior, we store a counter)
    gates = get_economy_stat('sink', 0.0)
    gates += amount
    set_economy_stat('sink', gates)
    return gates


def soft_cap_multiplier(balance):
    if balance <= 5000:
        return 1.0
    return max(0.15, 1.0 - math.log1p(balance / 10000.0) * 0.18)


def event_generator():
    if random.random() > 0.12:
        return None

    events = [
        ('Gold discovered', 1.12),
        ('Economic crisis', 0.82),
        ('Trade boom', 1.08),
        ('Taxation surge', 0.90),
    ]
    name, multiplier = random.choice(events)

    set_economy_stat('event_multiplier', multiplier)
    return name, multiplier


def get_event_multiplier():
    return get_economy_stat('event_multiplier', 1.0)


def adapt_salary_amount(base_amount, user_id):
    balance = get_user_balance(user_id)
    global_balance = get_user_balance(user_id)
    inflation = get_inflation_index()
    cap = soft_cap_multiplier(balance + global_balance)
    event = get_event_multiplier()

    adjusted = base_amount * cap / inflation * event
    adjusted = max(20.0, min(adjusted, base_amount * 2.0))

    return adjusted


def adapt_investment_outcome(amount):
    inflation = get_inflation_index()

    if amount > 1000:
        risk_increase = min(0.45, (amount - 1000) / 2000)
    else:
        risk_increase = 0.0

    if random.random() < (0.40 + risk_increase):
        profit_pct = random.uniform(4, 14) / (1 + inflation * 0.35)
        result = 'profit'
        delta = amount * profit_pct / 100
    else:
        loss_pct = random.uniform(4, 22) + (risk_increase * 15)
        result = 'loss'
        delta = -amount * loss_pct / 100

    delta = max(-amount, min(delta, amount * 0.35))
    return result, delta