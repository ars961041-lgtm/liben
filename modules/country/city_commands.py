from core.bot import bot
from modules.country.services.city_service import CityService
from modules.country.services.building_config import BUILDING_CONFIG, get_building_info
from database.db_queries.bank_queries import get_user_balance
from database.db_queries.cities_queries import get_user_city
from database.db_queries.countries_queries import (
    get_pending_country_invites, update_invite_status,
    accept_country_invite_atomic,
)
from utils.pagination import btn, edit_ui, register_action, send_ui
from utils.helpers import get_lines
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

CITY_COMMANDS = {"مدينتي", "شراء", "ترقية", "متجر", "جيش مدينتي", "جيشي",
                 "مسح مدينتي", "انضمام",
                 "تغيير اسم مدينتي", "تغيير اسم دولتي", "تغيير اسم تحالفي"}


def city_commands(message):
    if not message.text:
        return False

    text = message.text.strip()
    user_id = message.from_user.id
    chat_id = message.chat.id  # <<< أضفنا chat_id
    first_word = text.split()[0] if text.split() else ""

    if first_word not in CITY_COMMANDS and text not in CITY_COMMANDS:
        return False

    city_id = CityService.get_user_city_id(user_id)

    # ─── مدينتي ───
    if text == "مدينتي":
        if not city_id:
            bot.reply_to(message, "❌ ليس لديك مدينة.\nأنشئ دولة أولاً: <code>انشاء دولة </code>[الاسم]")
            return True
        # عرض دعوات الانضمام المعلقة أولاً
        pending = get_pending_country_invites(user_id)
        if pending:
            _show_city_invites(message, user_id, chat_id, pending)
        _send_city_overview(message, user_id, chat_id, city_id)
        return True

    # ─── جيش مدينتي ───
    if text in ("جيش مدينتي", "جيشي"):
        if not city_id:
            bot.reply_to(message, "❌ ليس لديك مدينة.")
            return True
        _send_city_army(message, city_id)
        return True

    # ─── متجر / شراء بدون args → فتح المتجر ───
    if text in ("متجر", "شراء"):
        if not city_id:
            bot.reply_to(message, "❌ ليس لديك مدينة.\nأنشئ دولة أولاً: <code>انشاء دولة </code>[الاسم]")
            return True
        from modules.city.asset_ui import open_city_store
        open_city_store(message=message, user_id=message.from_user.id, city_id=city_id)
        # open_city_store(message, user_id, city_id)
        return True

    # ─── شراء مع args: شراء hospital 5 ───
    if first_word == "شراء" and len(text.split()) > 1:
        if not city_id:
            bot.reply_to(message, "❌ ليس لديك مدينة.")
            return True
        parts = text.split()
        asset_name = parts[1]
        quantity = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
        from modules.city.asset_service import buy_asset
        success, msg = buy_asset(user_id, city_id, asset_name, quantity)
        bot.reply_to(message, msg)
        return True

    # ─── ترقية بدون args → فتح قائمة الترقية ───
    if text == "ترقية":
        if not city_id:
            bot.reply_to(message, "❌ ليس لديك مدينة.")
            return True
        from modules.city.asset_ui import open_upgrade_menu
        open_upgrade_menu(message, user_id, city_id)
        return True

    # ─── ترقية مع args: ترقية hospital 10 ───
    if first_word == "ترقية" and len(text.split()) > 1:
        if not city_id:
            bot.reply_to(message, "❌ ليس لديك مدينة.")
            return True
        parts = text.split()
        asset_name = parts[1]
        quantity = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
        from modules.city.asset_service import upgrade_asset
        success, msg = upgrade_asset(user_id, city_id, asset_name, quantity, from_level=1)
        bot.reply_to(message, msg)
        return True

    # ─── مسح مدينتي ───
    if text == "مسح مدينتي":
        from modules.country.city_management import handle_delete_city_cmd
        handle_delete_city_cmd(message)
        return True

    # ─── انضمام (رد على رسالة مالك الدولة) ───
    if text == "انضمام":
        from modules.country.city_management import handle_join_country_cmd
        handle_join_country_cmd(message)
        return True

    # ─── تغيير الأسماء ───
    if text == "تغيير اسم مدينتي":
        from modules.country.city_management import handle_rename_cmd
        handle_rename_cmd(message, "city")
        return True

    if text == "تغيير اسم دولتي":
        from modules.country.city_management import handle_rename_cmd
        handle_rename_cmd(message, "country")
        return True

    if text == "تغيير اسم تحالفي":
        from modules.country.city_management import handle_rename_cmd
        handle_rename_cmd(message, "alliance")
        return True

    return False


# ─────────────────────────────────────────
# عرض المدينة مع الأزرار
# ─────────────────────────────────────────
def _send_city_overview(message, user_id, chat_id, city_id):
    details = CityService.get_city_details(city_id)
    if not details:
        bot.reply_to(message, "❌ تعذر جلب بيانات المدينة.")
        return
    text = _city_main_text(details)
    buttons = _city_buttons(city_id, user_id, chat_id)  # <<< owner tuple
    send_ui(message.chat.id, text=text, buttons=buttons, layout=[3, 2], owner_id=user_id)


