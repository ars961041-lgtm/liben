from datetime import datetime
from core.bot import bot


def today_date(message):

    days = {
        "Monday": "الإثنين",
        "Tuesday": "الثلاثاء",
        "Wednesday": "الأربعاء",
        "Thursday": "الخميس",
        "Friday": "الجمعة",
        "Saturday": "السبت",
        "Sunday": "الأحد"
    }

    now = datetime.now()

    day = days.get(now.strftime("%A"))
    date = now.strftime("%Y-%m-%d")

    bot.reply_to(message, f"<b>{day} {date}</b>", parse_mode="HTML")

def today_time(message):

    now = datetime.now()

    time_12 = now.strftime("%I:%M:%S")
    am_pm = now.strftime("%p")

    if am_pm == "AM":
        period = "صباحاً"
    else:
        period = "مساءً"

    bot.reply_to(message, f"<b>{time_12} {period}</b>", parse_mode="HTML")