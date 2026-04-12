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
                 "تغيير اسم مدينتي", "تغيير اسم دولتي", "تغيير اسم تحالفي",
                 # quick-access shortcuts
                 "مدينة", "اقتصاد مدينتي", "سكان مدينتي", "حالة مدينتي"}


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

    # ─── مدينتي / مدينة ───
    if text in ("مدينتي", "مدينة", "حالة مدينتي"):
        if not city_id:
            bot.reply_to(message, "❌ ليس لديك مدينة.\nأنشئ دولة أولاً: <code>انشاء دولة </code>[الاسم]")
            return True
        pending = get_pending_country_invites(user_id)
        if pending:
            _show_city_invites(message, user_id, chat_id, pending)
        _send_city_overview(message, user_id, chat_id, city_id)
        return True

    # ─── اقتصاد مدينتي ───
    if text == "اقتصاد مدينتي":
        if not city_id:
            bot.reply_to(message, "❌ ليس لديك مدينة.")
            return True
        _send_economy_summary(message, city_id)
        return True

    # ─── سكان مدينتي ───
    if text == "سكان مدينتي":
        if not city_id:
            bot.reply_to(message, "❌ ليس لديك مدينة.")
            return True
        _send_population_summary(message, city_id)
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
            bot.reply_to(message, "❌ يجب أن يكون لديك دولة أولاً.\nاستخدم: <code>انشاء دولة </code>[الاسم]", parse_mode="HTML")
            return True
        from modules.city.asset_ui import open_city_store
        open_city_store(message=message, user_id=message.from_user.id, city_id=city_id)
        return True

    # ─── شراء [اسم] [كمية؟] ───
    if first_word == "شراء" and len(text.split()) > 1:
        if not city_id:
            bot.reply_to(message, "❌ يجب أن يكون لديك دولة أولاً.\nاستخدم: <code>انشاء دولة </code>[الاسم]", parse_mode="HTML")
            return True
        success, msg = _handle_buy_command(message, user_id, city_id, text)
        bot.reply_to(message, msg, parse_mode="HTML")
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
    buttons = _city_buttons(city_id, user_id, chat_id)
    send_ui(message.chat.id, text=text, buttons=buttons, layout=[3, 2], owner_id=user_id)


def _send_economy_summary(message, city_id):
    """Quick economy summary command."""
    from database.db_queries.assets_queries import calculate_city_effects
    from modules.city.city_simulation import get_population_capacity
    from database.db_queries.city_progression_queries import get_city_population
    effects = calculate_city_effects(city_id)
    pop = get_city_population(city_id)
    upkeep = round(pop * 0.001, 2)
    text = (
        f"💰 <b>ملخص اقتصاد مدينتك</b>\n{get_lines()}\n"
        f"📈 الدخل:      {effects.get('income', 0):.0f} {CURRENCY_ARABIC_NAME}\n"
        f"🔧 صيانة:      {effects.get('maintenance', 0):.0f} {CURRENCY_ARABIC_NAME}\n"
        f"👥 نفقات سكان: {upkeep:.0f} {CURRENCY_ARABIC_NAME}\n"
        f"💵 الصافي:     {effects.get('income', 0) - effects.get('maintenance', 0) - upkeep:.0f} {CURRENCY_ARABIC_NAME}\n"
        f"{get_lines()}\n"
        f"📊 مضاعفات الدخل:\n"
        f"  📚 تعليم: +{effects.get('education_bonus', 0)*100:.0f}%\n"
        f"  🛣 بنية:  +{effects.get('infra_bonus', 0)*100:.0f}%\n"
        f"  👥 سكان:  +{effects.get('population_income_bonus', 0)*100:.0f}%\n"
        f"  🧠 رضا:   ×{effects.get('satisfaction_modifier', 1.0):.2f}"
    )
    bot.reply_to(message, text, parse_mode="HTML")


