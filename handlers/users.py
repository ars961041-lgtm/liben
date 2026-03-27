from database.connection import get_db_conn
from database.db_queries import (
    get_user_msgs,
    get_user_balance,
    get_user_info,
    upsert_group_member,
    get_top_group_members,
    get_group_total_messages
)
from core.bot import bot
from telebot import types
from database.db_queries.groups_queries import get_group_stats
from handlers.utils.cache import get_cache, set_cache
from utils.helpers import limit_text, send_reply, send_error, get_error_icons, is_group, send_error_reply
import random
import time
from modules.country.keyboards.country_keyboard import create_gender_markup
from utils.constants import right_arrows, lines

gender_emojis = {
  "male": ["🧔", "👨‍💼", "🦸‍♂️", "🕺"],
  "female": ["👩", "👩‍🎤", "💃", "🧕"],
  "neutral": ["👤", "🌟", "✨", "🔆"]
}

def add_user_if_not_exists(msg):
  user_id = msg.from_user.id

  try:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

  except Exception as e:
      send_reply(msg, send_error("add_user_if_not_exists", e))

def track_group_members(msg):
  try:
    if not (is_group(msg)):
      return

    group_id = msg.chat.id
    group_name = msg.chat.title 
    user_id = msg.from_user.id  
    full_name = msg.from_user.first_name + (" " + msg.from_user.last_name if msg.from_user.last_name else "") 
    
    upsert_group_member(group_id, user_id, full_name, group_name)

  except Exception as e:
    send_reply(msg, send_error("track_group_members", e))

def send_account_info(message):
    """Display current user account info and stats."""
    try:
        user_id = message.from_user.id
        user = get_user_info(user_id)

        if not user:
            send_reply(message, "لا يوجد حساب مسجَّل. يرجى البدء بمحادثة مع البوت.")
            return

        user_id_db, name, username, gender, bio = user
        username = username or 'لا يوجد'
        bio = bio or 'لم يتم تعيينه'

        text = (
            f"{lines[4]}\n"
            f"👤 الاسم: {name}\n"
            f"🆔 الآيدي: <code>{user_id_db}</code>\n"
            f"🔗 اليوزر: @{username if username != 'لا يوجد' else username}\n"
            f"📝 البايو: {bio}\n"
            f"{lines[4]}"
        )

        send_reply(message, text)
    except Exception as e:
        send_error_reply(message, send_error("send_account_info", e))

def get_random_emoji(gender):
    return random.choice(gender_emojis.get(gender, gender_emojis["neutral"]))

def ask_gender(msg):
  try:
    if not (is_group(msg)):
      return

    user_id = msg.from_user.id
    markup = create_gender_markup(user_id)

    send_reply(msg, "من فضلك اختر جنسك:", reply_markup=markup)

  except Exception as e:
    send_error_reply(msg, send_error(f"ask_gender", e))

def send_gendered_welcome(msg, gender):
  try:
    group_name = msg.chat.title if is_group(msg) else None
    emoji = get_random_emoji(gender)
    greeting = ""
    if gender == "male":
      greeting = "أهلاً بك يا بطل 💪"
    elif gender == "female":
      greeting = "أهلاً بك يا زهرة 🌷"

    if group_name:
      text = f"{emoji} {greeting} في مجموعة <b>{group_name}</b>!"
    else:
      text = f"{emoji} {greeting} في البوت الخاص بنا."

    send_reply(msg, f"{text}")

  except Exception as e:
    send_error_reply(msg, send_error(f"send_gendered_welcome", e))


def send_welcome(message):
    welcome_text = f"""
{lines[4]}<b>
مرحباً بك في بوت Liben! 🤖

هذا البوت مصمم لإدارة المدن والاقتصاد والتفاعل في المجموعات.

الأوامر المتاحة:
- /start: لعرض هذه الرسالة
- عني أو ايدي أو معلوماتي: لعرض معلوماتك الشخصية
- توب المتفاعلين: لعرض أكثر 10 أعضاء تفاعلاً (في المجموعات فقط)
- إنشاء دولة: لبدء إنشاء دولة جديدة
- دولتي: لعرض معلومات دولتك
- بنكي: لفتح قائمة البنك الذكية
- إنشاء حساب بنكي: لبدء نظام Liben المالي

استمتع بالتفاعل! 🚀
</b>{lines[4]}
"""
    send_reply(message, welcome_text)

