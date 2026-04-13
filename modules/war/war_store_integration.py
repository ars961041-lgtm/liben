"""
War store UI — Troops & Equipment.
Entry: "🪖 قوات المدينة" button → hub (Troops / Equipment)
All navigation uses edit_ui. send_ui only on first open from text.
"""
import logging

from core.bot import bot
from database.db_queries.war_queries import (
    get_all_troop_types, get_city_troop, get_troop_type_by_id, add_city_troops,
    get_all_equipment_types, get_equipment_type_by_id,
    get_city_equipment_item, add_city_equipment,
)
from database.db_queries.bank_queries import get_user_balance, deduct_user_balance
from utils.pagination import btn, send_ui, edit_ui, register_action, grid
from utils.helpers import get_lines
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

logger = logging.getLogger(__name__)


def _apply_troop_discount(base_cost: float) -> tuple[float, float]:
    """Returns (discounted_cost, discount_pct). discount_pct=0 if no event active."""
    try:
        from modules.progression.global_events import get_event_effect
        discount = get_event_effect("troop_cost_discount")
        if discount > 0:
            logger.info("[EVENT_APPLIED] type=troop_cost_discount, discount=%.0f%%, base=%.0f, final=%.0f",
                        discount * 100, base_cost, base_cost * (1 - discount))
            return round(base_cost * (1 - discount), 2), discount
    except Exception:
        pass
    logger.debug("[EVENT_SKIP] troop_cost_discount — no active event or category mismatch")
    return base_cost, 0.0


def _apply_equipment_discount(base_cost: float) -> tuple[float, float]:
    """Returns (discounted_cost, discount_pct). discount_pct=0 if no event active."""
    try:
        from modules.progression.global_events import get_event_effect
        discount = get_event_effect("equipment_cost_discount")
        if discount > 0:
            logger.info("[EVENT_APPLIED] type=equipment_cost_discount, discount=%.0f%%, base=%.0f, final=%.0f",
                        discount * 100, base_cost, base_cost * (1 - discount))
            return round(base_cost * (1 - discount), 2), discount
    except Exception:
        pass
    logger.debug("[EVENT_SKIP] equipment_cost_discount — no active event or category mismatch")
    return base_cost, 0.0

GREEN = "su"
RED   = "d"
BLUE  = "p"


def _owner(call):
    return (call.from_user.id, call.message.chat.id)


# ══════════════════════════════════════════
# 🪖 Hub — نقطة الدخول من رسالة نصية
# ══════════════════════════════════════════

def open_troop_store(message, user_id: int, city_id: int):
    """Called from city store — opens troops list directly."""
    owner   = (user_id, message.chat.id)
    troops  = [dict(t) for t in get_all_troop_types()]
    balance = get_user_balance(user_id)
    text, buttons, layout = _troop_list_content(city_id, troops, balance, owner)
    send_ui(message.chat.id, text=text, buttons=buttons, layout=layout, owner_id=user_id)


def open_equipment_store(message, user_id: int, city_id: int):
    """Called from city store — opens equipment list directly."""
    owner     = (user_id, message.chat.id)
    equipment = [dict(e) for e in get_all_equipment_types()]
    balance   = get_user_balance(user_id)
    text, buttons, layout = _equipment_list_content(city_id, equipment, balance, owner)
    send_ui(message.chat.id, text=text, buttons=buttons, layout=layout, owner_id=user_id)


def _troop_list_content(city_id, troops, balance, owner):
    text = (
        f"🪖 متجر الجنود\n"
        f"{get_lines()}\n"
        f"💰 رصيدك: {balance:.0f} {CURRENCY_ARABIC_NAME}\n\n"
        f"اختر نوع الجنود:"
    )
    buttons = [
        btn(f"{t['emoji']} {t['name_ar']}",
            "troop_item", {"tid": t["id"], "cid": city_id}, color=BLUE, owner=owner)
        for t in troops
    ]
    back = [btn("رجوع", "store_back_sectors", {"cid": city_id}, color=RED, owner=owner)]
    layout = grid(len(buttons), 3) + [1]
    return text, buttons + back, layout


