"""
Full UI for the asset purchase & upgrade system.
All button flows live here.
"""
from core.bot import bot
from database.db_queries.assets_queries import (
    get_all_sectors, get_assets_by_sector, get_asset_by_id,
    get_city_assets, get_city_asset,
)
from database.db_queries.bank_queries import get_user_balance
from modules.city.asset_service import buy_asset, upgrade_asset, calc_buy_cost, calc_upgrade_cost
from modules.war.war_store_integration import open_troop_store, open_equipment_store
from utils.pagination import  btn, edit_ui, paginate_list, register_action, send_ui, grid
from utils.helpers import get_lines
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

# color codes
GREEN  = "su"   # 🟢 green  → buy / confirm
RED  = "d"    # 🔴 red    → cancel / danger

def _owner(call):
    return (call.from_user.id, call.message.chat.id)


# ══════════════════════════════════════════
# 🏪 متجر المدينة — نقطة الدخول
# ══════════════════════════════════════════

def open_city_store(message, user_id: int, city_id: int):
    owner   = (user_id, message.chat.id)
    sectors = get_all_sectors()
    balance = get_user_balance(user_id)

    text = (
        f"🏪 متجر المدينة\n"
        f"{get_lines()}\n"
        f"💰 رصيدك: {balance:.0f} {CURRENCY_ARABIC_NAME}\n\n"
        f"اختر القطاع:"
    )
    buttons = [
        btn(f"{s['emoji']} {s['name']}", "store_sector",
            {"sid": s["id"], "cid": city_id}, owner=owner)
        for s in sectors
    ]
    
    buttons.append(btn("🪖 قوات المدينة", "open_troop_store", {"cid": city_id}, color=GREEN, owner=owner))
    buttons.append(btn("🛡 معدات المدينة", "open_equipment_store", {"cid": city_id}, color=GREEN, owner=owner))
    
    buttons.append(btn("مدينتي", "city_back", {"cid": city_id}, color=RED, owner=owner))
    send_ui(message.chat.id, text=text, buttons=buttons,
            layout=grid(len(sectors), 2) + [2, 1], owner_id=user_id, reply_to=message.message_id)


# ══════════════════════════════════════════
# 📂 عناصر القطاع
# ══════════════════════════════════════════

@register_action("store_sector")
def handle_store_sector(call, data):
    sector_id = data.get("sid")
    city_id   = data.get("cid")
    page      = int(data.get("p", 0))
    owner     = _owner(call)

    assets = get_assets_by_sector(sector_id)
    if not assets:
        bot.answer_callback_query(call.id, "❌ لا توجد عناصر في هذا القطاع", show_alert=True)
        return

    paged, total_pages = paginate_list(assets, page, per_page=6)
    balance = get_user_balance(call.from_user.id)

    text = f"🏪 عناصر القطاع\nا {get_lines()}\n💰 رصيدك: {balance:.0f} {CURRENCY_ARABIC_NAME}\n\n"
    for a in paged:
        text += f"{a['emoji']} {a['name_ar']} — {a['base_price']:.0f} {CURRENCY_ARABIC_NAME}\n"

    buttons = [
        btn(f"{a['emoji']} {a['name_ar']}", "store_item",
            {"aid": a["id"], "cid": city_id}, color=GREEN, owner=owner)
        for a in paged
    ]
    nav = []
    if page < total_pages - 1:
        nav.append(btn("التالي ⬅️", "store_sector",
                       {"sid": sector_id, "cid": city_id, "p": page + 1}, owner=owner))
    if page > 0:
        nav.append(btn("➡️ السابق", "store_sector",
                       {"sid": sector_id, "cid": city_id, "p": page - 1}, owner=owner))
    nav.append(btn("رجوع", "store_back_sectors", {"cid": city_id}, color=RED, owner=owner))

    edit_ui(call, text=text, buttons=buttons + nav,
            layout=grid(len(buttons), 2) + [len(nav)])


# ══════════════════════════════════════════