def _send_population_summary(message, city_id):
    """Quick population summary command."""
    from database.db_queries.city_progression_queries import get_city_population, get_city_satisfaction
    from modules.city.city_simulation import get_population_capacity, is_city_in_rebellion
    from modules.city.city_stats import get_army_capacity, get_satisfaction_status
    pop = get_city_population(city_id)
    cap = get_population_capacity(city_id)
    army_cap = get_army_capacity(city_id)
    sat_status = get_satisfaction_status(city_id)
    in_rebellion = is_city_in_rebellion(city_id)
    upkeep = round(pop * 0.001, 2)
    text = (
        f"👥 <b>ملخص سكان مدينتك</b>\n{get_lines()}\n"
        f"👥 السكان:      {pop:,}\n"
        f"🏗 الطاقة القصوى: {cap:,}\n"
        f"📊 الامتلاء:    {pop/cap*100:.1f}%\n"
        f"🪖 طاقة الجيش:  {army_cap:,}\n"
        f"🧠 الرضا:       {sat_status['score']:.0f}/100 ({sat_status['tier']})\n"
        f"💸 نفقات يومية: {upkeep:.0f} {CURRENCY_ARABIC_NAME}\n"
    )
    if in_rebellion:
        text += "🔴 <b>المدينة في حالة تمرد!</b>\n"
    elif sat_status["effects"]:
        text += f"⚠️ {' | '.join(sat_status['effects'])}\n"
    bot.reply_to(message, text, parse_mode="HTML")


def _city_main_text(details):
    stats = details.get("stats", {})
    city_id = details.get("id")
    from database.db_queries.assets_queries import get_city_military_power
    from database.db_queries.city_progression_queries import (
        get_city_xp, get_city_population, xp_for_next_level
    )
    from modules.city.city_stats import get_satisfaction_status, get_army_capacity

    military   = get_city_military_power(city_id) if city_id else 0
    population = get_city_population(city_id) if city_id else 1000
    xp_data    = get_city_xp(city_id) if city_id else {"xp": 0, "level": 1}
    lvl, _, _  = xp_for_next_level(xp_data["xp"])
    sat_status = get_satisfaction_status(city_id) if city_id else {"score": 50, "tier": "مستقرة", "effects": [], "rebellion": False}
    army_cap   = get_army_capacity(city_id) if city_id else 500

    from modules.city.city_simulation import get_population_capacity
    pop_cap = get_population_capacity(city_id) if city_id else 10000

    sat_score = sat_status["score"]
    sat_tier  = sat_status["tier"]
    lvl_prod  = stats.get("level_production_bonus", 0.0)
    lvl_mil   = stats.get("level_military_bonus", 0.0)
    effects   = sat_status["effects"]

    text = (
        f"🏙 مدينة: {details['name']}\n"
        f"{get_lines()}\n"
        f"👥 السكان:   {population:,} / {pop_cap:,}  |  🪖 طاقة الجيش: {army_cap:,}\n"
        f"🧠 الرضا:    {sat_score:.0f}/100 ({sat_tier})\n"
        f"⭐ المستوى:  {lvl}  (+{lvl_prod*100:.0f}% إنتاج | +{lvl_mil*100:.0f}% عسكري)\n"
        f"{get_lines()}\n"
        f"💰 الاقتصاد: {stats.get('economy', 0):.1f}\n"
        f"🏥 الصحة:    {stats.get('health', 0):.1f}\n"
        f"📚 التعليم:   {stats.get('education', 0):.1f}\n"
        f"🪖 القوة:     {military:.1f}\n"
        f"🛣 البنية:    {stats.get('infrastructure', 0):.1f}\n"
        f"{get_lines()}\n"
        f"📈 الدخل: {stats.get('income', 0):.0f} | 🔧 الصيانة: {stats.get('maintenance', 0):.0f}"
    )
    if sat_status.get("rebellion"):
        text += "\n🔴 <b>تمرد نشط!</b> الدخل والبناء محجوبان."
    elif effects:
        text += f"\n⚠️ {' | '.join(effects)}"
    return text


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
# 🛒 معالج أمر الشراء الموحد
# ─────────────────────────────────────────

