from core.bot import bot
from telebot import types
import random
from .constants import *
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.config import bot_name


def get_bot_username() -> str:
    """يجلب username البوت ديناميكياً ويخزنه مؤقتاً."""
    try:
        import core.bot as _cb
        if not getattr(_cb, "bot_username", None):
            _cb.bot_username = bot.get_me().username
        return _cb.bot_username or ""
    except Exception:
        return ""


def get_bot_photo_id() -> str | None:
    """
    يجلب file_id لأحدث صورة بروفايل للبوت ديناميكياً ويخزنها مؤقتاً.
    يرجع None إذا لم تكن هناك صورة.
    """
    try:
        import core.bot as _cb
        if not getattr(_cb, "_bot_photo_id", None):
            bot_id = bot.get_me().id
            photos = bot.get_user_profile_photos(bot_id, limit=1)
            if photos.total_count > 0:
                _cb._bot_photo_id = photos.photos[0][-1].file_id
            else:
                _cb._bot_photo_id = ""
        return _cb._bot_photo_id or None
    except Exception:
        return None


def get_entity_photo_id(chat_id: int):
    """
    يجلب صورة بروفايل أي كيان (مجموعة أو مستخدم أو بوت).
    - للمجموعات/القنوات: يُنزّل الصورة ويرجع bytes
      (ChatPhoto.big_file_id لا يمكن استخدامه مباشرة مع send_photo)
    - للمستخدمين/البوتات: يرجع file_id من get_user_profile_photos
    يرجع None إذا لم تكن هناك صورة أو فشل التنزيل.
    """
    try:
        chat = bot.get_chat(chat_id)
        if chat.type in ("group", "supergroup", "channel"):
            photo = getattr(chat, "photo", None)
            if not photo:
                return None
            # big_file_id هو ChatPhoto — يجب تنزيله أولاً قبل إرساله
            file_info = bot.get_file(photo.big_file_id)
            downloaded = bot.download_file(file_info.file_path)
            return downloaded  # bytes — يمكن تمريره مباشرة لـ send_photo
        # مستخدم أو بوت — file_id من get_user_profile_photos قابل للإرسال مباشرة
        photos = bot.get_user_profile_photos(chat_id, limit=1)
        if photos.total_count > 0:
            return photos.photos[0][-1].file_id
        return None
    except Exception:
        return None


def get_bot_link():
    username = get_bot_username()
    name = bot_name

    # بناء رابط البوت
    if username:
        return f'<a href="https://t.me/{username}">{name}</a>'
    else:
        return f"<b>{name}</b>"


def make_open_bot_button() -> types.InlineKeyboardMarkup:
    """
    يبني زر URL لفتح خاص البوت.
    يُعاد استخدامه في أي مكان يحتاج المستخدم لبدء محادثة مع البوت.
    """
    username = get_bot_username()
    markup = types.InlineKeyboardMarkup()
    if username:
        markup.add(types.InlineKeyboardButton(
            "🔓 فتح خاص البوت",
            url=f"https://t.me/{username}"
        ))
    return markup


def send_bot_profile(chat_id: int, caption: str,
                     reply_to: int = None,
                     open_pm_button: bool = False) -> None:
    """
    يرسل صورة البوت الحالية (مجلوبة ديناميكياً) مع caption.
    إذا لم تكن هناك صورة يرسل نصاً فقط.
    """
    markup = None
    if open_pm_button:
        username = get_bot_username()
        if username:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(
                "💬 فتح خاص البوت",
                url=f"https://t.me/{username}"
            ))

    photo_id = get_bot_photo_id()
    kwargs = {
        "caption":    caption,
        "parse_mode": "HTML",
        "reply_markup": markup,
    }
    if reply_to:
        kwargs["reply_to_message_id"] = reply_to

    try:
        if photo_id:
            bot.send_photo(chat_id, photo_id, **kwargs)
        else:
            bot.send_message(chat_id, caption,
                             parse_mode="HTML",
                             disable_web_page_preview=True,
                             reply_markup=markup,
                             reply_to_message_id=reply_to)
    except Exception as e:
        print(f"[send_bot_profile] error: {e}")


