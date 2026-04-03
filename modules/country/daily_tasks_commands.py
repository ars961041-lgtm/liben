from database.db_queries.daily_tasks_queries import (
    show_daily_tasks,
    collect_daily_task_rewards,
    get_user_city,  # ← استدعاء دالة المدينة
)
from core.bot import bot

def daily_tasks_commands(message):
    """التعامل مع أوامر المهام اليومية: 'مهامي' و 'جائزة مهامي'"""
    if not message.text:
        return False

    text = message.text.strip()
    user_id = message.from_user.id

    if text not in ["مهامي", "جائزة مهامي"]:
        return False

    try:
        # ───── الحصول على مدينة اللاعب باستخدام الدالة ─────
        city = get_user_city(user_id)
        if not city:
            bot.reply_to(message, "❌ لم يتم العثور على مدينة مملوكة لك.")
            return True

        city_id = city["id"]

        # ────────────── عرض المهام ──────────────
        if text == "مهامي":
            tasks_text = show_daily_tasks(user_id, city_id)
            bot.reply_to(message, tasks_text)
            return True

        # ────────────── جمع الجوائز ──────────────
        if text == "جائزة مهامي":
            rewards_text = collect_daily_task_rewards(user_id, city_id)
            bot.reply_to(message, rewards_text)
            return True

    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {str(e)}")
        return True

    return False