def _equipment_list_content(city_id, equipment, balance, owner):
    text = (
        f"🛡 متجر المعدات\n"
        f"{get_lines()}\n"
        f"💰 رصيدك: {balance:.0f} {CURRENCY_ARABIC_NAME}\n\n"
        f"اختر نوع المعدات:"
    )
    buttons = [
        btn(f"{e['emoji']} {e['name_ar']}",
            "equipment_item", {"eid": e["id"], "cid": city_id}, color=BLUE, owner=owner)
        for e in equipment
    ]
    back = [btn("رجوع", "store_back_sectors", {"cid": city_id}, color=RED, owner=owner)]
    layout = grid(len(buttons), 3) + [1]
    return text, buttons + back, layout


# ══════════════════════════════════════════
# Callbacks (edit_ui)
# ══════════════════════════════════════════

@register_action("open_troop_store")
def handle_open_troop_store(call, data):
    city_id = data.get("cid")
    owner   = _owner(call)
    troops  = [dict(t) for t in get_all_troop_types()]
    balance = get_user_balance(call.from_user.id)
    if not troops:
        bot.answer_callback_query(call.id, "❌ لا توجد قوات متاحة", show_alert=True)
        return
    text, buttons, layout = _troop_list_content(city_id, troops, balance, owner)
    edit_ui(call, text=text, buttons=buttons, layout=layout)


@register_action("open_equipment_store")
def handle_open_equipment_store(call, data):
    city_id   = data.get("cid")
    owner     = _owner(call)
    equipment = [dict(e) for e in get_all_equipment_types()]
    balance   = get_user_balance(call.from_user.id)
    if not equipment:
        bot.answer_callback_query(call.id, "❌ لا توجد معدات متاحة", show_alert=True)
        return
    text, buttons, layout = _equipment_list_content(city_id, equipment, balance, owner)
    edit_ui(call, text=text, buttons=buttons, layout=layout)


# ══════════════════════════════════════════
# 🪖 تفاصيل جندي + كمية (back → open_troop_store)
# ══════════════════════════════════════════


# ══════════════════════════════════════════
# 🔍 تفاصيل جندي + كمية
# ══════════════════════════════════════════

@register_action("troop_item")
def handle_troop_item(call, data):
    troop_id = data.get("tid")
    city_id  = data.get("cid")
    owner    = _owner(call)

    troop_type = get_troop_type_by_id(troop_id)
    if not troop_type:
        bot.answer_callback_query(call.id, "❌ هذالنوع غير موجود", show_alert=True)
        return

    balance   = get_user_balance(call.from_user.id)
    owned_row = get_city_troop(city_id, troop_id)
    owned_qty = owned_row["quantity"] if owned_row else 0

    effective_cost, discount = _apply_troop_discount(troop_type["base_cost"])
    price_line = (
        f"💰 السعر:   ~~{troop_type['base_cost']:.0f}~~ {effective_cost:.0f} {CURRENCY_ARABIC_NAME} / وحدة 🎉"
        if discount > 0 else
        f"💰 السعر:   {troop_type['base_cost']:.0f} {CURRENCY_ARABIC_NAME} / وحدة"
    )

    text = (
        f"{troop_type['emoji']} {troop_type['name_ar']}\n"
        f"{get_lines()}\n"
        f"⚔️ الهجوم:  {troop_type['attack']}\n"
        f"🛡 الدفاع:  {troop_type['defense']}\n"
        f"❤️ الصحة:   {troop_type['hp']}\n"
        f"{price_line}\n"
        f"🪖 تمتلك:  {owned_qty} وحدة\n"
        f"💰 رصيدك:  {balance:.0f} {CURRENCY_ARABIC_NAME}\n\n"
        f"اختر الكمية للشراء:"
    )
    qty_btns = _qty_buttons("troop_buy", {"tid": troop_id, "cid": city_id},
                             effective_cost, balance, owner=owner)
    back = [btn("رجوع", "open_troop_store", {"cid": city_id}, color=RED, owner=owner)]
    edit_ui(call, text=text, buttons=qty_btns + back,
            layout=grid(len(qty_btns), 3) + [1])