def send_private_access_panel(chat_id: int, caption: str = None,
                               reply_to: int = None,
                               extra_buttons: list = None) -> None:
    """
    يرسل صورة البوت الحالية مع رسالة تطلب من المستخدم فتح الخاص،
    مع زر PM وأي أزرار إضافية.
    """
    from utils.keyboards import ui_btn, build_keyboard

    username = get_bot_username()
    if caption is None:
        caption = (
            "💬 <b>افتح خاص البوت</b>\n\n"
            "لاستخدام هذه الميزة يجب أن تبدأ محادثة خاصة مع البوت أولاً.\n"
            "اضغط الزر بالأسفل ثم اضغط <b>Start</b>."
        )

    buttons = []
    if username:
        buttons.append(ui_btn(f"💬 {bot_name}", url=f"https://t.me/{username}",
                               style="primary"))
    if extra_buttons:
        buttons.extend(extra_buttons)

    cols   = min(len(buttons), 2)
    layout = []
    rem    = len(buttons)
    while rem > 0:
        layout.append(min(cols, rem))
        rem -= cols

    markup   = build_keyboard(buttons, layout) if buttons else None
    photo_id = get_bot_photo_id()
    kwargs   = {"caption": caption, "parse_mode": "HTML", "reply_markup": markup}
    if reply_to:
        kwargs["reply_to_message_id"] = reply_to

    try:
        if photo_id:
            bot.send_photo(chat_id, photo_id, **kwargs)
        else:
            bot.send_message(chat_id, caption, parse_mode="HTML",
                             disable_web_page_preview=True,
                             reply_markup=markup,
                             reply_to_message_id=reply_to)
    except Exception as e:
        print(f"[send_private_access_panel] error: {e}")


def build_colored_buttons(buttons_data: list, cols: int = 1):
    """
    Reusable helper: takes parsed button dicts and returns an InlineKeyboardMarkup.

    buttons_data items:
        {"label": str, "url": str, "style": str}   → URL button
        {"label": str, "cb": str,  "style": str}   → callback button

    Uses utils/keyboards.py's ui_btn() and build_keyboard().
    """
    from utils.keyboards import ui_btn, build_keyboard as _kb
    btns = []
    for b in buttons_data:
        if b.get("url"):
            btns.append(ui_btn(b["label"], url=b["url"], style=b.get("style", "primary")))
        elif b.get("cb"):
            btns.append(ui_btn(b["label"], action=b["cb"], style=b.get("style", "primary")))
    if not btns:
        return None
    layout = []
    rem    = len(btns)
    while rem > 0:
        layout.append(min(cols, rem))
        rem -= cols
    return _kb(btns, layout)


def can_contact_user(user_id: int) -> bool:
    """
    يتحقق إذا كان المستخدم بدأ محادثة مع البوت ولم يحجبه.
    يرجع True إذا كان التواصل ممكناً.
    """
    try:
        bot.send_chat_action(user_id, "typing")
        return True
    except Exception:
        return False
      
# -------------------------------------------------------------- Get Shapes

def get_section_dividers():
  return random.choice(section_dividers)

def get_bullet():
  return random.choice(bullets)

def get_loading_bar():
  return loading_bar

def get_twinkle_line():
  return twinkle_line

def get_vertical_separator():
  return vertical_separator

def get_post_divider():
  return post_divider

def get_happy_cheer():
  return random.choice(happy_cheer)

def get_lines():
  return random.choice(lines)

def get_left_arrows():
  return random.choice(left_arrows)

def get_right_arrows():
  return random.choice(right_arrows)

def get_success_icons():
  return random.choice(success_icons)

def get_error_icons():
  return random.choice(error_icons)

def get_waiting_icon():
  return random.choice(waiting_icon)

def get_warning_icon():
  return random.choice(warning_icon)

def get_next_icon():
  return random.choice(next_icon)

def get_prev_icon():
  return random.choice(prev_icon)

# -------------------------------------------------------------- checks

# -------------------------------------------------------------- General Functions
def send_error (fun_name, error):
  return f"Error in {fun_name} : \n<b>{str(error)}</b>"

def send_error_reply (msg, text):
  try:
    bot.reply_to(msg, f'{get_error_icons()} {text}', parse_mode="HTML")
  except Exception as e:
    bot.reply_to(send_error("send_error_relpy", e), parse_mode="HTML")

def send_reply(msg, text, parse_html=True, buttons=None, Shape=True):
    try:
        markup = None
        if buttons:
            markup = InlineKeyboardMarkup()
            for row in buttons:
                markup.row(*[InlineKeyboardButton(b[0], callback_data=b[1]) for b in row])

        prefix = get_section_dividers() if Shape else ""
        final_text = prefix + f"<b>{text}</b>"

        bot.reply_to(
            msg,
            final_text,
            parse_mode="HTML" if parse_html else None,
            reply_markup=markup
        )

    except Exception as e:
        try:
            bot.reply_to(msg, f"{str(e)}  {get_error_icons()}", parse_mode="HTML")
        except Exception:
            pass

def send_message(chat_id, text, parse_html=True, buttons=None, reply_to_id=None):
    """
    إرسال رسالة جديدة (للبث والتنبيهات الحرجة فقط).
    استخدم send_reply للردود العادية.
    """
    try:
        markup = None
        if buttons:
            markup = InlineKeyboardMarkup()
            for row in buttons:
                markup.row(*[InlineKeyboardButton(b[0], callback_data=b[1]) for b in row])

        kwargs = {"parse_mode": "HTML" if parse_html else None, "reply_markup": markup}
        if reply_to_id:
            kwargs["reply_to_message_id"] = reply_to_id

        bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        print(f"[send_message] error: {e}")

