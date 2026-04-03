# modules/bank/services/economy_handlers.py
import random
from database.db_queries.cities_queries import get_city_users
from modules.bank.services.bank_service import daily_reward, invest, light_risk, salary

# -------------------------------
# 🏙️ توزيع الرواتب لجميع مستخدمي مدينة
# -------------------------------
def pay_salaries_to_city_users(city_id):
    users = get_city_users(city_id)
    results = []
    for user in users:
        success, msg = salary(user["user_id"])
        results.append((user["user_id"], msg))
    return results

# -------------------------------
# 🎁 دفع المكافآت اليومية لجميع مستخدمي مدينة
# -------------------------------
def pay_daily_rewards(city_id):
    users = get_city_users(city_id)
    results = []
    for user in users:
        success, msg = daily_reward(user["user_id"])
        results.append((user["user_id"], msg))
    return results

# -------------------------------
# 🎲 التعامل مع المخاطرة الخفيفة
# -------------------------------
def handle_risk_action(user_id):
    success, msg = light_risk(user_id)
    return success, msg

# -------------------------------
# 📈 التعامل مع الاستثمار
# -------------------------------
def handle_investment_action(user_id, amount=None):
    success, msg = invest(user_id, amount)
    return success, msg