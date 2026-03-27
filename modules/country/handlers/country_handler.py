from core.bot import bot
from handlers.callbacks import get_user_country_id
from utils.helpers import send_reply, send_error_reply, send_error, get_section_dividers
from database.db_queries import get_user_city_details, get_country_stats, get_country_budget

from modules.country.services.country_service import CountryService

from modules.country.keyboards.country_keyboard import (
    create_my_country_markup,
    get_building_keyboard,
    get_action_keyboard,
    get_quantity_keyboard
)


from utils.constants import *
from core.config import developers_id
from telebot.types import Message

class CountryHandler:
    def __init__(self):
        pass

    def buy_hospital(self, message: Message):
        user_id = message.from_user.id
        country_id = get_user_country_id(user_id)
        if not country_id:
            bot.reply_to(message, "❌ لا تملك دولة مسجلة.")
            return
        success, response = CountryService.buy_building(user_id, country_id, 'hospital', 1)
        bot.reply_to(message, response)

    def upgrade_hospital(self, message: Message):
        user_id = message.from_user.id
        country_id = get_user_country_id(user_id)
        if not country_id:
            bot.reply_to(message, "❌ لا تملك دولة مسجلة.")
            return
        success, response = CountryService.upgrade_building(user_id, country_id, 'hospital', 1)
        bot.reply_to(message, response)

    def view_country_budget(self, message: Message):
        user_id = message.from_user.id
        country_id = get_user_country_id(user_id)
        if not country_id:
            bot.reply_to(message, "❌ لا تملك دولة مسجلة.")
            return
        budget = get_country_budget(country_id)
        if not budget:
            bot.reply_to(message, "❌ لا توجد ميزانية مسجلة.")
            return
        response = (
            f"💰 ميزانية الدولة:\n"
            f"الميزانية الحالية: {budget['current_budget']}\n"
            f"آخر تحديث: {budget['last_update_time']}"
        )
        bot.reply_to(message, response)

    def view_country_stats(self, message: Message):
        user_id = message.from_user.id
        country_id = get_user_country_id(user_id)
        if not country_id:
            bot.reply_to(message, "❌ لا تملك دولة مسجلة.")
            return
        stats = get_country_stats(country_id)
        if not stats:
            bot.reply_to(message, "❌ لا توجد إحصائيات مسجلة.")
            return
        response = (
            f"🏙️ إحصائيات الدولة:\n"
            f"💰 الاقتصاد: {stats['economy_score']}\n"
            f"🏥 الصحة: {stats['health_level']}\n"
            f"📚 التعليم: {stats['education_level']}\n"
            f"🪖 القوة العسكرية: {stats['military_power']}\n"
            f"🛣 البنية التحتية: {stats['infrastructure_level']}"
        )
        bot.reply_to(message, response)

    def my_country(self, msg):
        user_id = msg.from_user.id

        try:
            country_details = get_user_city_details(user_id)

            if not country_details:
                return send_reply(msg, "❌ ليس لديك دولة")

            shape = get_section_dividers()
            text = "\n".join(f"{shape} {v}" for v in country_details.values())

            send_reply(
                msg,
                text,
                reply_markup=create_my_country_markup(user_id)
            )

        except Exception as e:
            send_error_reply(msg, send_error("my_city", e))

    def handle_country_sections(self, call):
        try:
            _, user_id, section = call.data.split("_")

            if str(call.from_user.id) != user_id:
                return

            if section == "infrastructure":
                bot.edit_message_text(
                    "🏗 اختر نوع المنشأة:",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=get_building_keyboard(user_id)
                )

            elif section == "economy":
                country_id = get_user_country_id(call.from_user.id)
                budget = get_country_budget(country_id)

                text = (
                    f"💰 ميزانية الدولة:\n"
                    f"الميزانية الحالية: {budget['current_budget']}\n"
                    f"آخر تحديث: {budget['last_update_time']}"
                )

                bot.edit_message_text(text, call.message.chat.id, call.message.message_id)

            elif section == "main":
                self.my_city(call.message)

            else:
                bot.answer_callback_query(call.id, "🚧 قيد التطوير")

        except Exception as e:
            send_error("handle_country_sections", e)

    def open_building(self, call):
        try:
            _, user_id, b_type = call.data.split("_")

            if str(call.from_user.id) != user_id:
                return

            bot.edit_message_text(
                "⚙️ اختر العملية:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=get_action_keyboard(user_id, b_type)
            )

        except Exception as e:
            send_error("open_building", e)

    def choose_buy(self, call):
        try:
            _, user_id, b_type = call.data.split("_")

            bot.edit_message_text(
                "📦 اختر الكمية:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=get_quantity_keyboard(user_id, "do_buy", b_type)
            )

        except Exception as e:
            send_error("choose_buy", e)

    def choose_upgrade(self, call):
        try:
            _, user_id, b_type = call.data.split("_")

            bot.edit_message_text(
                "📈 اختر عدد المباني للتطوير:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=get_quantity_keyboard(user_id, "do_up", b_type)
            )

        except Exception as e:
            send_error("choose_upgrade", e)

    def do_buy(self, call):
        try:
            _, user_id, b_type, qty = call.data.split("_")

            if str(call.from_user.id) != user_id:
                return

            country_id = get_user_country_id(call.from_user.id)

            success, msg = CountryService.buy_building(
                user_id=call.from_user.id,
                country_id=country_id,
                building_type=b_type,
                quantity=int(qty)
            )

            bot.send_message(call.message.chat.id, msg)

        except Exception as e:
            send_error("do_buy", e)

    def do_upgrade(self, call):
        try:
            _, user_id, b_type, qty = call.data.split("_")

            if str(call.from_user.id) != user_id:
                return

            country_id = get_user_country_id(call.from_user.id)

            success, msg = CountryService.upgrade_building(
                user_id=call.from_user.id,
                country_id=country_id,
                building_type=b_type,
                quantity=int(qty)
            )

            bot.send_message(call.message.chat.id, msg)

        except Exception as e:
            send_error("do_upgrade", e)

    def view_stats(self, call):
        try:
            user_id = call.from_user.id
            country_id = get_user_country_id(user_id)

            if not country_id:
                bot.answer_callback_query(call.id, "❌ لا تملك دولة")
                return

            stats = get_country_stats(country_id)

            text = (
                f"📊 إحصائيات الدولة:\n"
                f"💰 الاقتصاد: {stats['economy_score']}\n"
                f"🏥 الصحة: {stats['health_level']}\n"
                f"📚 التعليم: {stats['education_level']}\n"
                f"🪖 القوة العسكرية: {stats['military_power']}\n"
                f"🛣 البنية التحتية: {stats['infrastructure_level']}"
            )

            bot.send_message(call.message.chat.id, text)

        except Exception as e:
            send_error("view_stats", e)

    def view_budget(self, call):
        try:
            user_id = call.from_user.id
            country_id = get_user_country_id(user_id)

            if not country_id:
                bot.answer_callback_query(call.id, "❌ لا تملك دولة")
                return

            budget = get_country_budget(country_id)

            text = (
                f"💰 ميزانية الدولة:\n"
                f"الميزانية الحالية: {budget['current_budget']}\n"
                f"آخر تحديث: {budget['last_update_time']}"
            )

            bot.send_message(call.message.chat.id, text)

        except Exception as e:
            send_error("view_budget", e)

