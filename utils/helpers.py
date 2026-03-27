from core.config import developers_id
from core.bot import bot
from telebot import types
import random
from .constants import *

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

def get_ayah_divider():
  return ayah_divider

def get_post_divider():
  return post_divider

def get_happy_cheer():
  return random.choice(happy_cheer)

def get_lines():
  return random.choice(lines)

def get_arrow_left():
  return arrow_left

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

def is_developer (user_id):
  return user_id in developers_id

# -------------------------------------------------------------- General Functions
def send_error (fun_name, error):
  return f"Error in {fun_name} : \n<b>{str(error)}</b>"

def send_error_reply (msg, text):
  try:
    bot.reply_to(msg, f'{get_error_icons()} {text}', parse_mode="HTML")
  except Exception as e:
    bot.reply_to(send_error("send_error_relpy", e), parse_mode="HTML")

def send_reply(msg, text, parse_html=True, reply_markup=None):
  try:
    bot.reply_to (
      msg, 
      get_section_dividers() + "<b>" + text + "</b>",
      parse_mode="HTML" if parse_html else None,
      reply_markup = reply_markup
    )
  except Exception as e:
    bot.reply_to(send_error("send_reply", e), parse_mode="HTML")

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
  
# -------------------------------------------------------------- Messages

def dont_have_power ():
  return "<b>ليس لديك صلاحية لاستخدام هذا الأمر</b>"

