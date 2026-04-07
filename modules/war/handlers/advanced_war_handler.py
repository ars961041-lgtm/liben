"""
معالج الحرب المتقدمة
"""
import time as _time
from core.bot import bot
from utils.pagination import btn, send_ui, edit_ui, register_action, paginate_list, grid
from database.db_queries.countries_queries import get_country_by_owner
from database.db_queries.advanced_war_queries import (
    add_discovered_country, get_all_cards, get_user_cards, add_user_card, get_card_by_id,
    get_reputation, ensure_reputation, get_battle_history_for_country,
    get_active_battles_for_country, get_battle_by_id,
    get_spy_units, ensure_spy_units, get_my_pending_support_requests,
)
from database.db_queries.bank_queries import get_user_balance, deduct_user_balance
from modules.war.power_calculator import get_country_power, get_country_power_breakdown
from modules.war.services.advanced_war_service import (
    launch_attack, send_spies, handle_support_response, apply_card_to_battle,
    set_country_visibility, get_attackable_targets, verify_hidden_attack,
    send_support_request_all, send_support_request_targeted,
)

from utils.helpers import get_lines
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

def _back_btn(user_id, chat_id):
    return btn("🔙 رجوع", "adv_war_main_back", data={}, owner=(user_id, chat_id))


def _war_main_buttons(user_id, chat_id):
    return [
        btn("⚔️ شن هجوم",       "adv_war_attack",     data={"page": 0}, owner=(user_id, chat_id), color="d"),
        btn("🕵️ إرسال جواسيس",  "adv_war_spy",        data={"page": 0}, owner=(user_id, chat_id)),
        btn("🃏 متجر البطاقات",  "adv_war_cards_shop", data={"page": 0}, owner=(user_id, chat_id)),
        btn("🎒 بطاقاتي",        "adv_war_my_cards",   data={"page": 0}, owner=(user_id, chat_id)),
        btn("📊 سجل المعارك",    "adv_war_history",    data={},          owner=(user_id, chat_id)),
        btn("🏆 سمعتي",          "adv_war_reputation", data={},          owner=(user_id, chat_id), color="su"),
        btn("🔍 معاركي النشطة",  "adv_war_active",     data={},          owner=(user_id, chat_id), color="su"),
        btn("📣 طلبات الدعم",    "adv_war_support_menu", data={},        owner=(user_id, chat_id), color="su"),
    ]


# ══════════════════════════════════════════
# 🏠 القائمة الرئيسية
# ══════════════════════════════════════════