@register_action("troop_buy")
def handle_troop_buy(call, data):
    troop_id = data.get("tid")
    city_id  = data.get("cid")
    quantity = int(data.get("q", 1))
    owner    = _owner(call)

    troop_type = get_troop_type_by_id(troop_id)
    if not troop_type:
        bot.answer_callback_query(call.id, "❌ هذا النوع غير موجود", show_alert=True)
        return

    total_cost = troop_type["base_cost"] * quantity
    # ─── apply active event discount ───
    effective_unit, discount = _apply_troop_discount(troop_type["base_cost"])
    total_cost = round(effective_unit * quantity)
    base_cost  = troop_type["base_cost"] * quantity
    balance    = get_user_balance(call.from_user.id)

    if total_cost > balance:
        bot.answer_callback_query(call.id,
            f"❌ رصيدك {balance:.0f} — تحتاج {total_cost:.0f} {CURRENCY_ARABIC_NAME}", show_alert=True)
        return

    deduct_user_balance(call.from_user.id, total_cost)
    add_city_troops(city_id, troop_id, quantity)

    remaining  = get_user_balance(call.from_user.id)
    event_line = (
        f"🎯 خصم الحدث: -{discount*100:.0f}% (حملة التجنيد)\n"
        f"💡 الخصم: -{base_cost - total_cost:.0f} {CURRENCY_ARABIC_NAME}\n"
    ) if discount > 0 else ""
    msg = (
        f"✅ تم الشراء بنجاح\n"
        f"📦 العنصر: {troop_type['emoji']} {troop_type['name_ar']}\n"
        f"🔢 الكمية: {quantity}\n"
        f"🪖 السعر الأصلي: {base_cost:.0f} {CURRENCY_ARABIC_NAME}\n"
        f"{event_line}"
        f"✔ المدفوع الفعلي: {total_cost:.0f} {CURRENCY_ARABIC_NAME}\n"
        f"💳 الرصيد المتبقي: {remaining:.0f} {CURRENCY_ARABIC_NAME}"
    )
    bot.answer_callback_query(call.id)
    back = [btn("رجوع", "open_troop_store", {"cid": city_id}, color=RED, owner=owner)]
    edit_ui(call, text=msg, buttons=back, layout=[1])


# ══════════════════════════════════════════
# 🛡 قائمة المعدات
# ══════════════════════════════════════════

@register_action("open_equipment_list")
def handle_open_equipment_list(call, data):
    city_id   = data.get("cid")
    owner     = _owner(call)
    equipment = [dict(e) for e in get_all_equipment_types()]
    balance   = get_user_balance(call.from_user.id)

    if not equipment:
        bot.answer_callback_query(call.id, "❌ لتوجد معدات متاحة", show_alert=True)
        return

    text = (
        f"🛡 متجر المعدات\n"
        f"{get_lines()}\n"
        f"💰 رصيدك: {balance:.0f} {CURRENCY_ARABIC_NAME}\n\n"
        f"اختر نوع المعدات:"
    )
    buttons = [
        btn(f"{e['emoji']} {e['name_ar']}",
            "equipment_item", {"eid": e["id"], "cid": city_id}, color=BLUE, owner=owner)
        for e in equipment
    ]
    buttons.append(btn("رجوع", "open_equipment_store", {"cid": city_id}, color=RED, owner=owner))
    edit_ui(call, text=text, buttons=buttons,
            layout=grid(len(equipment), 3) + [1])


# ══════════════════════════════════════════
# 🔍 تفاصيل معدة + كمية
# ══════════════════════════════════════════

