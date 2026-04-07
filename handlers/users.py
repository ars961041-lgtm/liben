from database.connection import get_db_conn
from database.db_queries import (
    get_user_info,
    upsert_group_member,
)
from core.bot import bot
from database.db_queries.groups_queries import get_group_stats, get_group_total_messages
from utils.helpers import limit_text, send_reply, send_error, is_group, send_error_reply
import random
import time
from utils.constants import lines
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

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
    from utils.helpers import send_bot_profile, get_lines
    from utils.keyboards import ui_btn, build_keyboard
    from core.config import bot_name
    from core import memory as _mem
    _mem.set_last_command(message.from_user.id, "/start")

    caption = (
        f"<b>أهلاً وسهلاً! 👋</b>\n"
        f"{get_lines()}\n\n"
        f"أنا <b>Belo | بيلو</b> — بوت متكامل يجمع بين الترفيه والفائدة.\n\n"
        f"🕌 <b>الميزات الدينية:</b>\n"
        f"أذكار الصباح والمساء، القرآن الكريم، تذكير يومي\n\n"
        f"🎮 <b>الألعاب:</b>\n"
        f"دول، حروب، بنك، تحالفات، ألعاب ترفيهية\n\n"
        f"⚙️ <b>الإدارة:</b>\n"
        f"كتم، حظر، ترقية مشرفين، تذاكر دعم\n\n"
        f"✨ <b>أدوات أخرى:</b>\n"
        f"تنسيق النصوص، الوقت والتاريخ، المجلة اليومية\n\n"
        f"{get_lines()}\n"
        f"اكتب <code>مميزات بيلو</code> لاستعراض كل الميزات\n"
        f"اكتب <code>الألعاب</code> لعرض الألعاب المتاحة"
    )

    # Build buttons: PM button (groups only) + channel button
    from utils.helpers import get_bot_username
    buttons = []
    if message.chat.type != "private":
        username = get_bot_username()
        if username:
            buttons.append(ui_btn(bot_name, url=f"https://t.me/{username}", style="primary"))
    buttons.append(ui_btn("📢 قناة التحديثات", url="https://t.me/BotBeloPro", style="success"))

    markup = build_keyboard(buttons, [len(buttons)]) if buttons else None

    import os
    from core.bot import bot as _bot
    photo_path = os.path.join("assets", "images", "bot_profile.jpg")
    kwargs = {
        "caption":      caption,
        "parse_mode":   "HTML",
        "reply_markup": markup,
        "reply_to_message_id": message.message_id,
    }
    try:
        if os.path.exists(photo_path):
            with open(photo_path, "rb") as f:
                _bot.send_photo(message.chat.id, f, **kwargs)
        else:
            _bot.send_message(message.chat.id, caption,
                              parse_mode="HTML", reply_markup=markup,
                              reply_to_message_id=message.message_id)
    except Exception as e:
        print(f"[send_welcome] error: {e}")

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


def get_user_data(user):
    user_id = user.id

    full_name = user.first_name + (
        " " + user.last_name if user.last_name else ""
    )

    username = user.username or None

    photos = bot.get_user_profile_photos(user_id)

    photo_id = None
    if photos.total_count > 0:
        photo_id = photos.photos[0][-1].file_id

    bio = None
    try:
        chat = bot.get_chat(user_id)
        bio = getattr(chat, "bio", None)
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
        level, next_level = calculate_level(group_stats["messages_count"])
        achievements = get_achievements(group_stats["messages_count"])
        msg_count = group_stats["messages_count"]

        total = get_group_total_messages(group_id) or 1
        percentage = (msg_count / total) * 100

        caption += f"""📊 النشاط
📨 الرسائل: {msg_count} / {next_level}
📈 التفاعل: {percentage:.2f}٪
🏅 الترتيب: {group_stats['rank']}

⭐ المستوى: {level}
"""

        if achievements:
            caption += "\n🏆 الإنجازات\n"
            for ach in achievements:
                caption += f"{ach}\n"

    # ─── اللقب الموسمي ───
    try:
        from modules.progression.seasons import get_latest_title
        title = get_latest_title(user_id)
        if title:
            caption += f"\n🏆 اللقب الموسمي: {title}\n"
    except Exception:
        pass

    if user_data["bio"]:
        caption += f"\n📝 البايو: {user_data['bio']}"

    caption += f"\n</b>{lines[4]}"

    return caption

def send_user_profile(message):
    try:
        text = message.text.split()

        # 1️⃣ الرد على رسالة
        if message.reply_to_message:
            target = message.reply_to_message.from_user

        # 2️⃣ آيدي
        elif len(text) > 1 and text[1].isdigit():
            try:
                target = bot.get_chat(int(text[1]))
            except:
                send_reply(message, "❌ لا يمكن جلب هذا المستخدم. قد يكون لم يبدأ محادثة مع البوت أو ليس في المجموعة.")
                return

        # 3️⃣ نفسه
        else:
            target = message.from_user

        user_id = target.id
        chat_id = message.chat.id

        # جلب بيانات المستخدم
        user_data = get_user_data(target)

        group_stats = None
        if is_group(message):
            group_stats = get_group_stats(user_id, chat_id)

        # بناء البروفايل
        caption = build_profile(user_id, chat_id, user_data, group_stats)

        # إرسال الصورة إذا موجودة، وإلا نص
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
        send_error_reply(message, send_error("send_user_profile", e))