def _parse_buy_args(text: str) -> tuple[str, int]:
    """
    يحلل نص الأمر ويستخرج اسم العنصر والكمية.
    الصيغ المدعومة:
      شراء مشاة 10
      شراء مشاة خفيفة 10
      شراء مستشفى
    يرجع (item_name, quantity)
    """
    parts = text.split()[1:]   # أزل كلمة "شراء"
    if not parts:
        return "", 1

    # إذا كانت الكلمة الأخيرة رقماً → كمية
    if parts[-1].isdigit():
        quantity = int(parts[-1])
        item_name = " ".join(parts[:-1])
    else:
        quantity = 1
        item_name = " ".join(parts)

    return item_name.strip(), max(1, quantity)


def _resolve_item(item_name: str) -> tuple[str, dict | None]:
    """
    يبحث عن العنصر في ثلاثة مصادر بالترتيب:
      1. assets (مباني / بنية تحتية / اقتصاد / صحة / تعليم)
      2. troop_types (جنود)
      3. equipment_types (معدات)
    يرجع (kind, row) حيث kind ∈ {"asset", "troop", "equipment"} أو ("", None)
    """
    from database.db_queries.assets_queries import get_asset_by_name
    from database.connection import get_db_conn

    # 1. أصول المدينة
    asset = get_asset_by_name(item_name)
    if asset:
        return "asset", asset

    # 2. أنواع الجنود — بحث بالاسم العربي أو الإنجليزي
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM troop_types WHERE name = ? OR name_ar = ?",
        (item_name, item_name)
    )
    row = cursor.fetchone()
    if row:
        return "troop", dict(row)

    # 3. أنواع المعدات
    cursor.execute(
        "SELECT * FROM equipment_types WHERE name = ? OR name_ar = ?",
        (item_name, item_name)
    )
    row = cursor.fetchone()
    if row:
        return "equipment", dict(row)

    return "", None


def _handle_buy_command(message, user_id: int, city_id: int, text: str) -> tuple[bool, str]:
    """
    يعالج: شراء [اسم] [كمية؟]
    يدعم: أصول المدينة، جنود، معدات.
    يرجع (success, message_text)
    """
    from modules.bank.utils.constants import CURRENCY_ARABIC_NAME
    from database.db_queries.bank_queries import get_user_balance

    item_name, quantity = _parse_buy_args(text)
    if not item_name:
        return False, (
            "❌ صيغة غير صحيحة.\n\n"
            "📋 <b>الصيغة الصحيحة:</b>\n"
            "• <code>شراء [اسم العنصر]</code>\n"
            "• <code>شراء [اسم العنصر] [الكمية]</code>\n\n"
            "مثال: <code>شراء مستشفى 2</code>\n"
            "مثال: <code>شراء مشاة 10</code>"
        )

    kind, item = _resolve_item(item_name)

    if not item:
        return False, (
            f"❌ العنصر <b>{item_name}</b> غير موجود.\n\n"
            "💡 اكتب <code>متجر</code> لعرض كل العناصر المتاحة."
        )

    # ── أصول المدينة ──
    if kind == "asset":
        from modules.city.asset_service import buy_asset
        return buy_asset(user_id, city_id, item_name, quantity)

    # ── جنود ──
    if kind == "troop":
        from database.db_queries.countries_queries import get_country_by_owner
        from modules.war.force_shop import buy_troops
        country = get_country_by_owner(user_id)
        if not country:
            return False, "❌ ليس لديك دولة. أنشئ دولة أولاً."
        country = dict(country)
        ok, msg = buy_troops(user_id, country["id"], item["id"], quantity)
        if ok:
            balance = get_user_balance(user_id)
            msg += f"\n💰 الرصيد المتبقي: {balance:.0f} {CURRENCY_ARABIC_NAME}"
        return ok, msg

    # ── معدات ──
    if kind == "equipment":
        from database.db_queries.countries_queries import get_country_by_owner
        from modules.war.force_shop import buy_equipment
        country = get_country_by_owner(user_id)
        if not country:
            return False, "❌ ليس لديك دولة. أنشئ دولة أولاً."
        country = dict(country)
        ok, msg = buy_equipment(user_id, country["id"], item["id"], quantity)
        if ok:
            balance = get_user_balance(user_id)
            msg += f"\n💰 الرصيد المتبقي: {balance:.0f} {CURRENCY_ARABIC_NAME}"
        return ok, msg

    return False, "❌ نوع عنصر غير معروف."


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