@register_action("equipment_item")
def handle_equipment_item(call, data):
    eq_id   = data.get("eid")
    city_id = data.get("cid")
    owner   = _owner(call)

    eq = get_equipment_type_by_id(eq_id)
    if not eq:
        bot.answer_callback_query(call.id, "❌ هذالنوع غير موجود", show_alert=True)
        return

    balance   = get_user_balance(call.from_user.id)
    owned_row = get_city_equipment_item(city_id, eq_id)
    owned_qty = owned_row["quantity"] if owned_row else 0

    # build effects line
    effects = []
    if eq["attack_bonus"]:
        effects.append(f"⚔️ هجوم +{eq['attack_bonus']}")
    if eq["defense_bonus"]:
        effects.append(f"🛡 دفاع +{eq['defense_bonus']}")
    if eq["special_effect"]:
        effects.append(f"✨ {eq['special_effect']}")
    effects_text = " | ".join(effects) if effects else "لتأثيرات خاصة"

    effective_cost, discount = _apply_equipment_discount(eq["base_cost"])
    price_line = (
        f"💰 السعر:     ~~{eq['base_cost']:.0f}~~ {effective_cost:.0f} {CURRENCY_ARABIC_NAME} / وحدة 🎉"
        if discount > 0 else
        f"💰 السعر:     {eq['base_cost']:.0f} {CURRENCY_ARABIC_NAME} / وحدة"
    )

    text = (
        f"{eq['emoji']} {eq['name_ar']}\n"
        f"{get_lines()}\n"
        f"📊 التأثيرات: {effects_text}\n"
        f"{price_line}\n"
        f"🛡 تمتلك:    {owned_qty} وحدة\n"
        f"💰 رصيدك:    {balance:.0f} {CURRENCY_ARABIC_NAME}\n\n"
        f"اختر الكمية للشراء:"
    )
    qty_btns = _qty_buttons("equipment_buy", {"eid": eq_id, "cid": city_id},
                             effective_cost, balance, owner=owner)
    back = [btn("رجوع", "open_equipment_list", {"cid": city_id}, color=RED, owner=owner)]
    edit_ui(call, text=text, buttons=qty_btns + back,
            layout=grid(len(qty_btns), 3) + [1])


@register_action("equipment_buy")
def handle_equipment_buy(call, data):
    eq_id    = data.get("eid")
    city_id  = data.get("cid")
    quantity = int(data.get("q", 1))
    owner    = _owner(call)

    eq = get_equipment_type_by_id(eq_id)
    if not eq:
        bot.answer_callback_query(call.id, "❌ هذا النوع غير موجود", show_alert=True)
        return

    total_cost = eq["base_cost"] * quantity
    # ─── apply active event discount ───
    effective_unit, discount = _apply_equipment_discount(eq["base_cost"])
    total_cost = round(effective_unit * quantity)
    base_cost  = eq["base_cost"] * quantity
    balance    = get_user_balance(call.from_user.id)

    if total_cost > balance:
        bot.answer_callback_query(call.id,
            f"❌ رصيدك {balance:.0f} — تحتاج {total_cost:.0f} {CURRENCY_ARABIC_NAME}", show_alert=True)
        return

    deduct_user_balance(call.from_user.id, total_cost)
    add_city_equipment(city_id, eq_id, quantity)

    remaining  = get_user_balance(call.from_user.id)
    event_line = (
        f"🎯 خصم الحدث: -{discount*100:.0f}% (تخفيضات الأسلحة)\n"
        f"💡 الخصم: -{base_cost - total_cost:.0f} {CURRENCY_ARABIC_NAME}\n"
    ) if discount > 0 else ""
    msg = (
        f"✅ تم الشراء بنجاح\n"
        f"📦 العنصر: {eq['emoji']} {eq['name_ar']}\n"
        f"🔢 الكمية: {quantity}\n"
        f"🪖 السعر الأصلي: {base_cost:.0f} {CURRENCY_ARABIC_NAME}\n"
        f"{event_line}"
        f"✔ المدفوع الفعلي: {total_cost:.0f} {CURRENCY_ARABIC_NAME}\n"
        f"💳 الرصيد المتبقي: {remaining:.0f} {CURRENCY_ARABIC_NAME}"
    )
    bot.answer_callback_query(call.id)
    back = [btn("رجوع", "open_equipment_list", {"cid": city_id}, color=RED, owner=owner)]
    edit_ui(call, text=msg, buttons=back, layout=[1])


# ══════════════════════════════════════════
# أزرار الكمية
# ══════════════════════════════════════════

def _qty_buttons(action: str, base_data: dict, cost_per: float,
                 balance: float, max_qty: int = 9999,
                 owner: tuple = None) -> list:
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
        buttons.append(btn(f"1  ({cost_per:.0f})", action,
                           {**base_data, "q": 1}, owner=owner))
    return buttons
