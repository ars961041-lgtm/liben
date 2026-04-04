import logging
import time
from core.bot import bot
from handlers.replies import receive_responses
from database.db_schema import create_all_tables
from telebot.apihelper import ApiTelegramException
from web.app import keep_alive
from core.config import IS_TEST
from handlers.members.welcome import welcome_member, left_member
from database.daily_tasks import run_daily_tasks


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

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
        print("Error in message handler:", e)

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
            print("🔥 Unexpected Error:", e)
            print("🔁 Restarting bot in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    
    print("✅ Bot is running...")
    print("🧪 Running TEST bot" if IS_TEST else "🚀 Running MAIN bot")
    
    keep_alive()
    create_all_tables()

    run_daily_tasks()
    
    start_bot()