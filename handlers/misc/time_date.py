from datetime import datetime
from core.bot import bot
import pytz


def today_date(message, user_timezone="Asia/Aden"):
    """
    تعرض اليوم والتاريخ الحالي للمستخدم حسب منطقته الزمنية.
    """
    try:
        tz = pytz.timezone(user_timezone)
        now = datetime.now(tz)

        days = {
            "Monday": "الإثنين",
            "Tuesday": "الثلاثاء",
            "Wednesday": "الأربعاء",
            "Thursday": "الخميس",
            "Friday": "الجمعة",
            "Saturday": "السبت",
            "Sunday": "الأحد"
        }

        day = days.get(now.strftime("%A"), now.strftime("%A"))
        date = now.strftime("%Y-%m-%d")

        bot.reply_to(
            message,
            f"<b>{day} {date}</b> حسب توقيت {user_timezone}",
            parse_mode="HTML"
        )
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء جلب التاريخ: {e}")
        

def today_time(message, user_timezone="Asia/Aden"):
    """
    تعرض الوقت الحالي للمستخدم حسب منطقته الزمنية.
    """
    try:
        tz = pytz.timezone(user_timezone)
        now = datetime.now(tz)

        time_12 = now.strftime("%I:%M:%S")
        am_pm = now.strftime("%p")

        period = "صباحاً" if am_pm == "AM" else "مساءً"

        bot.reply_to(
            message,
            f"<b>{time_12} {period}</b> حسب توقيت {user_timezone}",
            parse_mode="HTML"
        )
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء جلب الوقت: {e}")