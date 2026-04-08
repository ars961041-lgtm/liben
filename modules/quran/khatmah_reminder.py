"""
مُجدوِل تذكيرات الختمة — يعمل في الخلفية.
"""
import time
import threading
from datetime import datetime, timezone

from core.bot import bot
from modules.quran import quran_db as db
from utils.pagination import btn
from utils.pagination.buttons import build_keyboard


def _scheduler_loop():
    while True:
        try:
            now    = datetime.now(timezone.utc)
            due    = db.get_due_khatma_reminders(now.hour, now.minute)
            for r in due:
                _fire(r)
        except Exception as e:
            print(f"[KhatmahReminder] {e}")
        time.sleep(60 - datetime.now().second)


def _fire(r: dict):
    uid    = r["user_id"]
    goal   = db.get_khatma_goal(uid)
    today  = db.get_today_count(uid)

    # Skip if daily goal already completed
    if goal > 0 and today >= goal:
        return

    streak   = db.get_streak(uid)
    days_off = db.get_days_since_last_read(uid)

    if days_off >= 1:
        from modules.quran.khatmah import _inactive_msg
        extra_line = f"\n{_inactive_msg(days_off)}"
    elif streak >= 2:
        extra_line = f"\n🔥 حافظ على سلسلتك! ({streak} يوم)"
    else:
        extra_line = ""

    owner   = (uid, uid)
    buttons = [btn("▶️ متابعة القراءة", "kh_continue", {}, owner=owner, color="su")]
    markup  = build_keyboard(buttons, [1], uid)

    try:
        bot.send_message(
            uid,
            f"🕌 <b>تذكير الختمة</b>\n\n"
            f"📖 وردك اليومي ينتظرك"
            f"{extra_line}\n"
            f"🎯 هدفك: <b>{goal}</b> آية\n"
            f"📊 تقدمك اليوم: <b>{today}</b> / {goal}",
            parse_mode="HTML",
            reply_markup=markup,
        )
    except Exception:
        pass   # silent fail — user may have blocked the bot


def start_khatmah_reminder_scheduler():
    threading.Thread(target=_scheduler_loop, daemon=True).start()