def open_advanced_war_menu(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    from core import memory as _mem, intelligence
    _mem.set_last_command(user_id, "عرش الحرب")

    country = get_country_by_owner(user_id)
    if not country:
        from core.personality import send_with_delay, no_country_msg
        send_with_delay(chat_id, no_country_msg(), delay=0.4,
                        reply_to=message.message_id)
        return

    country = dict(country)
    active = get_active_battles_for_country(country["id"])
    power = get_country_power(country["id"])
    status_line = f"⚔️ معارك نشطة: {len(active)}" if active else "☮️ لا توجد معارك نشطة"

    from database.db_queries.advanced_war_queries import get_visibility
    vis = get_visibility(country["id"])
    vis_icon = "🌑 مخفية" if vis and vis["visibility_mode"] == "hidden" else "☀️ ظاهرة"

    # مستوى الدولة
    from modules.war.country_level import get_level_info
    lvl_info = get_level_info(country["id"])

    # اقتراح ذكي
    suggestion = intelligence.get_suggestion_text(user_id)

    from core.personality import typing_delay
    typing_delay(chat_id, 0.5)

    buttons = _war_main_buttons(user_id, chat_id)
    has_alliance = any(b["action"] == "alliance_buy_upgrade" for b in buttons)
    layout = ([1] if has_alliance else []) + [2, 2, 2, 2, 2, 1]

    send_ui(chat_id=chat_id,
            text=(f"⚔️ <b>نظام الحرب المتقدم</b>\n"
                  f"🏳️ دولتك: <b>{country['name']}</b>\n"
                  f"🎖 المستوى: {lvl_info['label']} | 💪 القوة: {power:.0f}\n"
                  f"👁 الرؤية: {vis_icon} | {status_line}"
                  f"{suggestion}\n\nاختر ما تريد:"),
            buttons=buttons, layout=layout, owner_id=user_id,
            reply_to=message.message_id)


@register_action("adv_war_main_back")
def back_to_war_main(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!")
        return
    country = dict(country)
    active = get_active_battles_for_country(country["id"])
    power = get_country_power(country["id"])
    status_line = f"⚔️ معارك نشطة: {len(active)}" if active else "☮️ لا توجد معارك نشطة"
    from database.db_queries.advanced_war_queries import get_visibility
    vis = get_visibility(country["id"])
    vis_icon = "🌑 مخفية" if vis and vis["visibility_mode"] == "hidden" else "☀️ ظاهرة"
    edit_ui(call,
            text=(f"⚔️ <b>نظام الحرب المتقدم</b>\n"
                  f"🏳️ دولتك: <b>{country['name']}</b>\n"
                  f"💪 قوتك: {power:.0f} | 👁 الرؤية: {vis_icon}\n"
                  f"{status_line}\n\nاختر ما تريد:"),
            buttons=_war_main_buttons(user_id, chat_id),
            layout=[2, 2, 2, 2])


# ══════════════════════════════════════════
# ⚔️ نظام الهجوم الذكي
# ══════════════════════════════════════════

@register_action("adv_war_attack")
def show_attack_menu(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!")
        return
    country = dict(country)

    targets = get_attackable_targets(user_id)
    page = int(data.get("page", 0))

    if not targets:
        edit_ui(call,
                text=("🎯 <b>اختيار الهدف</b>\n\n"
                      "لا توجد أهداف مكتشفة حالياً.\n\n"
                      "💡 تلميح:\n"
                      "• تجسس على دول لاكتشافها\n"
                      "• أو أدخل كود هجوم دولة مخفية"),
                buttons=[
                    btn("🔑 إدخال كود هجوم", "adv_war_enter_code",
                        data={}, owner=(user_id, chat_id), color="p"),
                    _back_btn(user_id, chat_id),
                ], layout=[1, 1])
        return

    items, total_pages = paginate_list(targets, page, per_page=6)
    text = f"🎯 <b>اختر هدفاً للهجوم</b> (صفحة {page+1}/{total_pages})\n\n"

    from modules.war.country_level import get_country_tier, TIER_LABELS, get_tier_label
    my_tier = get_country_tier(country["id"])

    buttons = []
    for c in items:
        vis_icon  = "🌑" if c.get("visibility") == "hidden" else "🏳️"
        target_tier  = get_country_tier(c["id"])
        tier_label   = TIER_LABELS.get(target_tier, "🟡")

        # فحص إذا كان الهجوم مسموحاً
        from modules.war.country_level import ALLOWED_ATTACKS
        allowed = ALLOWED_ATTACKS.get((my_tier, target_tier), True)
        lock_icon = "" if allowed else " 🔒"

        text += f"{vis_icon} <b>{c['name']}</b> {tier_label}{lock_icon}\n"
        buttons.append(btn(
            f"{vis_icon} {c['name']} {tier_label}{lock_icon}",
            "adv_war_select_target",
            data={"target_id": c["id"], "target_name": c["name"]},
            owner=(user_id, chat_id),
            color="d" if allowed else "p"
        ))

    nav = []
    if page > 0:
        nav.append(btn("◀️", "adv_war_attack", data={"page": page-1}, owner=(user_id, chat_id)))
    if page < total_pages - 1:
        nav.append(btn("▶️", "adv_war_attack", data={"page": page+1}, owner=(user_id, chat_id)))
    nav.append(btn("🔑 إدخال كود", "adv_war_enter_code", data={}, owner=(user_id, chat_id)))
    nav.append(_back_btn(user_id, chat_id))

    layout = grid(len(items), 2) + [len(nav)]
    edit_ui(call, text=text, buttons=buttons + nav, layout=layout)


@register_action("adv_war_enter_code")
def enter_attack_code(call, data):
    """يطلب من المستخدم إدخال كود الهجوم"""
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    from utils.pagination.router import set_state
    set_state(user_id, chat_id, "awaiting_attack_code", data={})

    edit_ui(call,
            text=("🔑 <b>إدخال كود الهجوم</b>\n\n"
                  "أرسل الكود المكون من 5 أرقام للدولة المخفية.\n"
                  "مثال: <code>12345</code>\n\n"
                  "⏱️ الكود يتجدد كل 24 ساعة."),
            buttons=[_back_btn(user_id, chat_id)], layout=[1])


@register_action("adv_war_select_target")
def show_attack_options(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    target_id = data["target_id"]
    target_name = data.get("target_name", "الهدف")

    from modules.war.country_level import get_tier_label, get_country_tier, ALLOWED_ATTACKS, TIER_LABELS
    my_cid   = dict(get_country_by_owner(user_id))["id"]
    my_tier  = get_country_tier(my_cid)
    def_tier = get_country_tier(int(target_id))
    allowed  = ALLOWED_ATTACKS.get((my_tier, def_tier), True)

    # مقارنة الفئات فقط — بدون أرقام
    tier_order = {"weak": 0, "medium": 1, "strong": 2}
    diff = tier_order.get(def_tier, 1) - tier_order.get(my_tier, 1)
    if diff > 0:
        tier_diff = "⚠️ الهدف أقوى منك!"
    elif diff < 0:
        tier_diff = "✅ الهدف أضعف منك"
    else:
        tier_diff = "⚖️ نفس الفئة"

    tier_info = f"فئتك: {get_tier_label(my_cid)} | فئة الهدف: {get_tier_label(int(target_id))}"
    penalty_note = "\n⚠️ <b>هجوم بفعالية مخفضة 20% (قوي → متوسط)</b>" if (my_tier == "strong" and def_tier == "medium") else ""
    lock_note    = "\n🔒 <b>هذا الهجوم غير مسموح!</b>" if not allowed else ""

    buttons = [
        btn("⚔️ هجوم عادي",       "adv_war_confirm_attack",
            data={"target_id": target_id, "type": "normal"},        owner=(user_id, chat_id), color="d"),
        btn("💥 هجوم مباغت",       "adv_war_confirm_attack",
            data={"target_id": target_id, "type": "sudden"},        owner=(user_id, chat_id), color="d"),
        btn("🎭 هجوم وهمي",        "adv_war_confirm_attack",
            data={"target_id": target_id, "type": "fake"},          owner=(user_id, chat_id)),
        btn("🏚️ غارة على المباني", "adv_war_confirm_attack",
            data={"target_id": target_id, "type": "building_raid"}, owner=(user_id, chat_id)),
        btn("🔙 رجوع", "adv_war_attack", data={"page": 0}, owner=(user_id, chat_id)),
    ]
    edit_ui(call,
            text=(f"🎯 الهدف: <b>{target_name}</b>\n"
                  f"🎖 {tier_info}\n"
                  f"{tier_diff}{penalty_note}{lock_note}\n\n"
                  f"⚔️ <b>عادي</b> — 20 دقيقة، قوة كاملة\n"
                  f"💥 <b>مباغت</b> — 5 دقائق، قوة أقل 30%\n"
                  f"🎭 <b>وهمي</b> — يُربك العدو، لا ضرر\n"
                  f"🏚️ <b>غارة</b> — يستهدف المباني\n\nاختر نوع الهجوم:"),
            buttons=buttons, layout=[2, 2, 1])


@register_action("adv_war_confirm_attack")
def confirm_attack(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    target_id = int(data["target_id"])
    battle_type = data.get("type", "normal")
    type_names = {"normal": "⚔️ عادي", "sudden": "💥 مباغت", "fake": "🎭 وهمي", "building_raid": "🏚️ غارة"}

    ok, *result = launch_attack(user_id, target_id, battle_type)
    if not ok:
        bot.answer_callback_query(call.id, result[0], show_alert=True)
        return

    battle_id, travel_sec = result[0], result[1]
    edit_ui(call,
            text=(f"✅ <b>تم إطلاق الهجوم!</b>\n\n"
                  f"🗡 النوع: {type_names.get(battle_type, battle_type)}\n"
                  f"⏱️ وقت الوصول: {travel_sec // 60} دقيقة\n"
                  f"🆔 رقم المعركة: #{battle_id}\n\nسيتم إشعارك عند بدء القتال."),
            buttons=[_back_btn(user_id, chat_id)], layout=[1])


# ══════════════════════════════════════════
# 📣 نظام الدعم المتقدم
# ══════════════════════════════════════════

@register_action("adv_war_support_menu")
def show_support_menu(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    pending = get_my_pending_support_requests(user_id)
    pending_count = len(pending)

    edit_ui(call,
            text=(f"📣 <b>نظام الدعم</b>\n\n"
                  f"📥 طلبات معلقة: {pending_count}\n\n"
                  f"اختر ما تريد:"),
            buttons=[
                btn("🔥 طلب دعم من الجميع",    "adv_war_req_support_all",
                    data={}, owner=(user_id, chat_id), color="su"),
                btn("🎯 طلب دعم من دولة محددة", "adv_war_req_support_specific",
                    data={"page": 0}, owner=(user_id, chat_id), color="p"),
                btn(f"📥 طلباتي ({pending_count})", "adv_war_view_requests",
                    data={}, owner=(user_id, chat_id), color="p"),
                _back_btn(user_id, chat_id),
            ], layout=[1, 1, 1, 1])


@register_action("adv_war_req_support_all")
def request_support_all(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!")
        return
    country = dict(country)

    active = get_active_battles_for_country(country["id"])
    if not active:
        bot.answer_callback_query(call.id, "❌ لا توجد معارك نشطة!", show_alert=True)
        return

    battle = active[0]
    side = "attacker" if battle["attacker_country_id"] == country["id"] else "defender"

    ok, msg = send_support_request_all(battle["id"], user_id, side)
    bot.answer_callback_query(call.id, msg, show_alert=True)


@register_action("adv_war_req_support_specific")
def request_support_specific(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    page = int(data.get("page", 0))

    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!")
        return
    country = dict(country)

    active = get_active_battles_for_country(country["id"])
    if not active:
        bot.answer_callback_query(call.id, "❌ لا توجد معارك نشطة!", show_alert=True)
        return

    battle = active[0]
    side = "attacker" if battle["attacker_country_id"] == country["id"] else "defender"

    from database.db_queries.alliances_queries import get_alliance_by_user, get_alliance_by_id
    alliance = get_alliance_by_user(user_id)
    if not alliance:
        bot.answer_callback_query(call.id, "❌ لست في أي تحالف!", show_alert=True)
        return

    alliance_data = get_alliance_by_id(alliance["id"])
    members = [m for m in alliance_data["members"]
               if (m["user_id"] if isinstance(m, dict) else m[0]) != user_id]

    if not members:
        bot.answer_callback_query(call.id, "❌ لا يوجد أعضاء آخرون في التحالف!", show_alert=True)
        return

    # جلب بيانات الدول
    from database.db_queries.countries_queries import get_country_by_owner as _gcbo
    items_data = []
    for m in members:
        muid = m["user_id"] if isinstance(m, dict) else m[0]
        mcid = m.get("country_id") if isinstance(m, dict) else None
        if mcid:
            from database.connection import get_db_conn
            conn = get_db_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM countries WHERE id = ?", (mcid,))
            row = cursor.fetchone()
            if row:
                items_data.append({"country_id": row[0], "name": row[1], "user_id": muid})

    items, total_pages = paginate_list(items_data, page, per_page=6)
    buttons = [
        btn(f"🏳️ {c['name']}", "adv_war_send_targeted_support",
            data={"battle_id": battle["id"], "target_cid": c["country_id"], "side": side},
            owner=(user_id, chat_id), color="su")
        for c in items
    ]

    nav = []
    if page > 0:
        nav.append(btn("◀️", "adv_war_req_support_specific", data={"page": page-1}, owner=(user_id, chat_id)))
    if page < total_pages - 1:
        nav.append(btn("▶️", "adv_war_req_support_specific", data={"page": page+1}, owner=(user_id, chat_id)))
    nav.append(btn("🔙 رجوع", "adv_war_support_menu", data={}, owner=(user_id, chat_id)))

    layout = grid(len(items), 2) + [len(nav)]
    edit_ui(call, text=f"🎯 اختر دولة لطلب الدعم منها (معركة #{battle['id']}):",
            buttons=buttons + nav, layout=layout)


@register_action("adv_war_send_targeted_support")
def send_targeted_support(call, data):
    user_id = call.from_user.id
    battle_id = int(data["battle_id"])
    target_cid = int(data["target_cid"])
    side = data.get("side", "defender")

    ok, msg = send_support_request_targeted(battle_id, user_id, target_cid, side)
    bot.answer_callback_query(call.id, msg, show_alert=True)


@register_action("adv_war_view_requests")
def view_pending_requests(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    requests = get_my_pending_support_requests(user_id)
    if not requests:
        edit_ui(call,
                text="📥 <b>طلبات الدعم</b>\n\nلا توجد طلبات معلقة.",
                buttons=[btn("🔙 رجوع", "adv_war_support_menu", data={}, owner=(user_id, chat_id))],
                layout=[1])
        return

    text = "📥 <b>طلبات الدعم المعلقة</b>\n\n"
    buttons = []
    for req in requests[:5]:
        battle = get_battle_by_id(req["battle_id"])
        if not battle or battle["status"] == "finished":
            continue
        side_ar = "المهاجم" if req["side"] == "attacker" else "المدافع"
        requester = req.get("requester_name") or f"دولة #{req['requesting_country_id']}"
        text += f"⚔️ معركة #{req['battle_id']} | {requester} | {side_ar}\n"
        buttons.append(btn(f"🔥 أساعد — {requester}", "support_accept",
                           data={"req_id": req["id"], "battle_id": req["battle_id"]},
                           owner=(user_id, chat_id), color="su"))
        buttons.append(btn("❌ رفض", "support_reject",
                           data={"req_id": req["id"]},
                           owner=(user_id, chat_id), color="d"))

    buttons.append(btn("🔙 رجوع", "adv_war_support_menu", data={}, owner=(user_id, chat_id)))
    layout = [2] * (len(buttons) // 2) + [1]
    edit_ui(call, text=text, buttons=buttons, layout=layout)


@register_action("war_request_support_now")
def request_support_now(call, data):
    user_id = call.from_user.id
    battle_id = int(data["battle_id"])
    side = data.get("side", "defender")
    ok, msg = send_support_request_all(battle_id, user_id, side)
    bot.answer_callback_query(call.id, msg, show_alert=True)
    try:
        bot.edit_message_text(f"📣 {msg}", call.message.chat.id, call.message.message_id, parse_mode="HTML")
    except Exception:
        pass


# ══════════════════════════════════════════
# 🕵️ الجواسيس
# ══════════════════════════════════════════

@register_action("adv_war_spy")
def show_spy_menu(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    page = int(data.get("page", 0))

    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!")
        return
    country = dict(country)
    ensure_spy_units(country["id"])
    spy_data = get_spy_units(country["id"])

    from database.db_queries.countries_queries import get_all_countries
    all_countries = [dict(c) for c in get_all_countries() if c["id"] != country["id"]]
    items, total_pages = paginate_list(all_countries, page, per_page=6)

    from database.db_queries.advanced_war_queries import get_visibility
    buttons = []
    for c in items:
        vis = get_visibility(c["id"])
        vis_icon = "🌑" if vis and vis["visibility_mode"] == "hidden" else "🏳️"
        buttons.append(btn(f"{vis_icon} {c['name']}", "adv_war_do_spy",
                           data={"target_id": c["id"]}, owner=(user_id, chat_id)))

    try:
        from core.admin import get_const_int
        spy_cost = get_const_int("spy_cost", 150)
        spy_cd   = get_const_int("spy_cooldown_sec", 120)
    except Exception:
        spy_cost, spy_cd = 150, 120

    nav = []
    if page > 0:
        nav.append(btn("◀️", "adv_war_spy", data={"page": page-1}, owner=(user_id, chat_id)))
    if page < total_pages - 1:
        nav.append(btn("▶️", "adv_war_spy", data={"page": page+1}, owner=(user_id, chat_id)))
    nav.append(_back_btn(user_id, chat_id))

    layout = grid(len(items), 2) + [len(nav)]
    edit_ui(call,
            text=(f"🕵️ <b>نظام الجواسيس</b>\n\n"
                  f"مستوى جواسيسك: {spy_data['spy_level']}\n"
                  f"مستوى الدفاع: {spy_data['defense_level']}\n"
                  f"مستوى التمويه: {spy_data['camouflage_level']}\n\n"
                  f"💸 تكلفة العملية: {spy_cost} {CURRENCY_ARABIC_NAME}\n"
                  f"⏱️ كولداون: {spy_cd // 60} دقيقة لكل هدف\n\n"
                  f"🌑 = مخفية | 🏳️ = ظاهرة\n\nاختر دولة للتجسس:"),
            buttons=buttons + nav, layout=layout)


@register_action("adv_war_do_spy")
def execute_spy(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    target_id = int(data["target_id"])
    result_type, info = send_spies(user_id, target_id)
    icons = {"success": "🎯", "partial": "⚠️", "failed": "❌", "fake": "💀", "detected": "🚨"}
    discovered_note = "\n\n✅ تمت إضافة هذه الدولة لقائمة أهدافك!" if result_type in ("success", "partial") else ""
    edit_ui(call,
            text=f"{icons.get(result_type, '❓')} <b>نتيجة التجسس</b>\n\n{info}{discovered_note}",
            buttons=[btn("🔙 رجوع", "adv_war_spy", data={"page": 0}, owner=(user_id, chat_id))],
            layout=[1])


# ══════════════════════════════════════════
# 🃏 متجر البطاقات
# ══════════════════════════════════════════

@register_action("adv_war_cards_shop")
def show_cards_shop(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    page = int(data.get("page", 0))
    all_cards = get_all_cards()
    items, total_pages = paginate_list(all_cards, page, per_page=5)
    balance = get_user_balance(user_id)
    text = f"🃏 <b>متجر البطاقات</b>\n💰 رصيدك: {balance:.0f} {CURRENCY_ARABIC_NAME}\n\n"
    for c in items:
        text += f"{c['emoji']} <b>{c['name_ar']}</b>\n   📝 {c['description_ar']}\n   💵 {c['price']:.0f} {CURRENCY_ARABIC_NAME}\n\n"
    buttons = [btn(f"{c['emoji']} شراء {c['name_ar']}", "adv_war_buy_card",
                   data={"card_id": c["id"]}, owner=(user_id, chat_id), color="su") for c in items]
    nav = []
    if page > 0:
        nav.append(btn("◀️", "adv_war_cards_shop", data={"page": page-1}, owner=(user_id, chat_id)))
    if page < total_pages - 1:
        nav.append(btn("▶️", "adv_war_cards_shop", data={"page": page+1}, owner=(user_id, chat_id)))
    nav.append(_back_btn(user_id, chat_id))
    edit_ui(call, text=text, buttons=buttons + nav, layout=[1]*len(items) + [len(nav)])


@register_action("adv_war_buy_card")
def buy_card(call, data):
    user_id = call.from_user.id
    card_id = int(data["card_id"])
    card = get_card_by_id(card_id)
    if not card:
        bot.answer_callback_query(call.id, "❌ البطاقة غير موجودة!", show_alert=True)
        return
    if get_user_balance(user_id) < card["price"]:
        bot.answer_callback_query(call.id, f"❌ رصيدك غير كافٍ! تحتاج {card['price']:.0f} {CURRENCY_ARABIC_NAME}", show_alert=True)
        return
    deduct_user_balance(user_id, card["price"])
    add_user_card(user_id, card_id)
    bot.answer_callback_query(call.id, f"✅ اشتريت {card['name_ar']} {card['emoji']}", show_alert=True)


# ══════════════════════════════════════════
# 🎒 بطاقاتي
# ══════════════════════════════════════════

@register_action("adv_war_my_cards")
def show_my_cards(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    page = int(data.get("page", 0))
    cards = get_user_cards(user_id)
    if not cards:
        edit_ui(call, text="🎒 <b>بطاقاتي</b>\n\nليس لديك أي بطاقات.",
                buttons=[btn("🃏 المتجر", "adv_war_cards_shop", data={"page": 0}, owner=(user_id, chat_id)),
                         _back_btn(user_id, chat_id)], layout=[2])
        return
    items, total_pages = paginate_list(cards, page, per_page=5)
    text = f"🎒 <b>بطاقاتي</b> (صفحة {page+1}/{total_pages})\n\n"
    for c in items:
        text += f"{c['emoji']} <b>{c['name_ar']}</b> × {c['quantity']}\n   {c['description_ar']}\n\n"
    nav = []
    if page > 0:
        nav.append(btn("◀️", "adv_war_my_cards", data={"page": page-1}, owner=(user_id, chat_id)))
    if page < total_pages - 1:
        nav.append(btn("▶️", "adv_war_my_cards", data={"page": page+1}, owner=(user_id, chat_id)))
    nav.append(_back_btn(user_id, chat_id))
    edit_ui(call, text=text, buttons=nav, layout=[len(nav)])


# ══════════════════════════════════════════
# 📊 سجل / سمعة / معارك نشطة
# ══════════════════════════════════════════

@register_action("adv_war_history")
def show_battle_history(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!")
        return
    country = dict(country)
    history = get_battle_history_for_country(country["id"], limit=10)
    if not history:
        edit_ui(call, text="📊 <b>سجل المعارك</b>\n\nلا توجد معارك سابقة.",
                buttons=[_back_btn(user_id, chat_id)], layout=[1])
        return
    text = f"📊 <b>سجل المعارك</b> — {country['name']}\n\n"
    for b in history:
        won = b["winner_country_id"] == country["id"]
        icon = "🏆" if won else "💀"
        role = "مهاجم" if b["attacker_country_id"] == country["id"] else "مدافع"
        type_ar = {"normal": "عادي", "sudden": "مباغت", "fake": "وهمي", "building_raid": "غارة"}.get(b["battle_type"], b["battle_type"])
        text += f"{icon} #{b['id']} | {role} | {type_ar} | 💰 {b['loot']:.0f}\n"
    edit_ui(call, text=text, buttons=[_back_btn(user_id, chat_id)], layout=[1])


@register_action("adv_war_reputation")
def show_reputation(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    ensure_reputation(user_id)
    rep = get_reputation(user_id)
    if not rep:
        bot.answer_callback_query(call.id, "❌ خطأ في جلب السمعة")
        return
    edit_ui(call,
            text=(f"🏆 <b>سمعتك</b>\n\n"
                  f"اللقب: <b>{rep['reputation_title']}</b>\n\n"
                  f"📊 الإحصائيات:\n"
                  f"  🤝 معارك ساعدت فيها: {rep['battles_helped']}\n"
                  f"  😶 معارك تجاهلتها: {rep['battles_ignored']}\n"
                  f"  🐍 خيانات: {rep['betrayals']}\n"
                  f"  💯 نقاط الولاء: {rep['loyalty_score']}/100"),
            buttons=[_back_btn(user_id, chat_id)], layout=[1])


@register_action("adv_war_active")
def show_active_battles(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!")
        return
    country = dict(country)
    active = get_active_battles_for_country(country["id"])
    if not active:
        edit_ui(call, text="🔍 <b>المعارك النشطة</b>\n\nلا توجد معارك نشطة.",
                buttons=[_back_btn(user_id, chat_id)], layout=[1])
        return
    now = int(_time.time())
    text = "🔍 <b>المعارك النشطة</b>\n\n"
    buttons = []
    for b in active:
        status_ar = "🚶 في الطريق" if b["status"] == "traveling" else "⚔️ في القتال"
        role = "مهاجم" if b["attacker_country_id"] == country["id"] else "مدافع"
        remaining = max(0, b["travel_end_time"] - now) if b["status"] == "traveling" else max(0, (b.get("battle_end_time") or now) - now)
        text += f"⚔️ معركة #{b['id']} | {role}\n   {status_ar} | متبقي: {remaining // 60} دقيقة\n\n"
        buttons.append(btn(f"🃏 بطاقة للمعركة #{b['id']}", "adv_war_use_card_menu",
                           data={"battle_id": b["id"]}, owner=(user_id, chat_id)))
        if b["status"] == "in_battle":
            buttons.append(btn(f"⚡ أفعال المعركة #{b['id']}", "adv_war_live_actions",
                               data={"battle_id": b["id"]}, owner=(user_id, chat_id), color="d"))
    buttons.append(_back_btn(user_id, chat_id))
    edit_ui(call, text=text, buttons=buttons, layout=[1]*len(buttons))


@register_action("adv_war_use_card_menu")
def use_card_menu(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    battle_id = int(data["battle_id"])
    cards = get_user_cards(user_id)
    if not cards:
        bot.answer_callback_query(call.id, "❌ ليس لديك بطاقات!", show_alert=True)
        return
    buttons = [btn(f"{c['emoji']} {c['name_ar']} ×{c['quantity']}", "adv_war_use_card",
                   data={"battle_id": battle_id, "card_name": c["name"]}, owner=(user_id, chat_id))
               for c in cards]
    buttons.append(btn("🔙 رجوع", "adv_war_active", data={}, owner=(user_id, chat_id)))
    edit_ui(call, text=f"🃏 اختر بطاقة للمعركة #{battle_id}:",
            buttons=buttons, layout=[1]*len(buttons))


@register_action("adv_war_use_card")
def use_card_in_battle(call, data):
    user_id = call.from_user.id
    ok, msg = apply_card_to_battle(user_id, data["card_name"], int(data["battle_id"]))
    bot.answer_callback_query(call.id, msg, show_alert=True)


# ══════════════════════════════════════════
# 🤝 ردود الدعم
# ══════════════════════════════════════════

@register_action("support_accept")
def on_support_accept(call, data):
    user_id = call.from_user.id
    ok, msg = handle_support_response(user_id, int(data["req_id"]), accepted=True)
    bot.answer_callback_query(call.id, msg, show_alert=True)
    if ok:
        try:
            bot.edit_message_text("✅ انضممت للمعركة كداعم!", call.message.chat.id, call.message.message_id, parse_mode="HTML")
        except Exception:
            pass


@register_action("support_reject")
def on_support_reject(call, data):
    handle_support_response(call.from_user.id, int(data["req_id"]), accepted=False)
    bot.answer_callback_query(call.id, "تم تسجيل رفضك.")
    try:
        bot.edit_message_text("❌ رفضت طلب الدعم.", call.message.chat.id, call.message.message_id)
    except Exception:
        pass


# ══════════════════════════════════════════
# 📝 أوامر نصية
# ══════════════════════════════════════════

def handle_war_text_commands(message):
    text = message.text.strip()
    normalized = text.lower()

    if normalized in ["عرش الحرب", "الحرب", "حرب"]:
        open_advanced_war_menu(message)
        return True

    if normalized in ["طلب دعم", "طلبات الدعم"]:
        _handle_support_text(message)
        return True

    if normalized in ["جيش مدينتي", "قوات مدينتي", "قواتي", "جيشي"]:
        _handle_forces_command(message)
        return True

    if normalized in ["إخفاء دولتي", "اخفاء دولتي"]:
        ok, msg = set_country_visibility(message.from_user.id, "hidden")
        bot.reply_to(message, msg, parse_mode="HTML")
        return True

    if normalized in ["إظهار دولتي", "اظهار دولتي"]:
        ok, msg = set_country_visibility(message.from_user.id, "public")
        bot.reply_to(message, msg, parse_mode="HTML")
        return True

    if normalized in ["مستشفى", "المستشفى", "إصلاح", "الإصلاح"]:
        open_hospital_menu(message)
        return True

    if normalized.startswith("كود "):
        _handle_code_input(message, text)
        return True

    from utils.pagination.router import get_state, clear_state
    state = get_state(message.from_user.id, message.chat.id)
    if state.get("state") == "awaiting_attack_code":
        _process_code_state(message, text.strip())
        clear_state(message.from_user.id, message.chat.id)
        return True

    return False


def _handle_support_text(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    requests = get_my_pending_support_requests(user_id)
    if not requests:
        bot.reply_to(message, "📭 لا توجد طلبات دعم معلقة.")
        return
    for req in requests[:3]:
        battle = get_battle_by_id(req["battle_id"])
        if not battle or battle["status"] == "finished":
            continue
        side_ar = "المهاجم" if req["side"] == "attacker" else "المدافع"
        requester = req.get("requester_name") or f"دولة #{req['requesting_country_id']}"
        send_ui(chat_id,
                text=f"⚔️ <b>طلب دعم من {requester}</b>\n\nهل تريد دعمه كـ {side_ar}؟",
                buttons=[
                    btn("🔥 أساعد", "support_accept",
                        data={"req_id": req["id"], "battle_id": req["battle_id"]},
                        owner=(user_id, chat_id), color="su"),
                    btn("❌ لا", "support_reject",
                        data={"req_id": req["id"]},
                        owner=(user_id, chat_id), color="d"),
                ], layout=[2], owner_id=user_id)


def _handle_code_input(message, text):
    """معالجة: كود 12345 [country_id اختياري]"""
    parts = text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ الصيغة: كود [الكود] أو كود [الكود] [رقم الدولة]")
        return
    code = parts[1]
    # إذا أُعطي country_id
    if len(parts) >= 3 and parts[2].isdigit():
        target_cid = int(parts[2])
        ok, msg = verify_hidden_attack(message.from_user.id, target_cid, code)
        bot.reply_to(message, msg)
    else:
        # بحث في كل الدول المخفية
        from database.db_queries.countries_queries import get_all_countries
        from database.db_queries.advanced_war_queries import get_visibility
        country = get_country_by_owner(message.from_user.id)
        if not country:
            bot.reply_to(message, "❌ لا تملك دولة!")
            return
        my_cid = dict(country)["id"]
        found = False
        for c in get_all_countries():
            if c["id"] == my_cid:
                continue
            vis = get_visibility(c["id"])
            if vis and vis["visibility_mode"] == "hidden" and vis["daily_attack_code"] == code:
                add_discovered_country(my_cid, c["id"])
                bot.reply_to(message, f"✅ الكود صحيح! اكتشفت دولة مخفية.\nيمكنك الآن مهاجمتها من قائمة الأهداف.")
                found = True
                break
        if not found:
            bot.reply_to(message, "❌ الكود خاطئ أو لا توجد دولة مخفية بهذا الكود.")


def _process_code_state(message, code):
    """معالجة الكود المُدخل بعد الضغط على زر 'إدخال كود'"""
    _handle_code_input(message, f"كود {code}")


# ══════════════════════════════════════════
# ⚡ أفعال المعركة الحية
# ══════════════════════════════════════════

@register_action("adv_war_live_actions")
def show_live_actions(call, data):
    """قائمة الأفعال المتاحة أثناء المعركة"""
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    battle_id = int(data["battle_id"])

    from modules.war.live_battle_engine import (
        get_live_battle_state, get_active_effects_for_display,
        check_action_cooldown
    )

    battle = get_battle_by_id(battle_id)
    if not battle or battle["status"] != "in_battle":
        bot.answer_callback_query(call.id, "❌ المعركة لم تبدأ بعد أو انتهت.", show_alert=True)
        return

    state = get_live_battle_state(battle_id)
    effects = get_active_effects_for_display(battle_id)

    now = int(_time.time())
    remaining = max(0, (battle.get("battle_end_time") or now) - now)

    atk_p = state["atk_power"] if state else 0
    def_p = state["def_power"] if state else 0

    # شريط القوة المرئي
    total = max(1, atk_p + def_p)
    atk_pct = int((atk_p / total) * 10)
    def_pct = 10 - atk_pct
    bar = "🔴" * atk_pct + "🔵" * def_pct

    effects_text = ""
    if effects:
        effects_text = "\n\n✨ <b>تأثيرات نشطة:</b>\n"
        for ef in effects[:3]:
            rem_ef = max(0, ef["expires_at"] - now)
            effects_text += f"  • {ef['effect_type']} ({rem_ef}ث)\n"

    text = (
        f"⚔️ <b>المعركة الحية #{battle_id}</b>\n"
        f"⏱️ متبقي: {remaining // 60}د {remaining % 60}ث\n\n"
        f"📊 <b>القوى:</b>\n"
        f"  ⚔️ مهاجم: {atk_p:.0f}\n"
        f"  🛡 مدافع: {def_p:.0f}\n"
        f"  {bar}"
        f"{effects_text}\n\n"
        f"اختر فعلاً:"
    )

    # فحص الكولداون
    can_atk, rem_atk = check_action_cooldown(battle_id, user_id, "attack_boost", 30)
    can_def, rem_def = check_action_cooldown(battle_id, user_id, "defense_boost", 30)

    atk_label = "تعزيز الهجوم ⚔️" if can_atk else f"تعزيز الهجوم ({rem_atk}ث)"
    def_label = "تعزيز الدفاع 🛡" if can_def else f"تعزيز الدفاع ({rem_def}ث)"

    buttons = [
        btn(atk_label, "adv_war_action_boost",
            data={"battle_id": battle_id, "action": "attack_boost"},
            owner=(user_id, chat_id), color="d" if can_atk else "p"),
        btn(def_label, "adv_war_action_boost",
            data={"battle_id": battle_id, "action": "defense_boost"},
            owner=(user_id, chat_id), color="su" if can_def else "p"),
        btn("🃏 استخدام بطاقة", "adv_war_use_card_menu",
            data={"battle_id": battle_id}, owner=(user_id, chat_id)),
        btn("🔄 تحديث", "adv_war_live_actions",
            data={"battle_id": battle_id}, owner=(user_id, chat_id)),
        btn("🏃 انسحاب", "adv_war_retreat_confirm",
            data={"battle_id": battle_id}, owner=(user_id, chat_id), color="d"),
        btn("🔙 رجوع", "adv_war_active", data={}, owner=(user_id, chat_id)),
    ]
    edit_ui(call, text=text, buttons=buttons, layout=[2, 2, 2])


@register_action("adv_war_action_boost")
def do_battle_action(call, data):
    """تنفيذ تعزيز هجوم أو دفاع"""
    user_id = call.from_user.id
    battle_id = int(data["battle_id"])
    action = data.get("action", "attack_boost")

    from modules.war.live_battle_engine import (
        add_battle_effect, check_action_cooldown,
        set_action_cooldown, _log_event
    )

    battle = get_battle_by_id(battle_id)
    if not battle or battle["status"] != "in_battle":
        bot.answer_callback_query(call.id, "❌ المعركة غير نشطة.", show_alert=True)
        return

    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!", show_alert=True)
        return
    country = dict(country)
    cid = country["id"]

    # التحقق من أن المستخدم طرف في المعركة
    if cid not in (battle["attacker_country_id"], battle["defender_country_id"]):
        bot.answer_callback_query(call.id, "❌ لست طرفاً في هذه المعركة!", show_alert=True)
        return

    cooldown = 30
    can_use, remaining = check_action_cooldown(battle_id, user_id, action, cooldown)
    if not can_use:
        bot.answer_callback_query(call.id, f"⏳ انتظر {remaining} ثانية.", show_alert=True)
        return

    ACTIONS = {
        "attack_boost":  ("attack_boost",  0.10, 20, "تعزيز الهجوم +10%"),
        "defense_boost": ("defense_boost", 0.15, 20, "تعزيز الدفاع +15%"),
    }

    if action not in ACTIONS:
        bot.answer_callback_query(call.id, "❌ فعل غير معروف.", show_alert=True)
        return

    etype, evalue, duration, label = ACTIONS[action]
    add_battle_effect(battle_id, cid, user_id, etype, evalue, duration, source="action")
    set_action_cooldown(battle_id, user_id, action)
    side = "attacker" if battle["attacker_country_id"] == cid else "defender"
    _log_event(battle_id, "action", f"{label} من {side}", 0, 0)

    bot.answer_callback_query(call.id, f"✅ {label} لـ {duration} ثانية!", show_alert=False)
    # تحديث الواجهة
    show_live_actions(call, {"battle_id": battle_id})


# ══════════════════════════════════════════
# 🏃 الانسحاب
# ══════════════════════════════════════════

@register_action("adv_war_retreat_confirm")
def retreat_confirm(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    battle_id = int(data["battle_id"])
    edit_ui(call,
            text=(f"🏃 <b>تأكيد الانسحاب من المعركة #{battle_id}</b>\n\n"
                  f"⚠️ سيتم تخفيض خسائرك 50%\n"
                  f"📉 ستخسر نقاط سمعة\n"
                  f"🏆 سيفوز العدو تلقائياً\n\n"
                  f"هل أنت متأكد؟"),
            buttons=[
                btn("✅ نعم، انسحب", "adv_war_do_retreat",
                    data={"battle_id": battle_id}, owner=(user_id, chat_id), color="d"),
                btn("🔙 إلغاء", "adv_war_live_actions",
                    data={"battle_id": battle_id}, owner=(user_id, chat_id)),
            ], layout=[2])


@register_action("adv_war_do_retreat")
def do_retreat(call, data):
    user_id = call.from_user.id
    battle_id = int(data["battle_id"])

    from modules.war.war_economy import execute_retreat
    ok, msg = execute_retreat(user_id, battle_id)
    bot.answer_callback_query(call.id, "تم الانسحاب" if ok else "❌ فشل الانسحاب", show_alert=True)
    try:
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode="HTML")
    except Exception:
        pass


# ══════════════════════════════════════════
# 🏥 المستشفى والإصلاح
# ══════════════════════════════════════════

def open_hospital_menu(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    country = get_country_by_owner(user_id)
    if not country:
        bot.reply_to(message, "❌ لا تملك دولة!")
        return
    country = dict(country)

    from modules.war.war_economy import get_injured_troops, get_damaged_equipment, heal_ready_troops
    healed = heal_ready_troops(country["id"])
    injured = get_injured_troops(country["id"])
    damaged = get_damaged_equipment(country["id"])

    text = f"🏥 <b>المستشفى والإصلاح</b>\n"
    if healed > 0:
        text += f"✅ تم شفاء {healed} جندي!\n"
    text += f"{get_lines()}\n\n"

    if injured:
        text += f"🏥 <b>الجنود المصابون ({len(injured)} نوع):</b>\n"
        now = int(_time.time())
        for inj in injured[:5]:
            rem = max(0, inj["heal_time"] - now)
            text += f"  {inj['emoji']} {inj['name_ar']}: {inj['quantity']} | يُشفى خلال {rem // 60} دقيقة\n"
    else:
        text += "✅ لا يوجد جنود مصابون\n"

    text += "\n"
    if damaged:
        total_repair = sum(d["repair_cost"] for d in damaged)
        text += f"🔧 <b>المعدات التالفة ({len(damaged)} نوع):</b>\n"
        for d in damaged[:5]:
            text += f"  {d['emoji']} {d['name_ar']}: {d['quantity']} | تكلفة: {d['repair_cost']:.0f}\n"
        text += f"\n💰 إجمالي الإصلاح: {total_repair:.0f} {CURRENCY_ARABIC_NAME}"
    else:
        text += "✅ لا توجد معدات تالفة"

    buttons = []
    if damaged:
        buttons.append(btn("🔧 إصلاح كل المعدات", "adv_war_repair_all",
                           data={}, owner=(user_id, chat_id), color="su"))
    buttons.append(_back_btn(user_id, chat_id))

    send_ui(chat_id, text=text, buttons=buttons,
            layout=[1] * len(buttons), owner_id=user_id)


@register_action("adv_war_repair_all")
def repair_all_equipment(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!")
        return
    country = dict(country)

    from modules.war.war_economy import repair_equipment
    ok, msg, cost = repair_equipment(user_id, country["id"])
    bot.answer_callback_query(call.id, msg, show_alert=True)


# ══════════════════════════════════════════
# 📊 حالة الدولة (تعافٍ + مصابون)
# ══════════════════════════════════════════

@register_action("adv_war_country_status")
def show_country_status(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!")
        return
    country = dict(country)

    from modules.war.war_economy import (
        is_country_in_recovery, get_injured_troops, get_damaged_equipment
    )
    from modules.war.power_calculator import get_country_power_breakdown

    in_rec, rec_rem = is_country_in_recovery(country["id"])
    injured = get_injured_troops(country["id"])
    damaged = get_damaged_equipment(country["id"])
    breakdown = get_country_power_breakdown(country["id"])

    text = (
        f"🏳️ <b>حالة دولة {country['name']}</b>\n"
        f"{get_lines()}\n\n"
        f"💪 القوة الكاملة: {breakdown['total']:.0f}\n"
        f"🪖 الجنود: {breakdown['troop_count']}\n"
        f"🛡 المعدات: {breakdown['equipment_count']}\n"
        f"🏰 مضاعف التحالف: ×{breakdown['alliance_multiplier']:.2f}\n\n"
    )

    if in_rec:
        text += f"🔄 <b>فترة التعافي:</b> {rec_rem // 60} دقيقة متبقية\n\n"
    else:
        text += "✅ الدولة جاهزة للقتال\n\n"

    if injured:
        total_inj = sum(i["quantity"] for i in injured)
        text += f"🏥 مصابون: {total_inj} جندي\n"
    if damaged:
        total_dmg = sum(d["quantity"] for d in damaged)
        text += f"🔧 معدات تالفة: {total_dmg} وحدة\n"

    edit_ui(call, text=text,
            buttons=[_back_btn(user_id, chat_id)], layout=[1])


# ══════════════════════════════════════════
# 🔄 تحديث القائمة الرئيسية لتشمل الأزرار الجديدة
# ══════════════════════════════════════════

def _war_main_buttons(user_id, chat_id):
    from database.db_queries.alliances_queries import get_alliance_by_user
    alliance = get_alliance_by_user(user_id)
    buttons = []
    # متجر التحالف — أول زر إذا كان في تحالف
    if alliance:
        alliance = dict(alliance)
        buttons.append(btn("🏰 متجر التحالف", "alliance_buy_upgrade",
                           data={"aid": alliance["id"], "page": 0},
                           owner=(user_id, chat_id), color="su"))
    buttons += [
        btn("⚔️ شن هجوم",        "adv_war_attack",         data={"page": 0}, owner=(user_id, chat_id), color="d"),
        btn("🪖 متجر القوات",     "adv_war_force_shop",     data={"tab": "troops", "page": 0}, owner=(user_id, chat_id)),
        btn("🕵️ إرسال جواسيس",   "adv_war_spy",            data={"page": 0}, owner=(user_id, chat_id)),
        btn("🃏 متجر البطاقات",   "adv_war_cards_shop",     data={"page": 0}, owner=(user_id, chat_id)),
        btn("🎒 بطاقاتي",         "adv_war_my_cards",       data={"page": 0}, owner=(user_id, chat_id)),
        btn("📊 سجل المعارك",     "adv_war_history",        data={},          owner=(user_id, chat_id)),
        btn("📜 سجل الحروب",      "adv_war_war_log",        data={"page": 0}, owner=(user_id, chat_id)),
        btn("🏆 سمعتي",           "adv_war_reputation",     data={},          owner=(user_id, chat_id), color="su"),
        btn("🔍 معاركي النشطة",   "adv_war_active",         data={},          owner=(user_id, chat_id), color="su"),
        btn("📣 طلبات الدعم",     "adv_war_support_menu",   data={},          owner=(user_id, chat_id), color="su"),
        btn("🏥 المستشفى",        "adv_war_country_status", data={},          owner=(user_id, chat_id)),
    ]
    return buttons


# ══════════════════════════════════════════
# 📝 تحديث الأوامر النصية
# ══════════════════════════════════════════

def handle_war_text_commands(message):
    text = message.text.strip()
    normalized = text.lower()

    if normalized in ["عرش الحرب", "الحرب", "حرب"]:
        open_advanced_war_menu(message)
        return True

    if normalized in ["طلب دعم", "طلبات الدعم"]:
        _handle_support_text(message)
        return True

    if normalized in ["إخفاء دولتي", "اخفاء دولتي"]:
        ok, msg = set_country_visibility(message.from_user.id, "hidden")
        bot.reply_to(message, msg, parse_mode="HTML")
        return True

    if normalized in ["إظهار دولتي", "اظهار دولتي"]:
        ok, msg = set_country_visibility(message.from_user.id, "public")
        bot.reply_to(message, msg, parse_mode="HTML")
        return True

    if normalized in ["مستشفى", "المستشفى", "إصلاح", "الإصلاح"]:
        open_hospital_menu(message)
        return True

    if normalized.startswith("كود "):
        _handle_code_input(message, text)
        return True

    from utils.pagination.router import get_state, clear_state
    state = get_state(message.from_user.id, message.chat.id)
    if state.get("state") == "awaiting_attack_code":
        _process_code_state(message, text.strip())
        clear_state(message.from_user.id, message.chat.id)
        return True

    return False


# ══════════════════════════════════════════
# 📜 سجل الحروب
# ══════════════════════════════════════════

@register_action("adv_war_war_log")
def show_war_log(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    page    = int(data.get("page", 0))

    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!")
        return
    country = dict(country)

    from modules.war.war_balance import get_battle_history, format_history_entry
    history = get_battle_history(country["id"], limit=50)

    if not history:
        edit_ui(call,
                text="📜 <b>سجل الحروب</b>\n\nلا توجد معارك مسجلة بعد.",
                buttons=[_back_btn(user_id, chat_id)], layout=[1])
        return

    items, total_pages = paginate_list(history, page, per_page=8)
    text = f"📜 <b>سجل الحروب</b> (صفحة {page+1}/{total_pages})\n{get_lines()}\n\n"
    for entry in items:
        text += format_history_entry(entry, country["id"]) + "\n\n"

    nav = []
    if page > 0:
        nav.append(btn("◀️", "adv_war_war_log", data={"page": page-1}, owner=(user_id, chat_id)))
    if page < total_pages - 1:
        nav.append(btn("▶️", "adv_war_war_log", data={"page": page+1}, owner=(user_id, chat_id)))
    nav.append(_back_btn(user_id, chat_id))

    edit_ui(call, text=text, buttons=nav, layout=[len(nav)])


# ══════════════════════════════════════════
# 📊 حالة الدولة المحدّثة (مع التعب + طابور الإصلاح)
# ══════════════════════════════════════════

@register_action("adv_war_country_status")
def show_country_status(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!")
        return
    country = dict(country)

    from modules.war.war_economy import (
        is_country_in_recovery, get_injured_troops, get_damaged_equipment
    )
    from modules.war.war_balance import (
        get_fatigue_display, get_repair_queue, complete_ready_repairs
    )
    from modules.war.power_calculator import get_country_power_breakdown

    # إكمال الإصلاحات الجاهزة تلقائياً
    complete_ready_repairs(country["id"])

    in_rec, rec_rem = is_country_in_recovery(country["id"])
    injured  = get_injured_troops(country["id"])
    damaged  = get_damaged_equipment(country["id"])
    repair_q = get_repair_queue(country["id"])
    breakdown = get_country_power_breakdown(country["id"])
    fatigue_text = get_fatigue_display(country["id"])

    text = (
        f"🏳️ <b>حالة دولة {country['name']}</b>\n"
        f"{get_lines()}\n\n"
        f"💪 القوة الكاملة: {breakdown['total']:.0f}\n"
        f"🪖 الجنود: {breakdown['troop_count']}\n"
        f"🛡 المعدات: {breakdown['equipment_count']}\n"
        f"🏰 مضاعف التحالف: ×{breakdown['alliance_multiplier']:.2f}\n"
        f"😴 التعب: {fatigue_text}\n\n"
    )

    if in_rec:
        text += f"🔄 <b>فترة التعافي:</b> {rec_rem // 60} دقيقة متبقية\n\n"
    else:
        text += "✅ الدولة جاهزة للقتال\n\n"

    if injured:
        total_inj = sum(i["quantity"] for i in injured)
        text += f"🏥 مصابون: {total_inj} جندي\n"
    if damaged:
        total_dmg = sum(d["quantity"] for d in damaged)
        text += f"🔧 معدات تالفة: {total_dmg} وحدة\n"
    if repair_q:
        total_cost = sum(r["repair_cost"] for r in repair_q)
        text += f"⚙️ طابور الإصلاح: {len(repair_q)} نوع | {total_cost:.0f} {CURRENCY_ARABIC_NAME}\n"

    buttons = []
    if damaged or repair_q:
        buttons.append(btn("🔧 إصلاح كل المعدات", "adv_war_repair_all",
                           data={}, owner=(user_id, chat_id), color="su"))
    buttons.append(_back_btn(user_id, chat_id))
    edit_ui(call, text=text, buttons=buttons, layout=[1]*len(buttons))


# ══════════════════════════════════════════
# 🪖 متجر القوات
# ══════════════════════════════════════════

@register_action("adv_war_force_shop")
def show_force_shop(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    tab  = data.get("tab", "troops")
    page = int(data.get("page", 0))

    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!")
        return
    country = dict(country)

    from modules.war.force_shop import get_available_troops, get_available_equipment
    from database.db_queries.bank_queries import get_user_balance

    balance = get_user_balance(user_id)

    if tab == "troops":
        items_all = get_available_troops()
        title = "🪖 متجر الجنود"
        buy_action = "adv_war_buy_troop"
        id_key = "troop_id"
    else:
        items_all = get_available_equipment()
        title = "🛡 متجر المعدات"
        buy_action = "adv_war_buy_equip"
        id_key = "eq_id"

    items, total_pages = paginate_list(items_all, page, per_page=5)

    text = f"{title}\n💰 رصيدك: {balance:.0f} {CURRENCY_ARABIC_NAME}\n{get_lines()}\n\n"
    buttons = []
    for item in items:
        emoji = item.get("emoji", "⚔️")
        name  = item.get("name_ar", item.get("name", ""))
        cost  = item.get("base_cost", 0)
        text += f"{emoji} <b>{name}</b> — {cost:.0f} {CURRENCY_ARABIC_NAME}/وحدة\n"
        buttons.append(btn(f"{emoji} شراء {name}", buy_action,
                           data={id_key: item["id"], "qty": 1},
                           owner=(user_id, chat_id), color="su"))

    # تبويب الجنود / المعدات
    tab_btns = [
        btn("🪖 الجنود",  "adv_war_force_shop", data={"tab": "troops", "page": 0},
            owner=(user_id, chat_id), color="d" if tab == "troops" else "p"),
        btn("🛡 المعدات", "adv_war_force_shop", data={"tab": "equip",  "page": 0},
            owner=(user_id, chat_id), color="d" if tab == "equip" else "p"),
    ]

    nav = []
    if page > 0:
        nav.append(btn("◀️", "adv_war_force_shop", data={"tab": tab, "page": page-1}, owner=(user_id, chat_id)))
    if page < total_pages - 1:
        nav.append(btn("▶️", "adv_war_force_shop", data={"tab": tab, "page": page+1}, owner=(user_id, chat_id)))
    nav.append(btn("🪖 قواتي", "adv_war_my_forces", data={}, owner=(user_id, chat_id)))
    nav.append(_back_btn(user_id, chat_id))

    layout = [1]*len(items) + [2] + ([len(nav)-2] if len(nav) > 2 else []) + [2]
    edit_ui(call, text=text, buttons=buttons + tab_btns + nav, layout=layout)


@register_action("adv_war_buy_troop")
def buy_troop(call, data):
    user_id = call.from_user.id
    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!", show_alert=True)
        return
    country = dict(country)

    from modules.war.force_shop import buy_troops
    ok, msg = buy_troops(user_id, country["id"], int(data["troop_id"]), int(data.get("qty", 1)))
    bot.answer_callback_query(call.id, msg, show_alert=True)


@register_action("adv_war_buy_equip")
def buy_equip(call, data):
    user_id = call.from_user.id
    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!", show_alert=True)
        return
    country = dict(country)

    from modules.war.force_shop import buy_equipment
    ok, msg = buy_equipment(user_id, country["id"], int(data["eq_id"]), int(data.get("qty", 1)))
    bot.answer_callback_query(call.id, msg, show_alert=True)


@register_action("adv_war_my_forces")
def show_my_forces(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!")
        return
    country = dict(country)

    from modules.war.force_shop import get_city_forces_display
    from modules.war.country_level import get_level_info
    from modules.war.war_balance import get_fatigue_display

    text = get_city_forces_display(country["id"])
    lvl  = get_level_info(country["id"])
    fat  = get_fatigue_display(country["id"])
    text += f"\n🎖 المستوى: {lvl['label']}\n😴 التعب: {fat}"

    edit_ui(call, text=text,
            buttons=[
                btn("🪖 متجر القوات", "adv_war_force_shop",
                    data={"tab": "troops", "page": 0}, owner=(user_id, chat_id)),
                _back_btn(user_id, chat_id),
            ], layout=[2])


# ══════════════════════════════════════════
# 📝 أوامر نصية إضافية
# ══════════════════════════════════════════

def _handle_forces_command(message):
    """يعرض قوات المدينة عبر أمر نصي"""
    user_id = message.from_user.id
    chat_id = message.chat.id

    country = get_country_by_owner(user_id)
    if not country:
        bot.reply_to(message, "❌ لا تملك دولة!")
        return

    country = dict(country)
    from modules.war.force_shop import get_city_forces_display
    from modules.war.country_level import get_level_info
    from modules.war.war_balance import get_fatigue_display
    from utils.pagination import send_ui as _send_ui

    text = get_city_forces_display(country["id"])
    lvl  = get_level_info(country["id"])
    fat  = get_fatigue_display(country["id"])
    text += f"\n🎖 المستوى: {lvl['label']}\n😴 التعب: {fat}"

    _send_ui(chat_id, text=text,
             buttons=[btn("🪖 متجر القوات", "adv_war_force_shop",
                          data={"tab": "troops", "page": 0},
                          owner=(user_id, chat_id))],
             layout=[1], owner_id=user_id)


# ══════════════════════════════════════════
# 🔍 الاستكشاف والرادار
# ══════════════════════════════════════════

@register_action("adv_war_explore")
def do_explore(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    from modules.war.spy_service import explore_targets
    ok, result = explore_targets(user_id)

    if not ok:
        bot.answer_callback_query(call.id, result, show_alert=True)
        return

    edit_ui(call,
            text=result["message"],
            buttons=[
                btn("⚔️ هجوم الآن", "adv_war_select_target",
                    data={"target_id": result["id"], "target_name": result["name"]},
                    owner=(user_id, chat_id), color="d"),
                _back_btn(user_id, chat_id),
            ], layout=[1, 1])


@register_action("adv_war_radar")
def show_radar(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    from modules.war.spy_service import get_radar_targets
    from modules.war.country_level import TIER_LABELS

    targets = get_radar_targets(user_id, limit=6)
    if not targets:
        edit_ui(call,
                text="📡 <b>الرادار</b>\n\nلا توجد أهداف في نطاق رادارك حالياً.\nطوّر جواسيسك لتوسيع النطاق.",
                buttons=[_back_btn(user_id, chat_id)], layout=[1])
        return

    text = "📡 <b>الرادار — أهداف قريبة</b>\n{get_lines()}\n\n"
    buttons = []
    for t in targets:
        tier_label = TIER_LABELS.get(t["tier"], "🟡")
        text += f"🏳️ <b>{t['name']}</b> {tier_label}\n"
        buttons.append(btn(f"🏳️ {t['name']}", "adv_war_select_target",
                           data={"target_id": t["id"], "target_name": t["name"]},
                           owner=(user_id, chat_id), color="d"))

    buttons.append(_back_btn(user_id, chat_id))
    edit_ui(call, text=text, buttons=buttons, layout=[1]*len(buttons))


# ══════════════════════════════════════════
# 🕵️ إدارة العملاء
# ══════════════════════════════════════════

@register_action("adv_war_agents")
def show_agents_menu(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!")
        return
    country = dict(country)

    from modules.war.spy_service import get_agents, AGENT_TYPES, _c

    agents = get_agents(country["id"])
    text   = "🕵️ <b>عملاء التجسس</b>\n{get_lines()}\n\n"

    if agents:
        for a in agents:
            atype = AGENT_TYPES.get(a["agent_type"], {})
            text += (
                f"{atype.get('name_ar', a['agent_type'])} "
                f"مستوى {a['level']} | XP: {a['experience']}\n"
            )
    else:
        text += "لا يوجد عملاء حالياً.\n\n"

    text += "\n💡 جنّد عملاء لتنفيذ مهام متخصصة:"

    buttons = [
        btn("🕵️ تجنيد كشاف",  "adv_war_recruit_agent",
            data={"type": "scout"},    owner=(user_id, chat_id), color="p"),
        btn("💣 تجنيد مخرب",   "adv_war_recruit_agent",
            data={"type": "saboteur"}, owner=(user_id, chat_id), color="d"),
        btn("☠️ تجنيد قاتل",   "adv_war_recruit_agent",
            data={"type": "assassin"}, owner=(user_id, chat_id), color="d"),
        _back_btn(user_id, chat_id),
    ]
    edit_ui(call, text=text, buttons=buttons, layout=[2, 1, 1])


@register_action("adv_war_recruit_agent")
def recruit_agent(call, data):
    user_id    = call.from_user.id
    agent_type = data.get("type", "scout")

    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!", show_alert=True)
        return
    country = dict(country)

    from modules.war.spy_service import recruit_agent as _recruit, AGENT_TYPES, _c
    ok, msg = _recruit(country["id"], user_id, agent_type)
    bot.answer_callback_query(call.id, msg, show_alert=True)


@register_action("adv_war_deploy_agent")
def deploy_agent(call, data):
    """تنفيذ مهمة عميل على هدف"""
    user_id    = call.from_user.id
    chat_id    = call.message.chat.id
    target_id  = int(data["target_id"])
    agent_type = data.get("agent_type", "scout")

    from modules.war.spy_service import execute_spy_mission
    result_type, msg, effects = execute_spy_mission(user_id, target_id, agent_type)

    icons = {"success": "🎯", "partial": "⚠️", "failed": "❌",
             "fake": "💀", "detected": "🚨"}
    icon = icons.get(result_type, "❓")

    extra = ""
    if effects.get("troops_killed"):
        extra = f"\n\n☠️ قتلى: {effects['troops_killed']} جندي"
    elif effects.get("sabotage_pct"):
        extra = f"\n\n💣 تأثير التخريب: -{int(effects['sabotage_pct']*100)}%"

    edit_ui(call,
            text=f"{icon} <b>نتيجة المهمة</b>\n\n{msg}{extra}",
            buttons=[
                btn("🔙 رجوع", "adv_war_spy", data={"page": 0}, owner=(user_id, chat_id))
            ], layout=[1])


# ══════════════════════════════════════════
# 💰 الدعم المالي للتحالف
# ══════════════════════════════════════════

@register_action("adv_war_resource_support")
def send_resource_support(call, data):
    """يرسل دعماً مالياً لحليف في معركة"""
    user_id   = call.from_user.id
    battle_id = int(data["battle_id"])
    side      = data.get("side", "defender")

    try:
        from core.admin import get_const_int
        amount = get_const_int("support_res_amount", 500)
    except Exception:
        amount = 500

    from database.db_queries.bank_queries import get_user_balance, deduct_user_balance
    balance = get_user_balance(user_id)
    if balance < amount:
        bot.answer_callback_query(call.id, f"❌ رصيدك غير كافٍ! تحتاج {amount} {CURRENCY_ARABIC_NAME}", show_alert=True)
        return

    deduct_user_balance(user_id, amount)

    # إضافة الموارد لعاصمة الطرف المدعوم
    from database.db_queries.advanced_war_queries import get_battle_by_id
    from database.db_queries.war_queries import update_city_resources
    from modules.war.live_battle_engine import _get_capital_city_id

    battle = get_battle_by_id(battle_id)
    if battle:
        target_cid = battle["defender_country_id"] if side == "defender" else battle["attacker_country_id"]
        cap = _get_capital_city_id(target_cid)
        if cap:
            update_city_resources(cap, amount)

    # تسجيل إحصائيات الدعم
    try:
        from modules.war.maintenance_service import record_alliance_support
        from database.db_queries.alliances_queries import get_alliance_by_user
        alliance = get_alliance_by_user(user_id)
        if alliance:
            record_alliance_support(alliance["id"], user_id, resource_sent=amount)
    except Exception:
        pass

    bot.answer_callback_query(call.id, f"💰 تم إرسال {amount} {CURRENCY_ARABIC_NAME} دعماً مالياً!", show_alert=True)


# ══════════════════════════════════════════
# 📊 إحصائيات دعم التحالف
# ══════════════════════════════════════════

@register_action("adv_war_support_stats")
def show_support_stats(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    from database.db_queries.alliances_queries import get_alliance_by_user
    from modules.war.maintenance_service import get_alliance_support_leaderboard

    alliance = get_alliance_by_user(user_id)
    if not alliance:
        bot.answer_callback_query(call.id, "❌ لست في أي تحالف!", show_alert=True)
        return
    alliance = dict(alliance)

    stats = get_alliance_support_leaderboard(alliance["id"])
    text  = f"🤝 <b>إحصائيات دعم تحالف {alliance['name']}</b>\n{get_lines()}\n\n"

    if not stats:
        text += "لا توجد إحصائيات بعد."
    else:
        for i, s in enumerate(stats[:10], 1):
            text += (
                f"{i}. <b>{s['name']}</b>\n"
                f"   ⚔️ معارك: {s['battles_supported']} | "
                f"💪 قوة: {s['total_power_contributed']:.0f} | "
                f"💰 موارد: {s['resource_sent']:.0f}\n\n"
            )

    edit_ui(call, text=text, buttons=[_back_btn(user_id, chat_id)], layout=[1])


# ══════════════════════════════════════════
# 🔄 تحديث القائمة الرئيسية لتشمل الأزرار الجديدة
# ══════════════════════════════════════════

def _war_main_buttons(user_id, chat_id):
    from database.db_queries.alliances_queries import get_alliance_by_user
    alliance = get_alliance_by_user(user_id)
    buttons  = []

    if alliance:
        alliance = dict(alliance)
        buttons.append(btn("🏰 متجر التحالف", "alliance_buy_upgrade",
                           data={"aid": alliance["id"], "page": 0},
                           owner=(user_id, chat_id), color="su"))

    buttons += [
        btn("⚔️ شن هجوم",        "adv_war_attack",         data={"page": 0}, owner=(user_id, chat_id), color="d"),
        btn("🔍 استكشاف",         "adv_war_explore",        data={},          owner=(user_id, chat_id), color="p"),
        btn("📡 الرادار",          "adv_war_radar",          data={},          owner=(user_id, chat_id), color="p"),
        btn("🕵️ عملاء التجسس",   "adv_war_agents",         data={},          owner=(user_id, chat_id)),
        btn("🪖 متجر القوات",     "adv_war_force_shop",     data={"tab": "troops", "page": 0}, owner=(user_id, chat_id)),
        btn("🃏 متجر البطاقات",   "adv_war_cards_shop",     data={"page": 0}, owner=(user_id, chat_id)),
        btn("🎒 بطاقاتي",         "adv_war_my_cards",       data={"page": 0}, owner=(user_id, chat_id)),
        btn("📊 سجل المعارك",     "adv_war_history",        data={},          owner=(user_id, chat_id)),
        btn("📜 سجل الحروب",      "adv_war_war_log",        data={"page": 0}, owner=(user_id, chat_id)),
        btn("🏆 سمعتي",           "adv_war_reputation",     data={},          owner=(user_id, chat_id), color="su"),
        btn("🔍 معاركي النشطة",   "adv_war_active",         data={},          owner=(user_id, chat_id), color="su"),
        btn("📣 طلبات الدعم",     "adv_war_support_menu",   data={},          owner=(user_id, chat_id), color="su"),
        btn("🤝 إحصائيات الدعم",  "adv_war_support_stats",  data={},          owner=(user_id, chat_id)),
        btn("🏥 المستشفى",        "adv_war_country_status", data={},          owner=(user_id, chat_id)),
    ]
    return buttons