def is_group (msg):
  if msg.chat.type in ["group", "supergroup"]:
    return True

def is_private (msg):
  if msg.chat.type == 'private':
    return True

# -------------------------------------------------------------- Text helpers

def limit_text(text, max_length=20, suffix='...'):
  """Return text truncated to max_length (keeping display as entered)."""
  if text is None:
    return ""

  text = str(text)
  if len(text) <= max_length:
    return text

  return text[:max_length].rstrip() + suffix

def format_remaining_time(seconds):
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    parts = []
    if days > 0:
        if days == 1:
            parts.append("1 يوم")
        else:
            parts.append(f"{days} أيام")
    if hours > 0:
        if hours == 1:
            parts.append("1 ساعة")
        elif hours == 2:
            parts.append("ساعتان")
        elif 3 <= hours <= 10:
            parts.append(f"{hours} ساعات")
        else:
            parts.append(f"{hours} ساعة")
    if minutes > 0:
        if minutes == 1:
            parts.append("1 دقيقة")
        elif minutes == 2:
            parts.append("دقيقتان")
        elif 3 <= minutes <= 10:
            parts.append(f"{minutes} دقائق")
        else:
            parts.append(f"{minutes} دقيقة")
    if sec > 0 and not parts:  # فقط إذا لم يكن هناك دقائق أو ساعات أو أيام
        if sec == 1:
            parts.append("1 ثانية")
        else:
            parts.append(f"{sec} ثواني")

    return " و ".join(parts)

def convert_to_arabic_numbers(number):
    return str(number).translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))

def format_ayah_number(ayah_number: int) -> str:

    # عكس الرقم كنص حتى لا يضيع الصفر
    reversed_number = str(ayah_number)[::-1]

    # تحويل للأرقام العربية
    arabic_number = convert_to_arabic_numbers(reversed_number)

    return f"{arabic_number}{ayah_divider}"

# -------------------------------------------------------------- Messages

def dont_have_power ():
  return "<b>ليس لديك صلاحية لاستخدام هذا الأمر</b>"


# ══════════════════════════════════════════
# 📤 send_result / edit_result — المعيار العالمي
# ══════════════════════════════════════════

def send_result(chat_id: int, text: str, buttons=None, reply_to_id: int = None):
    """
    إرسال رسالة بالمعيار العالمي:
    - parse_mode="HTML" دائماً
    - disable_web_page_preview=True دائماً
    - fallback تلقائي إذا كانت الرسالة المُرَدّ عليها محذوفة
    """
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = None
    if buttons:
        markup = InlineKeyboardMarkup()
        for row in buttons:
            markup.row(*[InlineKeyboardButton(b[0], callback_data=b[1]) for b in row])
    safe_send_message(chat_id, text, reply_to_id=reply_to_id, markup=markup)


def edit_result(chat_id: int, message_id: int, text: str, buttons=None):
    """
    تعديل رسالة بالمعيار العالمي:
    - parse_mode="HTML" دائماً
    - disable_web_page_preview=True دائماً
    """
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = None
    if buttons:
        markup = InlineKeyboardMarkup()
        for row in buttons:
            markup.row(*[InlineKeyboardButton(b[0], callback_data=b[1]) for b in row])
    try:
        bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=markup,
        )
    except Exception as e:
        print(f"[edit_result] error: {e}")

def safe_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )


# ══════════════════════════════════════════
# 📤 safe_send_message — إرسال آمن مع fallback
# ══════════════════════════════════════════

def safe_send_message(chat_id: int, text: str,
                      reply_to_id: int = None,
                      markup=None,
                      parse_mode: str = "HTML") -> object:
    """
    إرسال رسالة مع fallback تلقائي:
    1. يحاول الإرسال مع reply_to_message_id
    2. إذا فشل بسبب 'message to be replied not found' → يُعيد بدون reply
    3. إذا فشل كلياً → يُسجّل الخطأ ويرجع None

    يرجع كائن الرسالة عند النجاح، أو None عند الفشل.
    """
    kwargs = {
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
        "reply_markup": markup,
    }
    if reply_to_id:
        kwargs["reply_to_message_id"] = reply_to_id

    try:
        return bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        err = str(e).lower()
        # الرسالة المُرَدّ عليها محذوفة — أعد المحاولة بدون reply
        if reply_to_id and "message to be replied not found" in err:
            kwargs.pop("reply_to_message_id", None)
            try:
                return bot.send_message(chat_id, text, **kwargs)
            except Exception as e2:
                print(f"[safe_send_message] retry failed cid={chat_id}: {e2}")
                return None
        print(f"[safe_send_message] failed cid={chat_id}: {e}")
        return None