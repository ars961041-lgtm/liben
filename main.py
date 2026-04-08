import logging
import time
import traceback
from core.bot import bot
from handlers.replies import receive_responses
from database.db_schema import create_all_tables
from telebot.apihelper import ApiTelegramException
from web.app import keep_alive
from core.config import IS_TEST, DB_NAME, DB_CONTENT
from handlers.members.welcome import welcome_member, left_member
from database.daily_tasks import run_daily_tasks


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def _ensure_databases():
    """يتحقق من وجود ملفات DB ويُنشئها إذا لم تكن موجودة."""
    import os
    for path in (DB_NAME, DB_CONTENT):
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        if not os.path.exists(path):
            import sqlite3
            sqlite3.connect(path).close()
            print(f"✅ Created database: {path}")
        else:
            print(f"✅ Database exists: {path}")


@bot.message_handler(content_types=["new_chat_members"])
def welcome(message):
    welcome_member(message)

@bot.message_handler(content_types=["left_chat_member"])
def left(message):
    left_member(message)

@bot.message_handler(func=lambda message: True)
def replies(message):
    try:
        receive_responses(message)
    except Exception as e:
        print(f"Error in message handler: {e}\n{traceback.format_exc()}")


@bot.message_handler(content_types=["photo", "video", "audio", "voice",
                                     "video_note", "document", "sticker", "animation"])
def media_handler(message):
    try:
        receive_responses(message)
    except Exception as e:
        print(f"Error in media handler: {e}\n{traceback.format_exc()}")

def start_bot():
    while True:
        try:
            print("🚀 Starting bot polling...")
            bot.infinity_polling(
                timeout=20,
                long_polling_timeout=10,
                skip_pending=True
            )
        except ApiTelegramException as e:
            print("Telegram API Error:", e)
            time.sleep(5)
        except Exception as e:
            print(f"🔥 Unexpected Error: {e}\n{traceback.format_exc()}")
            print("🔁 Restarting bot in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    
    print("✅ Bot is running...")
    print("🧪 Running TEST bot" if IS_TEST else "🚀 Running MAIN bot")

    # ── تأكد من وجود قواعد البيانات قبل أي شيء ──
    _ensure_databases()

    keep_alive()
    create_all_tables()

    # Register rules callbacks
    from modules.rules.rules_handler import register_rules_callbacks
    register_rules_callbacks()

    # Start khatmah reminder scheduler
    from modules.quran.khatmah_reminder import start_khatmah_reminder_scheduler
    start_khatmah_reminder_scheduler()

    run_daily_tasks()
    
    start_bot()