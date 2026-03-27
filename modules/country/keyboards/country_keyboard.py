from telebot import types
import random
from utils.constants import bullets
from database.db_queries.countries_queries import get_all_countries
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def btn(text, callback, style="primary"):
    return types.InlineKeyboardButton(
        text=text,
        callback_data=callback,
        style=style
    )

def get_country_style(country):
    """
    مثال لحالة الدول
    country = (id, name, status)
    status = owned / enemy / neutral
    """
    if len(country) >= 3:
        status = country[2]

        if status == "owned":
            return "success"   # 🟢
        elif status == "enemy":
            return "danger"    # 🔴
        else:
            return "primary"   # 🔵

    return "primary"

# def create_country_markup(page, user_id):
#     countries = get_all_countries()

#     PER_PAGE = 10
#     start = page * PER_PAGE
#     end = start + PER_PAGE

#     current_countries = countries[start:end]

#     layout_pattern = [2, 2, 1, 2, 2, 1]

#     markup = types.InlineKeyboardMarkup()
#     index = 0

#     for row_size in layout_pattern:

#         row = []

#         for _ in range(row_size):

#             if index >= len(current_countries):
#                 break

#             country = current_countries[index]
#             country_id, country_name = country[:2]

#             row.append(
#                 btn(
#                     f"{random.choice(bullets)} {country_name}",
#                     f"create_{user_id}_country_{country_id}",
#                     get_country_style(country)
#                 )
#             )

#             index += 1

#         if row:
#             markup.row(*row)

#     # navigation
#     nav = []

#     if start > 0:
#         nav.append(btn("➡️ السابق", f"prev_{user_id}_country_page", "secondary"))

#     if end < len(countries):
#         nav.append(btn("التالي ⬅️", f"next_{user_id}_country_page", "secondary"))

#     if nav:
#         markup.row(*nav)

#     return markup

def create_my_country_markup(user_id):
    markup = types.InlineKeyboardMarkup()

    rows = [
        [
            ("📚 الجانب الثقافي", "culture"),
            ("🏛 الجانب السياسي", "politics")
        ],
        [
            ("🪖 الجانب العسكري", "military")
        ],
        [
            ("💰 الجانب الاقتصادي", "economy"),
            ("🎡 الجانب السياحي", "tourism")
        ],
        [
            ("🏙 البنية التحتية", "infrastructure")
        ]
    ]

    for row in rows:

        buttons = [
            btn(text, f"country_{user_id}_{action}")
            for text, action in row
        ]

        markup.row(*buttons)

    # bottom buttons
    markup.row(
        btn("🏠 الرئيسية", f"country_{user_id}_main", "success"),
        btn("❌ إغلاق", f"close_{user_id}", "danger")
    )

    return markup

def create_gender_markup(user_id):
    markup = types.InlineKeyboardMarkup()

    markup.row(
        btn("🚹 ذكر", f"set_{user_id}_gender_male"),
        btn("🚺 أنثى", f"set_{user_id}_gender_female")
    )

    return markup

def get_building_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("🏥 Buy Hospital", callback_data="buy_hospital"),
        InlineKeyboardButton("⬆️ Upgrade Hospital", callback_data="upgrade_hospital")
    )
    keyboard.row(
        InlineKeyboardButton("🏭 Buy Factory", callback_data="buy_factory"),
        InlineKeyboardButton("⬆️ Upgrade Factory", callback_data="upgrade_factory")
    )
    keyboard.row(
        InlineKeyboardButton("📊 View Stats", callback_data="view_stats"),
        InlineKeyboardButton("💰 View Budget", callback_data="view_budget")
    )
    return keyboard

def get_quantity_keyboard(action, building_type):
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("1️⃣ Buy 1", callback_data=f"{action}_{building_type}_1"),
        InlineKeyboardButton("5️⃣ Buy 5", callback_data=f"{action}_{building_type}_5"),
        InlineKeyboardButton("🔟 Buy 10", callback_data=f"{action}_{building_type}_10")
    )
    return keyboard

### -----------------------------------------------------------------------------------------------


def get_building_keyboard(user_id):
    keyboard = InlineKeyboardMarkup()

    keyboard.row(
        InlineKeyboardButton("🏥 مستشفيات", callback_data=f"building_{user_id}_hospital"),
        InlineKeyboardButton("🏭 مصانع", callback_data=f"building_{user_id}_factory")
    )

    keyboard.row(
        InlineKeyboardButton("🏫 مدارس", callback_data=f"building_{user_id}_school"),
        InlineKeyboardButton("🪖 عسكرية", callback_data=f"building_{user_id}_military_base")
    )

    return keyboard

def get_action_keyboard(user_id, building_type):
    keyboard = InlineKeyboardMarkup()

    keyboard.row(
        InlineKeyboardButton("➕ شراء", callback_data=f"buy_{user_id}_{building_type}"),
        InlineKeyboardButton("⬆️ تطوير", callback_data=f"up_{user_id}_{building_type}")
    )

    return keyboard

def get_quantity_keyboard(user_id, action, building_type):
    keyboard = InlineKeyboardMarkup()

    keyboard.row(
        InlineKeyboardButton("1️⃣", callback_data=f"{action}_{user_id}_{building_type}_1"),
        InlineKeyboardButton("5️⃣", callback_data=f"{action}_{user_id}_{building_type}_5"),
        InlineKeyboardButton("🔟", callback_data=f"{action}_{user_id}_{building_type}_10")
    )

    return keyboard