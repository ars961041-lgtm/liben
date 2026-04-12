import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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


@bot.channel_post_handler(func=lambda m: True)
def on_channel_post(message):
    try:
        from modules.content_hub.channel_sync import handle_channel_post
        handle_channel_post(message)
    except Exception as e:
        print(f"[channel_post] Error: {e}")


@bot.edited_channel_post_handler(func=lambda m: True)
def on_channel_post_edit(message):
    try:
        from modules.content_hub.channel_sync import handle_channel_post_edit
        handle_channel_post_edit(message)
    except Exception as e:
        print(f"[edited_channel_post] Error: {e}")


@bot.chat_member_handler()
def on_chat_member_update(update):
    # تجاهل أحداث الانضمام/المغادرة في القنوات — البوت يعمل فيها بالأوامر فقط
    if update.chat.type == "channel":
        return

    old = update.old_chat_member.status
    new = update.new_chat_member.status
    if old in ("left", "kicked") and new == "member":
        welcome_member(update)
    elif old == "member" and new in ("left", "kicked"):
        left_member(update)


@bot.message_handler(commands=["start"])
def handle_start_command(message):
    """
    معالج /start — مسجَّل قبل func=lambda لضمان الأولوية.
    يتعامل مع جميع deep links الهمسات.
    """
    print(f"[START] uid={message.from_user.id} text='{message.text}'")
    try:
        parts = message.text.split(maxsplit=1)
        arg   = parts[1].strip() if len(parts) > 1 else ""

        if arg:
            print(f"[START] arg='{arg}'")

            # ── Whisper deep links ──
            if arg.startswith("hms"):
                # /start hms<TOKEN> — كتابة همسة جديدة
                token = arg[3:]
                print(f"[WHISPER] hms token={token}")
                from modules.whispers.whisper_handler import handle_hms_start
                handle_hms_start(message, token)
                return

            if arg.startswith("hmrp"):
                # /start hmrp<id> — الرد على همسة
                wid = arg[4:]
                print(f"[WHISPER] hmrp wid={wid}")
                from modules.whispers.whisper_handler import handle_hmrp_start
                handle_hmrp_start(message, wid)
                return

        # /start بدون payload أو payload غير معروف
        from handlers.replies import receive_responses
        receive_responses(message)

    except Exception as e:
        import traceback
        print(f"[START] ERROR: {e}\n{traceback.format_exc()}")
        try:
            bot.send_message(message.from_user.id, "❌ حدث خطأ. حاول مجدداً.")
        except Exception:
            pass


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
                skip_pending=True,
                allowed_updates=[
                    "message",
                    "callback_query",
                    "chat_member",
                    "inline_query",
                    "my_chat_member",
                    "channel_post",
                    "edited_channel_post",
                ]
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

    # Start unified scheduler and run first daily cycle
    from database.daily_tasks import run_daily_tasks
    run_daily_tasks()

    start_bot()