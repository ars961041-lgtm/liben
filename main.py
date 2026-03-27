import logging
import time
import threading

from core.bot import bot
from handlers.replies import receive_responses
from database.db_schema import create_all_tables
from handlers.callbacks import callback_query
from telebot.apihelper import ApiTelegramException

from web.app import run_flask


# =========================
# إعداد اللوق
# =========================
logging.basicConfig(level=logging.INFO)


# =========================
# Message Handler
# =========================
@bot.message_handler(func=lambda message: True)
def replies(message):
    try:
        receive_responses(message)
    except Exception as e:
        print("❌ Error in message handler:", e)


# =========================
# Callback Handler
# =========================
@bot.callback_query_handler(func=lambda call: True)
def callback_query_handle(call):
    try:
        callback_query(call)
    except Exception as e:
        print("❌ Error in callback handler:", e)


# =========================
# تشغيل البوت مع إعادة المحاولة
# =========================
def start_bot():
    while True:
        try:
            print("🚀 Starting bot polling...")

            bot.infinity_polling(
                skip_pending=True
            )

        except ApiTelegramException as e:

            if e.error_code == 409:
                print("⚠️ Bot already running elsewhere!")
                print("🔁 Retrying in 10 seconds...")
                time.sleep(10)

            else:
                print("Telegram API Error:", e)
                time.sleep(5)

        except Exception as e:

            print("🔥 Unexpected Error:", e)
            print("🔁 Restarting bot in 5 seconds...")
            time.sleep(5)


# =========================
# التشغيل الرئيسي
# =========================
if __name__ == "__main__":

    print("✅ Bot is starting...")

    create_all_tables()

    # تشغيل Flask في thread منفصل
    threading.Thread(target=run_flask, daemon=True).start()

    # تشغيل البوت
    start_bot()