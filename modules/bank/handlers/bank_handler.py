from database.db_queries.bank_queries import check_bank_account, get_user_balance
from modules.bank.services.bank_service import (
    create_bank_account,
    salary,
    invest,
    daily_reward,
    small_task,
    light_risk,
    format_top_richest
)

from utils.helpers import send_reply

def ensure_bank_account(message, user_id):
    has_account, msg = check_bank_account(user_id)
    if not has_account:
        send_reply(message, msg)
        return False
    return True

def bank_commands(message):
    text = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    # Top richest
    if text == "توب الفلوس":
        top_text = format_top_richest(user_id, username=username, limit=20)
        send_reply(message, top_text)
        return True

    # Create bank account
    if text in ["إنشاء حساب بنكي", "انشاء حساب بتكي"]:
        success, result = create_bank_account(user_id)
        send_reply(message, result)
        return True

    # Salary
    if text == "راتب":
        if not ensure_bank_account(message, user_id):
            return True
        success, result = salary(user_id, username)
        send_reply(message, result)
        return True

    # Invest
    if text.startswith("استثمار فلوسي"):
        if not ensure_bank_account(message, user_id):
            return True
        
        parts = text.split()
        if len(parts) == 2:
            amount = get_user_balance(user_id)
        elif len(parts) == 3:
            try:
                amount = float(parts[2])
            except ValueError:
                amount = None
        else:
            amount = None

        success, result = invest(user_id, amount)
        send_reply(message, result)
        return True

    # Daily reward
    if text == "يومي":
        if not ensure_bank_account(message, user_id):
            return True
        success, result = daily_reward(user_id)
        send_reply(message, result)
        return True

    # Small task
    if text == "مهمة":
        if not ensure_bank_account(message, user_id):
            return True
        success, result = small_task(user_id)
        send_reply(message, result)
        return True

    # Light risk
    if text == "مخاطرة":
        if not ensure_bank_account(message, user_id):
            return True
        success, result = light_risk(user_id)
        send_reply(message, result)
        return True

    if text == "فلوسي":
        if not ensure_bank_account(message, user_id):
            return True
        balance = get_user_balance(user_id)
        send_reply(message, f"💰 رصيدك: {balance:.2f} Liben")
        return True
    
    return False