# Instantiate the handler
handler = CountryHandler()

# Register the handlers
@bot.message_handler(commands=['شراء_مستشفى'])
def buy_hospital(message: Message):
    handler.buy_hospital(message)

@bot.message_handler(commands=['تطوير_مستشفى'])
def upgrade_hospital(message: Message):
    handler.upgrade_hospital(message)

@bot.message_handler(commands=['ميزانية_الدولة'])
def view_country_budget(message: Message):
    handler.view_country_budget(message)

@bot.message_handler(commands=['احصائيات_الدولة'])
def view_country_stats(message: Message):
    handler.view_country_stats(message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("country_"))
def handle_country_sections(call):
    handler.handle_country_sections(call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("building_"))
def open_building(call):
    handler.open_building(call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def choose_buy(call):
    handler.choose_buy(call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("up_"))
def choose_upgrade(call):
    handler.choose_upgrade(call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("do_buy_"))
def do_buy(call):
    handler.do_buy(call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("do_up_"))
def do_upgrade(call):
    handler.do_upgrade(call)

@bot.callback_query_handler(func=lambda call: call.data == "view_stats")
def view_stats(call):
    handler.view_stats(call)

@bot.callback_query_handler(func=lambda call: call.data == "view_budget")
def view_budget(call):
    handler.view_budget(call)

# For external imports
def my_country(msg):
    handler.my_country(msg)
    
def create_country_command(msg):
  try:
    user_id = msg.from_user.id
    success, result_message = CountryService.create_country_from_text(user_id, msg.text)

    send_reply(msg, result_message)

  except Exception as e:
    send_error_reply(msg, send_error("create_city_command", e))
