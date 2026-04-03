# war_handler.py

from core.bot import bot
from database.db_queries.countries_queries import get_city_by_id
from modules.war.services.war_service import execute_attack
from utils.pagination import btn, send_ui, edit_ui, register_action


# ────────── فتح نظام الحرب ──────────
def open_war_menu(message):
    buttons = [
        btn("🔥 هجوم", "war_attack", owner=(message.from_user.id, message.chat.id), color="d"),
        btn("📊 تقاريري", "war_reports", owner=(message.from_user.id, message.chat.id), color="p")
    ]
    send_ui(
        chat_id=message.chat.id,
        text="⚔️ <b>نظام الحرب</b>\nاختر ما تريد:",
        buttons=buttons,
        layout=[2],
        owner_id=message.from_user.id
    )


# ────────── اختيار هدف للهجوم ──────────
@register_action("war_attack")
def show_targets(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    from database.db_queries.countries_queries import (
        get_country_by_owner,
        get_all_cities_of_country_by_country_id
    )
    from database.db_queries.countries_queries import get_capital_city

    # 🏳️ التحقق: هل هو مالك دولة؟
    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ فقط مالك الدولة يمكنه الهجوم!")
        return

    capital_city = get_capital_city(user_id)

    if not capital_city:
        bot.answer_callback_query(call.id, "❌ لا تملك عاصمة!")
        return

    attacker_city = capital_city["id"]

    # 🏙 جلب كل مدن الدولة
    country_cities = get_all_cities_of_country_by_country_id(country["id"])
    player_city_ids = [c["id"] for c in country_cities]

    # 🎯 جلب الأهداف
    targets = get_all_targets(player_city_ids)

    if not targets:
        bot.answer_callback_query(call.id, "❌ لا توجد مدن متاحة للهجوم!")
        return

    # 🔘 الأزرار
    buttons = [
        btn(
            f"🏙 {t['name']}",
            "attack_target",
            data={"attacker": attacker_city, "defender": t['id']},
            owner=(user_id, chat_id),
            color="d"
        )
        for t in targets
    ]

    send_ui(
        chat_id,
        text="🎯 اختر هدف للهجوم:",
        buttons=buttons,
        layout=[1, 1],
        owner_id=user_id
    )
# ────────── تنفيذ الهجوم ──────────
@register_action("attack_target")
def execute_war(call, data):
    attacker_city_id = int(data.get("attacker"))
    defender_city_id = int(data.get("defender"))

    attacker_city = get_city_by_id(attacker_city_id)
    defender_city = get_city_by_id(defender_city_id)

    # رسالة انتظار
    edit_ui(call, text="⚔️ جاري تنفيذ المعركة...\n⏳ انتظر قليلاً")

    # تنفيذ المعركة
    report = execute_attack(
        attacker_city_id,
        defender_city_id,
        attacker_name=attacker_city["name"],
        defender_name=defender_city["name"]
    )

    bot.send_message(call.message.chat.id, report, parse_mode="HTML")


# ────────── تقارير الحرب (مبدئي) ──────────
@register_action("war_reports")
def war_reports(call, data):
    bot.answer_callback_query(call.id, "🚧 قريبًا...")


# ────────── دالة مساعدة لجلب المدن المستهدفة ──────────
def get_all_targets(player_city_ids: list):
    """
    تجلب كل المدن التي يمكن مهاجمتها، مع استثناء جميع مدن الدولة الخاصة باللاعب
    """
    from database.connection import get_db_conn

    conn = get_db_conn()
    cursor = conn.cursor()

    if not player_city_ids:
        cursor.execute("SELECT id, name FROM cities LIMIT 10")
        return cursor.fetchall()

    placeholders = ",".join(["?"] * len(player_city_ids))
    query = f"SELECT id, name FROM cities WHERE id NOT IN ({placeholders}) LIMIT 10"
    cursor.execute(query, player_city_ids)
    return cursor.fetchall()