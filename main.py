import logging
import time
from core.bot import bot
from handlers.replies import receive_responses
from database.db_schema import create_all_tables
from handlers.callbacks import callback_query
from telebot.apihelper import ApiTelegramException
from web.app import keep_alive

logging.basicConfig(level=logging.INFO)

@bot.message_handler(func=lambda message: True)
def replies(message):
    try:
        receive_responses(message)
    except Exception as e:
        print("Error in message handler:", e)

@bot.callback_query_handler(func=lambda call: True)
def callback_query_handle(call):
    try:
        callback_query(call)
    except Exception as e:
        print("Error in callback handler:", e)

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

    keep_alive()  # 🔥 مهم لـ Render

    create_all_tables()

    start_bot()