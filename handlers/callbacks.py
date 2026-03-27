from telebot.apihelper import ApiTelegramException
from telebot import types
from telebot.types import CallbackQuery

from core.bot import bot
from handlers.users import send_gendered_welcome
from modules.country.keyboards.country_keyboard import create_my_country_markup
from modules.country.services.country_service import CountryService
from utils.helpers import get_warning_icon, get_success_icons, get_section_dividers, get_error_icons
from database.connection import get_db_conn
from database.db_queries import (
    get_user_city, 
    assign_country_to_user, 
    get_user_city_details, 
    get_user_gender, 
    get_country_stats, 
    get_country_budget
)

def get_user_country_id(user_id):
    """Helper function to retrieve the country ID for a user."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM countries WHERE owner_id = ?', (user_id,))
    result = cursor.fetchone()
    return result[0] if result else None

def its_not_for_you (msg_id, user_id, expected_user_id):
  if user_id != expected_user_id:
    bot.answer_callback_query(msg_id, f"لا يمكنك استخدام هذه الأزرار!", show_alert=True)
    return False
  return True

def callback_query(call):
  chat_id = call.message.chat.id
  user_id = str(call.from_user.id)
  msg_id = call.message.message_id
  text = call.message.text
  reply_markup = call.message.reply_markup

  parts = call.data.split("_")
  expected_user_id = parts[1]

  success_icon = get_success_icons()
  error_icon = get_error_icons()

  if call.data.startswith("top_") or call.data.startswith("close_"):
    handle_top_callbacks(call)
    return

  if not its_not_for_you (call.id, user_id, expected_user_id):
      return

  if call.data.startswith("create_"):
    entity = parts[2]
    city_id = parts[3]
    key = f'create_city_{user_id}_{chat_id}'

    if entity in ["city", "country"]:
      
      check_country = get_user_city(int(user_id))
      if check_country:
        bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=f"{success_icon} لديك دولة بالفعل '{check_country}'.")
        return

      assign_country_to_user(city_id, int(user_id))
      bot.answer_callback_query(call.id, f"{success_icon} تم تسجيل الدولة لك!")
      bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=f"{success_icon} تم اختيار الدولة وتسجيلها باسمك.")
      return 
    
  elif parts[0] in ["prev", "next"]:
    bot.answer_callback_query(call.id, text=f"{get_warning_icon()} ميزة التنقل غير مدعومة حالياً")


  elif parts[0] in ["city", "country"]:
    country_entities = parts[2]

    if country_entities == "culture":
      new_text = "أهلا بك في الجانب الثقافي"
      new_markup = create_my_country_markup(user_id)
      if text == new_text and reply_markup == new_markup:
        bot.answer_callback_query(call.id, text=f"{success_icon} أنت بالفعل هنا")
        return

      try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=new_text,
            reply_markup=new_markup
        )
        bot.answer_callback_query(call.id)
      except ApiTelegramException as e:
        if "message is not modified" in str(e):
            bot.answer_callback_query(call.id, text=f"{success_icon} أنت بالفعل هنا")
        else:
            raise  

    elif country_entities == "politics":
        new_text = "أهلا بك في الجانب السياسي"
        new_markup = create_my_country_markup(user_id)
        if text == new_text and reply_markup == new_markup:
            bot.answer_callback_query(call.id, text=f"{success_icon} لا يوجد تغيير")
            return

        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=new_text,
                reply_markup=new_markup
            )
            bot.answer_callback_query(call.id)
        except ApiTelegramException as e:
            if "message is not modified" in str(e):
                bot.answer_callback_query(call.id, text=f"{success_icon} أنت بالفعل هنا")
            else:
                raise
              
    elif country_entities == "main":
      city_details = get_user_city_details(user_id)
      if city_details:
        get_shape = get_section_dividers()
        reply = '\n'.join(f"{get_shape} {value}" for value in city_details.values())
      else:
        reply = f"{error_icon} لم يتم العثور على بيانات الدولة."

      new_markup = create_my_country_markup(user_id)
      if text == reply and reply_markup == new_markup:
        bot.answer_callback_query(call.id, text=f"{success_icon} أنت بالفعل هنا")
        return

      try:
        bot.edit_message_text(
          chat_id=chat_id,
          message_id=msg_id,
          text=reply,
          reply_markup=new_markup,
          parse_mode="HTML"
        )
        bot.answer_callback_query(call.id)
      except ApiTelegramException as e:
        if "message is not modified" in str(e):
          bot.answer_callback_query(call.id, text=f"{success_icon} أنت بالفعل هنا")
        else:
          raise

  elif parts[0] == "set":
    if parts[2] == "gender":
      conn = get_db_conn()
      gender = get_user_gender(int(user_id))
      if gender:
        bot.edit_message_text(f"{success_icon}لقد تم تحديد جنسك بالطبع '{gender}'", chat_id, msg_id)
        return

      gender = parts[-1]
      gndr = "ذكر" if gender == "male" else "أنثى"

      conn.execute("UPDATE users SET gender = ? WHERE id = ?", (gndr, int(user_id)))
        # send_gendered_welcome(call.message, gender)
      bot.edit_message_text(f"{success_icon} تم حفظ الجنس بنجاح!", chat_id, msg_id)

  elif parts[0] == "close":
    closed_text = f"{get_section_dividers()} تم الإغلاق بنجاح"

    try:
      bot.edit_message_text(
        chat_id=chat_id,
        message_id=msg_id,
        text=closed_text,
        reply_markup=None
      )
      bot.answer_callback_query(call.id, text=f"{success_icon} تم الإغلاق")
    except ApiTelegramException as e:
      if "message is not modified" in str(e):
        bot.answer_callback_query(call.id, text=f"{success_icon} تم الإغلاق مسبقًا")
      else:
        raise


def show_top_menu(message, user_id=None, edit=False, msg_id=None):
    from telebot import types
    if user_id is None:
        user_id = message.from_user.id

    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("توب الفلوس 💰", callback_data=f"top_money_{user_id}"),
        types.InlineKeyboardButton("توب التفاعل 📊", callback_data=f"top_interaction_{user_id}")
    )
    markup.row(types.InlineKeyboardButton("مسح 🗑️", callback_data=f"close_{user_id}"))

    text = "‌‌‏أهلاً بك عزيزي في قائمة الاوامر :\n• اختر نوع التوب من الازرار"
    if edit and msg_id:
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg_id, text=text, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, text, reply_markup=markup)


def handle_top_callbacks(call):
    chat_id = call.message.chat.id
    user_id = str(call.from_user.id)
    msg_id = call.message.message_id

    parts = call.data.split("_")
    expected_user_id = parts[-1]

    if not its_not_for_you(call.id, user_id, expected_user_id):
        return

    if call.data.startswith("top_money_"):
        from modules.bank.services.bank_service import format_top_richest
        username = call.from_user.username or call.from_user.first_name
        top_text = format_top_richest(int(user_id), username=username, limit=20)
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("رجوع ↩️", callback_data=f"top_back_{user_id}"),
            types.InlineKeyboardButton("مسح 🗑️", callback_data=f"close_{user_id}")
        )
        bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=top_text, reply_markup=markup)

    elif call.data.startswith("top_interaction_"):
        from handlers.tops.tops import get_top_messages
        if not hasattr(call.message, 'chat') or call.message.chat.type not in ['group', 'supergroup']:
            top_text = "توب التفاعل متاح فقط في المجموعات!"
        else:
            top_text = get_top_messages(call.message.chat.id)
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("رجوع ↩️", callback_data=f"top_back_{user_id}"),
            types.InlineKeyboardButton("مسح 🗑️", callback_data=f"close_{user_id}")
        )
        bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=top_text, reply_markup=markup)

    elif call.data.startswith("top_back_"):
        show_top_menu(call.message, user_id=int(user_id), edit=True, msg_id=msg_id)

    elif call.data.startswith("close_"):
        closed_text = f"{get_section_dividers()} تم الإغلاق بنجاح"
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=closed_text,
                reply_markup=None
            )
        except ApiTelegramException:
            pass

def handle_buy_building(callback: CallbackQuery, building_type: str, quantity: int, cost_per_unit: float):
    user_id = callback.from_user.id
    country_id = get_user_country_id(user_id)  # Assume this helper exists

    success, message = CountryService.buy_building(user_id, country_id, building_type, quantity, cost_per_unit)
    callback.bot.answer_callback_query(callback.id, message)


def handle_upgrade_building(callback: CallbackQuery, building_type: str, quantity: int, upgrade_cost_per_level: float):
    user_id = callback.from_user.id
    country_id = get_user_country_id(user_id)

    success, message = CountryService.upgrade_building(user_id, country_id, building_type, quantity, upgrade_cost_per_level)
    callback.bot.answer_callback_query(callback.id, message)


def handle_view_country_stats(callback: CallbackQuery):
    user_id = callback.from_user.id
    country_id = get_user_country_id(user_id)

    stats = get_country_stats(country_id)
    if not stats:
        callback.bot.answer_callback_query(callback.id, "No stats available for your country.")
        return

    message = (
        f"🏙️ Country Stats:\n"
        f"💰 Economy Score: {stats['economy_score']}\n"
        f"🏥 Health Level: {stats['health_level']}\n"
        f"📚 Education Level: {stats['education_level']}\n"
        f"🪖 Military Power: {stats['military_power']}\n"
        f"🛣 Infrastructure Level: {stats['infrastructure_level']}"
    )
    callback.bot.send_message(callback.message.chat.id, message)


def handle_view_country_budget(callback: CallbackQuery):
    user_id = callback.from_user.id
    country_id = get_user_country_id(user_id)

    budget = get_country_budget(country_id)
    if not budget:
        callback.bot.answer_callback_query(callback.id, "No budget data available.")
        return

    message = (
        f"💰 Country Budget:\n"
        f"Current Budget: {budget['current_budget']}\n"
        f"Last Updated: {budget['last_update_time']}"
    )
    callback.bot.send_message(callback.message.chat.id, message)