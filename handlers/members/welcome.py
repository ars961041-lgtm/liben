"""
نظام الترحيب والوداع — نسخة احترافية.
"""
import os
import random
from datetime import datetime

from core.bot import bot
from core.config import bot_name, developers_id
from utils.helpers import get_bot_username, get_lines
from utils.keyboards import ui_btn, build_keyboard, send_ui

_WELCOME_MSGS = [
    "يا هلا وسهلا 👋 نورت المجموعة",
    "مرحبا 🌟 القروب ازداد نور",
    "هلا وغلا 😄 حياك بين إخوانك",
    "حي الله 🔥 نورت المكان",
    "أهلاً 🤝 تفضل البيت بيتك",
    "يا مرحبا مليون ✨ نورت القروب",
    "ياهلا 😎 شد حيلك معنا",
    "مرحبا 🌹 وصلت الدار",
    "هلا 👀 القروب نور يوم دخلت",
    "يا أهلاً 🔥 القروب صار أخطر",
    "يا أهلاً 🔥 توه القروب اكتمل",
    "يا أهلاً 👀 انتبه لا تتعود علينا",
]

_DEV_WELCOME_MSGS = [
    "⚡️ المطور دخل — الكل يقف!",
    "👑 صاحب البوت وصل — أهلاً وسهلاً",
    "🛠 المطور في الدار — البوت بخير الحين",
    "💻 وصل المطور — الكود يفرح",
    "🚀 المطور هبط — استعدوا للتحديثات",
]

_LEFT_MSGS = [
    "مع السلامة 👋 الله يكتب لك الخير",
    "طلع 😔 الباب يفوت جمل",
    "ودعنا 🌙 الله يسهّل دربك",
    "غادر 👀 شكله ما تحملنا",
    "راح 🚶‍♂️ الله معه",
    "انقلع 😂 نمزح ارجع بس",
    "وداعاً 🌹 نتمنى نشوفك مرة ثانية",
    "خرج 👋 القروب بيشتاق لك",
    "اختفى 🫡 الله يحفظه",
    "غادر ✨ نتمنى له التوفيق",
]

_PHOTO_PATH = os.path.join("assets", "images", "bot_profile.jpg")

# Developer info reused from general_handler
_DEV_ID      = list(developers_id)[0] if developers_id else None
_UPDATES_URL = "https://t.me/BotBeloPro"


# ══════════════════════════════════════════
# عضو جديد
# ══════════════════════════════════════════

def welcome_member(message):
    bot_id = bot.get_me().id
    for member in message.new_chat_members:
        if member.id == bot_id:
            _send_bot_joined(message)   # bot itself was added
        elif not member.is_bot:
            _send_welcome(message, member)


def _send_welcome(message, member):
    uid        = member.id
    first_name = member.first_name or ""
    last_name  = member.last_name  or ""
    full_name  = (first_name + " " + last_name).strip()
    username   = f"@{member.username}" if member.username else "لا يوجد"
    group_name = message.chat.title or "المجموعة"
    is_dev     = uid in developers_id

    now      = datetime.now()
    date_str = now.strftime("%Y/%m/%d")
    time_str = now.strftime("%H:%M")

    welcome_line = (
        random.choice(_DEV_WELCOME_MSGS) if is_dev
        else random.choice(_WELCOME_MSGS)
    )

    caption = (
        f"°︙ نورت قروبنا <b>{group_name}</b> يا "
        f"<a href='tg://user?id={uid}'>{first_name}</a> ⚡️\n\n"
        f"°︙ اسمك ⇚ <b>{full_name}</b>\n"
        f"°︙ ايديك ⇚ <code>{uid}</code>\n"
        f"°︙ يوزرك ⇚ {username}\n"
        f"°︙ تاريخ الانضمام ⇚ {date_str}\n"
        f"°︙ الساعة ⇚ {time_str}\n\n"
        f"✨ {welcome_line}"
    )

    markup = _build_welcome_markup(message)
    _send_photo_or_text(message.chat.id, _PHOTO_PATH, caption, markup,
                        reply_to=message.message_id)

    # auto-send rules if enabled
    from modules.rules.rules_handler import send_rules_to_new_member
    send_rules_to_new_member(message.chat.id, uid)