def _profit_block(asset):

    net_profit = asset["income"] - asset["maintenance"]

    return (
        "\n📊 <b>الربحية</b>\n<blockquote>"
        f"الدخل: {asset['income']:.0f}\n"
        f"الصيانة: -{asset['maintenance']:.0f}\n"
        f"ا--------\n"
        f"الصافي: <b>+{net_profit:.0f}</b>\n</blockquote>\n"
    )
    
# ══════════════════════════════════════════
# 🔍 تفاصيل عنصر + اختيار الكمية
# ══════════════════════════════════════════
@register_action("store_item")
def handle_store_item(call, data):

    asset_id = data.get("aid")
    city_id  = data.get("cid")
    owner    = _owner(call)

    asset   = get_asset_by_id(asset_id)
    balance = get_user_balance(call.from_user.id)

    if not asset:
        bot.answer_callback_query(call.id, "❌ عنصر غير موجود", show_alert=True)
        return

    owned = get_city_assets(city_id)
    owned_qty = sum(r["quantity"] for r in owned if r["asset_id"] == asset_id)

    text = (
        f"{asset['emoji']} <b>{asset['name_ar']}</b>\n"
        f"{get_lines()}\n"
        f"<blockquote>💰 السعر: {asset['base_price']:.0f} {CURRENCY_ARABIC_NAME} / وحدة\n"
        f"🔧 الصيانة: {asset['maintenance']:.0f} / وحدة\n"
        f"📈 الدخل الأساسي: {asset['income']:.0f} / وحدة\n"
        f"📊 التأثيرات:\n{_stat_lines(asset)}"
        f"🏗 تمتلك: {owned_qty} وحدة\n"
        f"💰 رصيدك: {balance:.0f} {CURRENCY_ARABIC_NAME}\n</blockquote>\n"
    )

    text += _profit_block(asset)
    text += "\nاختر الكمية للشراء:"

    buttons = _qty_buttons("store_buy", {"aid": asset_id, "cid": city_id}, asset["base_price"], balance, owner=owner)

    back = [btn(
        "رجوع",
        "store_sector",
        {"sid": asset["sector_id"], "cid": city_id},
        color=RED,
        owner=owner
    )]

    edit_ui(
        call,
        text=text,
        buttons=buttons + back,
        layout=grid(len(buttons), 3) + [1]
    )
    
# ══════════════════════════════════════════
# 🟢 تنفيذ الشراء
# ══════════════════════════════════════════

@register_action("store_buy")
def handle_store_buy(call, data):
    asset_id = data.get("aid")
    city_id  = data.get("cid")
    quantity = int(data.get("q", 1))
    owner    = _owner(call)

    asset = get_asset_by_id(asset_id)
    if not asset:
        bot.answer_callback_query(call.id, "❌ عنصر غير موجود", show_alert=True)
        return

    success, msg = buy_asset(call.from_user.id, city_id, asset["name"], quantity)
    bot.answer_callback_query(call.id)

    back = [btn("رجوع", "store_item",
                {"aid": asset_id, "cid": city_id}, color=RED, owner=owner)]
    edit_ui(call, text=msg, buttons=back, layout=[1])


# ══════════════════════════════════════════
# 🔼 قائمة الترقية
# ══════════════════════════════════════════

def open_upgrade_menu(message, user_id: int, city_id: int):
    owned = get_city_assets(city_id)
    if not owned:
        bot.reply_to(message, "❌ لا تمتلك أي عناصر بعد.\nاستخدم متجر للشراء.")
        return

    owner   = (user_id, message.chat.id)
    balance = get_user_balance(user_id)
    text = (
        f"🔼 ترقية العناصر\n{get_lines()}\n"
        f"💰 رصيدك: {balance:.0f} {CURRENCY_ARABIC_NAME}\n\nاختر العنصر للترقية:"
    )

    buttons = []
    for r in owned:
        if r["level"] >= r.get("max_level", 10):
            continue
        buttons.append(btn(
            f"{r['emoji']} {r['name_ar']} (مستوى {r['level']})",
            "upgrade_item", {"aid": r["asset_id"], "cid": city_id}, owner=owner)
        )
    if not buttons:
        bot.reply_to(message, "✅ جميع عناصرك في أقصى مستوى!")
        return

    buttons.append(btn("رجوع", "city_back", {"cid": city_id}, color=RED, owner=owner))
    send_ui(message.chat.id, text=text, buttons=buttons,
            layout=grid(len(buttons) - 1, 2) + [1], owner_id=user_id, reply_to=message.message_id)