def _city_main_text(details):
    stats = details.get("stats", {})
    city_id = details.get("id")
    from database.db_queries.assets_queries import get_city_military_power
    military = get_city_military_power(city_id) if city_id else 0
    return (
        f"🏙 مدينة: {details['name']}\n"
        f"{get_lines()}\n"
        f"💰 الاقتصاد:       {stats.get('economy', 0):.1f}\n"
        f"🏥 الصحة:          {stats.get('health', 0):.1f}\n"
        f"📚 التعليم:         {stats.get('education', 0):.1f}\n"
        f"🪖 القوة العسكرية: {military:.1f}\n"
        f"🛣 البنية التحتية:  {stats.get('infrastructure', 0):.1f}\n"
        f"{get_lines()}\n"
        f"📈 الدخل: {stats.get('income', 0):.0f} | 🔧 الصيانة: {stats.get('maintenance', 0):.0f}"
    )


def _city_buttons(city_id, user_id, chat_id):
    owner = (user_id, chat_id)
    return [
        btn("💰 الاقتصاد",  "city_detail", {"t": "economy", "cid": city_id}, color="primary", owner=owner),
        btn("🏥 الصحة",     "city_detail", {"t": "health", "cid": city_id}, color="primary", owner=owner),
        btn("📚 التعليم",   "city_detail", {"t": "education", "cid": city_id}, color="primary", owner=owner),
        btn("🪖 العسكرية",  "city_detail", {"t": "military", "cid": city_id}, color="primary", owner=owner),
        btn("🏢 المباني",    "city_detail", {"t": "buildings", "cid": city_id}, color="primary", owner=owner),
    ]


@register_action("city_detail")
def handle_city_detail(call, data):
    topic = data.get("t")
    city_id = data.get("cid")
    if not city_id:
        bot.answer_callback_query(call.id, "❌ بيانات غير صالحة", show_alert=True)
        return

    details = CityService.get_city_details(city_id)
    if not details:
        bot.answer_callback_query(call.id, "❌ المدينة غير موجودة", show_alert=True)
        return

    stats = details.get("stats", {})

    if topic == "economy":
        text = (
            f"💰 اقتصاد مدينة {details['name']}\n"
            f"{get_lines()}\n"
            f"نقاط الاقتصاد: {stats.get('economy', 0):.1f}\n"
            f"الدخل:   {stats.get('income', 0):.0f} {CURRENCY_ARABIC_NAME}\n"
            f"الصيانة: {stats.get('maintenance', 0):.0f} {CURRENCY_ARABIC_NAME}\n"
            f"الصافي:  {stats.get('income', 0) - stats.get('maintenance', 0):.0f} {CURRENCY_ARABIC_NAME}\n\n"
            f"لتحسينه: شراء مصنع أو بنك محلي أو سوق تجاري"
        )
    elif topic == "health":
        text = (
            f"🏥 صحة مدينة {details['name']}\n"
            f"{get_lines()}\n"
            f"مستوى الصحة: {stats.get('health', 0):.1f}\n\n"
            f"لتحسينه: شراء مستشفى أو عيادة"
        )
    elif topic == "education":
        text = (
            f"📚 تعليم مدينة {details['name']}\n"
            f"{get_lines()}\n"
            f"مستوى التعليم: {stats.get('education', 0):.1f}\n\n"
            f"لتحسينه: شراء مدرسة أو جامعة"
        )
    elif topic == "military":
        text = (
            f"🪖 قوة مدينة {details['name']}\n"
            f"{get_lines()}\n"
            f"القوة العسكرية: {stats.get('military', 0):.1f}\n\n"
            f"لتحسينه: شراء جنود أو معدات"
        )
    elif topic == "buildings":
        from database.db_queries.assets_queries import get_city_assets
        rows = get_city_assets(city_id)
        if not rows:
            text = f"🏢 مباني مدينة {details['name']}\n{get_lines()}\nلا توجد مباني بعد.\n\nللشراء: متجر"
        else:
            text = f"🏢 مباني مدينة {details['name']}\n{get_lines()}\n"
            for r in rows:
                text += f"{r['emoji']} {r['name_ar']}: {r['quantity']} وحدة | مستوى {r['level']}\n"
            text += "\nللترقية: ترقية"
    else:
        text = "❌ قسم غير معروف"

    back_buttons = [
        btn("🔙 رجوع", "city_back", {"cid": city_id}, color="w",
            owner=(call.from_user.id, call.message.chat.id))
    ]
    edit_ui(call, text=text, buttons=back_buttons, layout=[1])