# ══════════════════════════════════════════
# البوت أُضيف لمجموعة
# ══════════════════════════════════════════

def _send_bot_joined(message):
    """Sent when the bot itself is added to a group."""
    cid        = message.chat.id
    group_name = message.chat.title or "المجموعة"

    # Fetch group owner name
    owner_name = "غير معروف"
    try:
        admins = bot.get_chat_administrators(cid)
        owner  = next((a for a in admins if a.status == "creator"), None)
        if owner:
            owner_name = owner.user.first_name or owner_name
    except Exception:
        pass

    caption = (
        f"🤖 <b>تم تفعيل بوت {bot_name} بنجاح!</b>\n"
        f"{get_lines()}\n\n"
        f"📛 اسم القروب: <b>{group_name}</b>\n"
        f"👑 المالك: <b>{owner_name}</b>\n\n"
        f"✨ البوت الآن جاهز لإدارة القروب وتقديم المميزات"
    )

    buttons = _build_bot_joined_buttons()

    # Try group photo first, fallback to bot profile
    photo = _get_group_photo(cid)
    if photo:
        try:
            bot.send_photo(cid, photo, caption=caption,
                           parse_mode="HTML", reply_markup=buttons)
            return
        except Exception:
            pass

    _send_photo_or_text(cid, _PHOTO_PATH, caption, buttons)


def _build_bot_joined_buttons():
    """Developer button + updates channel button."""
    buttons = []

    if _DEV_ID:
        try:
            dev_user = bot.get_chat(_DEV_ID)
            dev_name = dev_user.first_name or "المطور"
            if dev_user.username:
                buttons.append(ui_btn(
                    f"👨‍💻 {dev_name}",
                    url=f"https://t.me/{dev_user.username}",
                    style="success",
                ))
        except Exception:
            pass

    buttons.append(ui_btn("📢 قناة التحديثات", url=_UPDATES_URL, style="primary"))

    return build_keyboard(buttons, [len(buttons)]) if buttons else None


def _get_group_photo(chat_id: int):
    """Returns a file_id for the group photo, or None."""
    try:
        chat  = bot.get_chat(chat_id)
        photo = getattr(chat, "photo", None)
        if photo:
            return photo.big_file_id
    except Exception:
        pass
    return None


# ══════════════════════════════════════════
# مساعدات
# ══════════════════════════════════════════

def _build_welcome_markup(message):
    """Bot PM button + group owner button."""
    bot_username = get_bot_username()
    buttons = []

    if bot_username:
        buttons.append(ui_btn(bot_name, url=f"https://t.me/{bot_username}",
                               style="primary"))
    try:
        admins = bot.get_chat_administrators(message.chat.id)
        owner  = next((a for a in admins if a.status == "creator"), None)
        if owner and owner.user.username:
            buttons.append(ui_btn(
                f"👑 {owner.user.first_name}",
                url=f"https://t.me/{owner.user.username}",
                style="secondary",
            ))
    except Exception:
        pass

    return build_keyboard(buttons, [len(buttons)]) if buttons else None


def _send_photo_or_text(chat_id, photo_path, caption, markup, reply_to=None):
    """Send photo with caption, fallback to text if image missing."""
    kwargs = {"caption": caption, "parse_mode": "HTML", "reply_markup": markup}
    if reply_to:
        kwargs["reply_to_message_id"] = reply_to
    try:
        if os.path.exists(photo_path):
            with open(photo_path, "rb") as f:
                bot.send_photo(chat_id, f, **kwargs)
        else:
            bot.send_message(chat_id, caption, parse_mode="HTML",
                             reply_markup=markup, reply_to_message_id=reply_to)
    except Exception as e:
        print(f"[welcome] error: {e}")


# ══════════════════════════════════════════
# وداع عضو
# ══════════════════════════════════════════

def left_member(message):
    user = message.left_chat_member
    if user.is_bot:
        return
    text = (
        f"<b>{random.choice(_LEFT_MSGS)} "
        f"<a href='tg://user?id={user.id}'>{user.first_name}</a></b>"
    )
    try:
        bot.reply_to(message, text, parse_mode="HTML")
    except Exception as e:
        print(f"[left_member] error: {e}")
