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

def send_user_info(message):

  if not is_group(message):
      send_account_info(message)
      return

  try:      
    group_id = message.chat.id
    user_id = message.from_user.id
    full_name = message.from_user.first_name + (" " + message.from_user.last_name if message.from_user.last_name else "")

    msg_count = get_user_msgs(user_id, group_id)
    photos = bot.get_user_profile_photos(user_id)
    photo_count = photos.total_count
    user_info = bot.get_chat(user_id)

    bio = user_info.bio if hasattr(user_info, "bio") and user_info.bio else None
    username = message.from_user.username

    members = get_top_group_members(group_id, limit=1000)
    total_group_msgs = get_group_total_messages(group_id) or 1

    # ترتيب العضو
    rank = next((i + 1 for i, (uid, _) in enumerate(members) if uid == user_id), None)
    percentage = (msg_count / total_group_msgs) * 100

    caption = f"{lines[4]}<b>\n👤 الاسم: {full_name}\n🆔 الآيدي: <code>{user_id}</code>\n"
    caption += f"💬 عدد الرسائل: {msg_count}\n📈 نسبة التفاعل: {percentage:.2f}٪\n"
    if rank:
      caption += f"🏅 الترتيب بين المتفاعلين: {rank}\n"
    if username:
      caption += f"🔗 اليوزر: @{username}\n"
    if bio:
      caption += f"📝 البايو: {bio}\n"

    caption += f"</b>{right_arrows[2]} {lines[4]}"

    # إرسال صورة إن وجدت، وإلا إرسال النص فقط
    if photo_count > 0:
      bot.send_photo(
        message.chat.id,
        photos.photos[0][-1].file_id,
        caption=caption,
        parse_mode='HTML',
        reply_to_message_id=message.message_id,
        has_spoiler=True
      )
    else:
      send_reply(message, caption)
  except Exception as e:
    send_error_reply(message, send_error(f"send_user_info", e))


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

def send_top_users(message):
    if not is_group(message):
        send_reply(message, "هذا الأمر متاح فقط في المجموعات!")
        return

    group_id = message.chat.id
    top_text = get_top_users_text(group_id)
    send_reply(message, top_text)


def get_top_users_text(group_id):
    top_users = get_top_group_members(group_id, limit=10)

    if not top_users:
        return "لا توجد بيانات تفاعل في هذه المجموعة بعد."

    emojis = ["🥇", "🥈", "🥉"] + [""] * 7

    caption = f"{lines[4]}<b>\n↜ توب لأكثر 10 متفاعلين في القروب \n\n"

    for i, (user_id, msg_count, name) in enumerate(top_users, 1):
        emoji = emojis[i-1] if i <= 3 else ""
        short_name = limit_text(name, 20)
        caption += f"{i}) {emoji} {msg_count} l {short_name}\n"

    caption += f"\n</b>{lines[4]}"

    return caption

# =========================
# CACHE SYSTEM
# =========================

USER_CACHE = {}
CACHE_TTL = 120  # 2 minutes

def get_cached_user(user_id):

    if user_id in USER_CACHE:
        data, timestamp = USER_CACHE[user_id]

        if time.time() - timestamp < CACHE_TTL:
            return data

        USER_CACHE.pop(user_id, None)

    photos = bot.get_user_profile_photos(user_id)
    user_info = bot.get_chat(user_id)

    photo_id = None
    if photos.total_count > 0:
        photo_id = photos.photos[0][-1].file_id

    data = {
        "photo_id": photo_id,
        "photo_count": photos.total_count,
        "bio": getattr(user_info, "bio", None)
    }

    USER_CACHE[user_id] = (data, time.time())

    return data

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


# =========================
# USER DATA
# =========================

def get_user_data(user_id, message):
    full_name = message.from_user.first_name + (
        " " + message.from_user.last_name if message.from_user.last_name else ""
    )

    username = message.from_user.username or "لا يوجد"

    cached = get_cached_user(user_id)

    user = get_user_info(user_id)

    return {
        "full_name": full_name,
        "username": username,
        "photo_id": cached["photo_id"],
        "bio": cached["bio"] or "لم يتم تعيينه",
    }


# =========================
# GROUP STATS
# =========================

def get_group_stats(user_id, group_id):
    msg_count = get_user_msgs(user_id, group_id)

    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, message_count
        FROM group_members
        WHERE group_id = ?
        ORDER BY message_count DESC
    """, (group_id,))

    members = cursor.fetchall()

    cursor.execute("""
        SELECT SUM(message_count)
        FROM group_members
        WHERE group_id = ?
    """, (group_id,))

    total_msgs = cursor.fetchone()[0] or 1

    rank = next((i + 1 for i, (uid, _) in enumerate(members) if uid == user_id), None)
    percentage = (msg_count / total_msgs) * 100

    return {
        "msg_count": msg_count,
        "rank": rank,
        "percentage": percentage
    }


# =========================
# PROFILE BUILDER
# =========================

def build_profile(user_id, group_id, user_data, group_stats=None):
    caption = f"""{lines[4]}<b>\n\n👤 الاسم: {user_data['full_name']}\n🆔 الآيدي: <code>{user_id}</code>\n🔗 اليوزر: @{user_data['username']}\n\n"""

    if group_stats:
        level, next_level = calculate_level(group_stats["msg_count"])
        achievements = get_achievements(group_stats["msg_count"])

        msg_count = group_stats["msg_count"]

        caption += f"""
        📊 النشاط
        📊 الرسائل: {msg_count} / {next_level}
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

    caption += f"""\n\n</b>{lines[4]}"""

    return caption


# =========================
# MAIN PROFILE SENDER
# =========================
def send_profile(message):
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id

        user_data = get_user_data(user_id, message)
        group_stats = get_group_stats(user_id, chat_id) if is_group(message) else None

        caption = build_profile(user_id, chat_id, user_data, group_stats)

        if user_data["photo_id"]:
            file_id = user_data["photo_id"]

            try:
                bot.send_photo(
                    chat_id,
                    file_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_to_message_id=message.message_id,
                    has_spoiler=True
                )

            except Exception as e:

                if "FILE_REFERENCE_EXPIRED" in str(e):

                    # حذف الكاش
                    USER_CACHE.pop(user_id, None)

                    # إعادة تحميل البيانات
                    cached = get_cached_user(user_id)
                    file_id = cached["photo_id"]

                    bot.send_photo(
                        chat_id,
                        file_id,
                        caption=caption,
                        parse_mode="HTML",
                        reply_to_message_id=message.message_id,
                        has_spoiler=True
                    )

                else:
                    raise

        else:
            send_reply(message, caption)

    except Exception as e:
        send_error_reply(message, send_error("send_profile", e))