@register_action("upgrade_item")
def handle_upgrade_item(call, data):
    asset_id = data.get("aid")
    city_id  = data.get("cid")
    owner    = _owner(call)

    asset   = get_asset_by_id(asset_id)
    owned   = get_city_assets(city_id)
    rows    = [r for r in owned if r["asset_id"] == asset_id]
    balance = get_user_balance(call.from_user.id)

    if not rows:
        bot.answer_callback_query(call.id, "❌ لا تمتلك هذا العنصر", show_alert=True)
        return

    text = (
        f"🔼 ترقية {asset['emoji']} {asset['name_ar']}\n"
        f"{get_lines()}\n💰 رصيدك: {balance:.0f} {CURRENCY_ARABIC_NAME}\n\n"
    )
    for r in rows:
        cost_1 = calc_upgrade_cost(asset, r["level"], 1)
        text += f"مستوى {r['level']}: {r['quantity']} وحدة | ترقية وحدة = {cost_1:.0f} {CURRENCY_ARABIC_NAME}\n"
    text += "\nاختر المستوى للترقية:"

    level_btns = [
        btn(f"مستوى {r['level']} ({r['quantity']} وحدة)",
            "upgrade_level", {"aid": asset_id, "cid": city_id, "fl": r["level"]},
            owner=owner)
        for r in rows if r["level"] < asset.get("max_level", 10)
    ]
    back = [btn("رجوع", "upgrade_back", {"cid": city_id}, color=RED, owner=owner)]
    edit_ui(call, text=text, buttons=level_btns + back,
            layout=[1] * len(level_btns) + [1])


@register_action("upgrade_level")
def handle_upgrade_level(call, data):
    asset_id   = data.get("aid")
    city_id    = data.get("cid")
    from_level = int(data.get("fl", 1))
    owner      = _owner(call)

    asset   = get_asset_by_id(asset_id)
    row     = get_city_asset(city_id, asset_id, from_level)
    balance = get_user_balance(call.from_user.id)

    if not row:
        bot.answer_callback_query(call.id, "❌ لا توجد وحدات في هذا المستوى", show_alert=True)
        return

    max_qty  = row["quantity"]
    cost_per = calc_upgrade_cost(asset, from_level, 1)
    text = (
        f"🔼 ترقية {asset['emoji']} {asset['name_ar']}\n"
        f"المستوى: {from_level} → {from_level + 1}\n"
        f"{get_lines()}\n"
        f"تمتلك: {max_qty} وحدة\n"
        f"💰 رصيدك: {balance:.0f} {CURRENCY_ARABIC_NAME}\n\n"
        f"اختر الكمية للترقية:"
    )
    qty_btns = _qty_buttons("upgrade_confirm",
                             {"aid": asset_id, "cid": city_id, "fl": from_level},
                             cost_per, balance, max_qty=max_qty, owner=owner)
    back = [btn("رجوع", "upgrade_item", {"aid": asset_id, "cid": city_id},
                color=RED, owner=owner)]
    edit_ui(call, text=text, buttons=qty_btns + back,
            layout=grid(len(qty_btns), 3) + [1])


@register_action("upgrade_confirm")
def handle_upgrade_confirm(call, data):
    asset_id   = data.get("aid")
    city_id    = data.get("cid")
    from_level = int(data.get("fl", 1))
    quantity   = int(data.get("q", 1))
    owner      = _owner(call)

    asset = get_asset_by_id(asset_id)
    success, msg = upgrade_asset(call.from_user.id, city_id, asset["name"], quantity, from_level)
    bot.answer_callback_query(call.id)

    back = [btn("رجوع", "upgrade_item",
                {"aid": asset_id, "cid": city_id}, color=RED, owner=owner)]
    edit_ui(call, text=msg, buttons=back, layout=[1])