# =========================
# LEVEL SYSTEM
# =========================

def calculate_level(messages):
    level = int(messages ** 0.5)
    next_level = (level + 1) ** 2

    return level, next_level


# =========================
# ACHIEVEMENTS SYSTEM
# =========================

def get_achievements(msg_count):
    achievements = []

    if msg_count >= 100:
        achievements.append("🥉 متفاعل")

    if msg_count >= 500:
        achievements.append("🥈 نشيط")

    if msg_count >= 1000:
        achievements.append("🥇 أسطورة")

    return achievements


def get_user_data(user_id, message):

    full_name = message.from_user.first_name + (
        " " + message.from_user.last_name if message.from_user.last_name else ""
    )

    username = message.from_user.username or None

    photos = bot.get_user_profile_photos(user_id)

    photo_id = None
    if photos.total_count > 0:
        photo_id = photos.photos[0][-1].file_id

    bio = None
    try:
        user = bot.get_chat(user_id)
        bio = getattr(user, "bio", None)
    except:
        pass

    return {
        "full_name": full_name,
        "username": username,
        "photo_id": photo_id,
        "photo_count": photos.total_count,
        "bio": bio or "لم يتم تعيينه",
    }
 
def get_user_data(user_id, message):

    full_name = message.from_user.first_name + (
        " " + message.from_user.last_name if message.from_user.last_name else ""
    )

    username = message.from_user.username or None

    photos = bot.get_user_profile_photos(user_id)

    photo_id = None
    if photos.total_count > 0:
        photo_id = photos.photos[0][-1].file_id

    bio = None
    try:
        user = bot.get_chat(user_id)
        bio = getattr(user, "bio", None)
    except:
        pass

    return {
        "full_name": full_name,
        "username": username,
        "photo_id": photo_id,
        "photo_count": photos.total_count,
        "bio": bio or "لم يتم تعيينه",
    }

def build_profile(user_id, group_id, user_data, group_stats=None):

    caption = f"""{lines[4]}<b>

👤 الاسم: {user_data['full_name']}
🆔 الآيدي: <code>{user_id}</code>
"""

    if user_data["username"]:
        caption += f"🔗 اليوزر: @{user_data['username']}\n"

    caption += "\n"

    if group_stats:

        level, next_level = calculate_level(group_stats["msg_count"])
        achievements = get_achievements(group_stats["msg_count"])

        msg_count = group_stats["msg_count"]

        caption += f"""📊 النشاط
📨 الرسائل: {msg_count} / {next_level}
📈 التفاعل: {group_stats['percentage']:.2f}٪
🏅 الترتيب: {group_stats['rank']}

⭐ المستوى: {level}
"""

        if achievements:
            caption += "\n🏆 الإنجازات\n"
            for ach in achievements:
                caption += f"{ach}\n"

    if user_data["bio"]:
        caption += f"\n📝 البايو: {user_data['bio']}"

    caption += f"\n</b>{lines[4]}"

    return caption

def send_profile(message):

    try:

        user_id = message.from_user.id
        chat_id = message.chat.id

        user_data = get_user_data(user_id, message)

        group_stats = None
        if is_group(message):
            group_stats = get_group_stats(user_id, chat_id)

        caption = build_profile(user_id, chat_id, user_data, group_stats)

        if user_data["photo_id"]:

            bot.send_photo(
                chat_id,
                user_data["photo_id"],
                caption=caption,
                parse_mode="HTML",
                reply_to_message_id=message.message_id,
                has_spoiler=True
            )

        else:
            send_reply(message, caption)

    except Exception as e:
        send_error_reply(message, send_error("send_profile", e))