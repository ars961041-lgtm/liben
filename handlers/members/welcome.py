"""
نظام الترحيب والوداع — نسخة احترافية.
"""
import random
from datetime import datetime

from core.bot import bot
from core.config import bot_name, developers_id
from utils.helpers import get_bot_username, get_lines, get_bot_photo_id, get_entity_photo_id
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

_DEV_ID      = list(developers_id)[0] if developers_id else None
_UPDATES_URL = "https://t.me/BotBeloPro"


# ══════════════════════════════════════════
# عضو جديد
# ══════════════════════════════════════════

# def welcome_member(message):
#     bot_id = bot.get_me().id
#     for member in message.new_chat_members:
#         if member.id == bot_id:
#             _send_bot_joined(message)   # bot itself was added
#         elif not member.is_bot:
#             # فحص ميزة الترحيب
#             from database.db_queries.group_features_queries import is_feature_enabled
#             if is_feature_enabled(message.chat.id, "feat_welcome"):
#                 _send_welcome(message, member)

def welcome_member(update):
    bot_id = bot.get_me().id
    user = update.new_chat_member.user

    if user.id == bot_id:
        _send_bot_joined(update)

    elif not user.is_bot:
        from database.db_queries.group_features_queries import is_feature_enabled

        if is_feature_enabled(update.chat.id, "feat_welcome"):
            _send_welcome(update, user)

def _send_welcome(update, member):
    uid        = member.id
    first_name = member.first_name or ""
    last_name  = member.last_name  or ""
    full_name  = (first_name + " " + last_name).strip()
    username   = f"@{member.username}" if member.username else "لا يوجد"
    group_name = update.chat.title or "المجموعة"
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

    markup = _build_welcome_markup(update)

    group_photo = get_entity_photo_id(update.chat.id)
    photo_id    = group_photo or get_bot_photo_id()

    _send_photo_or_text(update.chat.id, photo_id, caption, markup)

    # auto-send rules if enabled
    from modules.rules.rules_handler import send_rules_to_new_member
    send_rules_to_new_member(update.chat.id, uid)
    
# ══════════════════════════════════════════
# البوت أُضيف لمجموعة
# ══════════════════════════════════════════

def _send_bot_joined(message):
    """Sent when the bot itself is added to a group."""
    cid        = message.chat.id
    group_name = message.chat.title or "المجموعة"

    # ── فحص صلاحيات البوت ──
    bot_id    = bot.get_me().id
    is_admin  = False
    try:
        member   = bot.get_chat_member(cid, bot_id)
        is_admin = member.status in ("administrator", "creator")
    except Exception:
        pass

    # جلب معلومات المجموعة الكاملة
    group_username = ""
    group_desc     = ""
    try:
        chat_info      = bot.get_chat(cid)
        group_username = f"@{chat_info.username}" if getattr(chat_info, "username", None) else ""
        group_desc     = getattr(chat_info, "description", None) or ""
    except Exception:
        pass

    # جلب اسم المالك
    owner_name = "غير معروف"
    try:
        admins = bot.get_chat_administrators(cid)
        owner  = next((a for a in admins if a.status == "creator"), None)
        if owner:
            owner_name = owner.user.first_name or owner_name
    except Exception:
        pass

    if is_admin:
        caption = (
            f"✅ <b>تم تفعيل بوت {bot_name} بنجاح!</b>\n"
            f"{get_lines()}\n\n"
            f"📛 اسم القروب: <b>{group_name}</b>\n"
        )
        if group_username:
            caption += f"🔗 يوزر القروب: {group_username}\n"
        caption += f"👑 المالك: <b>{owner_name}</b>\n"
        if group_desc:
            caption += f"📝 الوصف: {group_desc}\n"
        caption += f"\n✨ البوت الآن جاهز لإدارة القروب وتقديم المميزات"
    else:
        caption = (
            f"⚠️ <b>تم إضافة {bot_name} للمجموعة</b>\n"
            f"{get_lines()}\n\n"
            f"📛 المجموعة: <b>{group_name}</b>\n\n"
            f"❗ <b>البوت يحتاج صلاحيات المشرف ليعمل بشكل صحيح.</b>\n\n"
            f"يرجى ترقية البوت إلى مشرف حتى يتمكن من:\n"
            f"• إدارة الأعضاء (كتم، حظر، تقييد)\n"
            f"• إرسال رسائل الترحيب\n"
            f"• تثبيت الرسائل وإدارة المجموعة"
        )

    buttons = _build_bot_joined_buttons()

    photo_id = get_entity_photo_id(cid) or get_bot_photo_id()
    _send_photo_or_text(cid, photo_id, caption, buttons)


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

    return build_keyboard(buttons, [1] * len(buttons)) if buttons else None


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
                style="danger",
            ))
    except Exception:
        pass

    return build_keyboard(buttons, [1] * len(buttons)) if buttons else None


def _send_photo_or_text(chat_id, photo_id, caption, markup, reply_to=None):
    """Send photo with caption using file_id, fallback to text if no photo."""
    kwargs = {"caption": caption, "parse_mode": "HTML", "reply_markup": markup}
    if reply_to:
        kwargs["reply_to_message_id"] = reply_to
    try:
        if photo_id:
            bot.send_photo(chat_id, photo_id, **kwargs)
        else:
            bot.send_message(chat_id, caption, parse_mode="HTML",
                             reply_markup=markup, reply_to_message_id=reply_to)
    except Exception as e:
        print(f"[welcome] error: {e}")


# ══════════════════════════════════════════
# وداع عضو
# ══════════════════════════════════════════

# def left_member(message):
#     user = message.left_chat_member
#     if user.is_bot:
#         return
#     text = (
#         f"<b>{random.choice(_LEFT_MSGS)} "
#         f"<a href='tg://user?id={user.id}'>{user.first_name}</a></b>"
#     )
#     try:
#         bot.reply_to(message, text, parse_mode="HTML")
#     except Exception as e:
#         print(f"[left_member] error: {e}")
def left_member(update):
    user = update.new_chat_member.user

    if user.is_bot:
        return

    text = (
        f"<b>{random.choice(_LEFT_MSGS)} "
        f"<a href='tg://user?id={user.id}'>{user.first_name}</a></b>"
    )

    try:
        bot.send_message(update.chat.id, text, parse_mode="HTML")
    except Exception as e:
        print(f"[left_member] error: {e}")