# ══════════════════════════════════════════
# 🔙 أزرار الرجوع
# ══════════════════════════════════════════
@register_action("store_back_sectors")
def handle_back_sectors(call, data):
    city_id = data.get("cid")
    owner   = _owner(call)
    sectors = get_all_sectors()
    balance = get_user_balance(call.from_user.id)

    text = (
        f"🏪 متجر المدينة\nا {get_lines()}\n"
        f"💰 رصيدك: {balance:.0f} {CURRENCY_ARABIC_NAME}\n\nاختر القطاع:"
    )

    buttons = [
        btn(f"{s['emoji']} {s['name']}", "store_sector",
            {"sid": s["id"], "cid": city_id}, owner=owner)
        for s in sectors
    ]

    # ✅ أضف زر قوات المدينة
    buttons.append(btn("🪖 قوات المدينة", "open_troop_store", {"cid": city_id}, color=GREEN, owner=owner))
    buttons.append(btn("🛡 معدات المدينة", "open_equipment_store", {"cid": city_id}, color=GREEN, owner=owner))

    # زر الرجوع
    buttons.append(btn("مدينتي", "city_back", {"cid": city_id}, color=RED, owner=owner))

    edit_ui(call, text=text, buttons=buttons, layout=grid(len(sectors), 2) + [2, 1])

@register_action("upgrade_back")
def handle_upgrade_back(call, data):
    city_id = data.get("cid")
    owner   = _owner(call)
    owned   = get_city_assets(city_id)
    balance = get_user_balance(call.from_user.id)
    text = (
        f"🔼 ترقية العناصر\n{get_lines()}\n"
        f"💰 رصيدك: {balance:.0f} {CURRENCY_ARABIC_NAME}\n\nاختر العنصر:"
    )

    buttons = []
    for r in owned:
        if r["level"] >= r.get("max_level", 10):
            continue
        buttons.append(btn(
            f"{r['emoji']} {r['name_ar']} (مستوى {r['level']})",
            "upgrade_item", {"aid": r["asset_id"], "cid": city_id}, owner=owner)
        )
    buttons.append(btn("رجوع", "city_back", {"cid": city_id}, color=RED, owner=owner))
    edit_ui(call, text=text, buttons=buttons, layout=grid(len(buttons) - 1, 2) + [1])


# ══════════════════════════════════════════
# 🛠 دوال مساعدة
# ══════════════════════════════════════════

def _stat_lines(asset: dict) -> str:
    # Direct stat contributions
    direct = [
        ("stat_economy",        "💰 اقتصاد"),
        ("stat_health",         "🏥 صحة"),
        ("stat_education",      "📚 تعليم"),
        ("stat_infrastructure", "🛣 بنية"),
    ]
    lines = [f"  {lbl}: +{asset[k]}" for k, lbl in direct if asset.get(k)]

    # Indirect effects hint
    name = asset.get("name", "")
    if asset.get("stat_health", 0) > 0:
        lines.append("  ↳ يقلل تكلفة صيانة الجيش")
    if asset.get("stat_education", 0) > 0:
        lines.append("  ↳ يزيد دخل المدينة ونمو السكان")
    if asset.get("stat_infrastructure", 0) > 0:
        lines.append("  ↳ يعزز كفاءة الاقتصاد وقوة الجيش")

    return ("\n".join(lines) + "\n") if lines else "  لا تأثيرات مباشرة\n"


def _qty_buttons(action: str, base_data: dict, cost_per: float,
                 balance: float, max_qty: int = 9999,
                 owner: tuple = None) -> list:
    """Show only affordable quantities — stop at first unaffordable."""
    buttons = []
    for q in [1, 5, 10, 25, 50, 100]:
        if q > max_qty:
            break
        total = cost_per * q
        if total > balance:
            break
        buttons.append(btn(f"{q}  ({total:.0f})", action,
                           {**base_data, "q": q}, owner=owner))
    if not buttons:
        # can't afford even 1 — show it anyway so user sees the price
        buttons.append(btn(f"1  ({cost_per:.0f})", action,
                           {**base_data, "q": 1}, owner=owner))
    return buttons