@register_action("city_back")
def handle_city_back(call, data):
    city_id = data.get("cid")
    details = CityService.get_city_details(city_id)
    if not details:
        bot.answer_callback_query(call.id, "❌ المدينة غير موجودة", show_alert=True)
        return
    edit_ui(call, text=_city_main_text(details),
            buttons=_city_buttons(city_id, call.from_user.id, call.message.chat.id), layout=[3, 2])


# ─────────────────────────────────────────
# قائمة المباني
# ─────────────────────────────────────────
def _buildings_list_text():
    lines = []
    for key, cfg in BUILDING_CONFIG.items():
        lines.append(f"{cfg['emoji']} {cfg['name_ar']} ({key}) — {cfg['base_cost']} {CURRENCY_ARABIC_NAME}")
    return "\n".join(lines)


def _send_buildings_menu(message, user_id, city_id):
    text = f"🏢 المباني المتاحة للشراء:\n{get_lines()}\n" + _buildings_list_text()
    text += "\n\nللشراء: شراء [نوع] [كمية]\nمثال: شراء hospital 2"
    bot.reply_to(message, text)


# ─────────────────────────────────────────
# 📨 دعوات الانضمام للدولة
# ─────────────────────────────────────────
def _show_city_invites(message, user_id, chat_id, pending):
    text = "📨 <b>دعوات انضمام معلقة:</b>\n\n"
    buttons = []
    for inv in pending[:5]:
        text += f"🏙 <b>{inv['city_name']}</b> — 🏳️ {inv.get('country_name', '')}\n"
        buttons.append(btn(f"✅ قبول — {inv['city_name']}", "country_invite_accept",
                           data={"inv_id": inv["id"]},
                           owner=(user_id, chat_id), color="su"))
        buttons.append(btn("❌ رفض", "country_invite_reject",
                           data={"inv_id": inv["id"]},
                           owner=(user_id, chat_id), color="d"))
    layout = [2] * len(pending[:5])
    send_ui(chat_id, text=text, buttons=buttons, layout=layout, owner_id=user_id)


@register_action("country_invite_accept")
def on_country_invite_accept(call, data):
    user_id = call.from_user.id
    inv_id  = int(data["inv_id"])

    ok, result = accept_country_invite_atomic(inv_id, user_id)
    if not ok:
        bot.answer_callback_query(call.id, result, show_alert=True)
        return

    bot.answer_callback_query(call.id, "✅ قبلت الدعوة! المدينة أصبحت لك.", show_alert=True)
    try:
        bot.edit_message_text("✅ تم قبول دعوة الانضمام.", call.message.chat.id, call.message.message_id)
    except Exception:
        pass


@register_action("country_invite_reject")
def on_country_invite_reject(call, data):
    inv_id = int(data["inv_id"])
    update_invite_status(inv_id, "rejected")
    bot.answer_callback_query(call.id, "❌ تم رفض الدعوة.")
    try:
        bot.edit_message_text("❌ رفضت دعوة الانضمام.", call.message.chat.id, call.message.message_id)
    except Exception:
        pass


# ─────────────────────────────────────────
# 🪖 جيش المدينة
# ─────────────────────────────────────────
def _send_city_army(message, city_id):
    from database.db_queries.war_queries import get_city_troops, get_city_equipment

    troops = get_city_troops(city_id)
    equipment = get_city_equipment(city_id)

    total_atk = 0.0
    total_def = 0.0
    total_hp  = 0.0

    text = f"🪖 <b>جيش مدينتك</b>\n{get_lines()}\n\n"

    if troops:
        text += "⚔️ <b>الجنود:</b>\n"
        for t in troops:
            t = dict(t)
            qty = max(0, t.get("quantity", 0))
            atk = t.get("attack", 0) * qty
            dfn = t.get("defense", 0) * qty
            hp  = t.get("hp", 0) * qty
            total_atk += atk
            total_def += dfn
            total_hp  += hp
            text += f"  {t.get('emoji','🪖')} {t.get('name_ar','؟')} × {qty}\n"
    else:
        text += "⚔️ لا يوجد جنود\n"

    if equipment:
        text += "\n🛡 <b>المعدات:</b>\n"
        for e in equipment:
            e = dict(e)
            qty = max(0, e.get("quantity", 0))
            total_atk += e.get("attack_bonus", 0) * qty
            total_def += e.get("defense_bonus", 0) * qty
            text += f"  {e.get('emoji','🔧')} {e.get('name_ar','؟')} × {qty}\n"
    else:
        text += "\n🛡 لا توجد معدات\n"

    total_power = max(0, total_atk + total_def)
    text += (
        f"\n{get_lines()}\n"
        f"⚔️ الهجوم الكلي: {max(0, total_atk):.0f}\n"
        f"🛡 الدفاع الكلي: {max(0, total_def):.0f}\n"
        f"❤️ الحياة الكلية: {max(0, total_hp):.0f}\n"
        f"💪 القوة الإجمالية: {total_power:.0f}"
    )

    bot.reply_to(message, text, parse_mode="HTML")