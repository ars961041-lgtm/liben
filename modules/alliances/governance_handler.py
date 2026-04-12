"""
معالج حوكمة التحالفات — واجهة المستخدم
Alliance Governance Handler — UI & Callbacks

يغطي: الخزينة، السمعة، الألقاب، الأدوار، الضرائب
"""
from core.bot import bot
from utils.pagination import btn, send_ui, edit_ui, register_action, paginate_list, grid
from database.db_queries.countries_queries import get_country_by_owner
from database.db_queries.alliances_queries import (
    get_alliance_by_user, get_alliance_by_id, get_alliance_member_count,
)
from database.db_queries.alliance_governance_queries import (
    get_treasury, deposit_treasury, withdraw_treasury, get_treasury_log,
    reward_member, get_alliance_reputation, update_alliance_reputation,
    get_alliance_titles, get_all_current_titles, get_top_alliances_by_reputation,
    has_permission, promote_member, demote_member, get_member_role,
    get_tax_config, set_tax_rate, get_alliance_full_stats,
    TITLE_DEFINITIONS,
)
from utils.helpers import get_lines
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME


def _back_gov(user_id, chat_id, aid):
    return btn("🔙 رجوع", "gov_main", data={"aid": aid}, owner=(user_id, chat_id))


def _role_ar(role):
    return {"leader": "👑 قائد", "officer": "⭐ ضابط", "member": "🪖 عضو"}.get(role, role)


# ══════════════════════════════════════════
# 🏠 القائمة الرئيسية للحوكمة
# ══════════════════════════════════════════

def open_governance_menu(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    alliance = get_alliance_by_user(user_id)
    if not alliance:
        from core.personality import send_with_delay
        send_with_delay(chat_id, "❌ لست في أي تحالف.", delay=0.3,
                        reply_to=message.message_id)
        return
    alliance = dict(alliance)
    _render_gov_main(chat_id, user_id, chat_id, alliance["id"], send_msg=message)


def _render_gov_main(chat_id, user_id, owner_chat_id, alliance_id,
                     send_msg=None, edit_call=None):
    alliance = get_alliance_by_id(alliance_id)
    if not alliance:
        return
    stats = get_alliance_full_stats(alliance_id)
    rep = stats["reputation"]
    treasury = stats["treasury"]
    titles = stats["titles"]
    role = get_member_role(alliance_id, user_id) or "member"

    title_line = " | ".join(f"{t['emoji']} {t['title_ar']}" for t in titles) if titles else "لا ألقاب"

    text = (
        f"🏛️ <b>حوكمة تحالف: {alliance['name']}</b>\n"
        f"{get_lines()}\n"
        f"💰 الخزينة: {treasury['balance']:.0f} {CURRENCY_ARABIC_NAME}\n"
        f"⭐ السمعة: {rep.get('score', 0):.0f} — {rep.get('title', '😶 غير معروف')}\n"
        f"🏆 الألقاب: {title_line}\n"
        f"👤 دورك: {_role_ar(role)}\n\n"
        f"اختر ما تريد:"
    )

    buttons = [
        btn("🏦 الخزينة",    "gov_treasury",    data={"aid": alliance_id},
            owner=(user_id, owner_chat_id), color="p"),
        btn("⭐ السمعة",     "gov_reputation",  data={"aid": alliance_id},
            owner=(user_id, owner_chat_id), color="p"),
        btn("🏆 الألقاب",   "gov_titles",      data={"aid": alliance_id},
            owner=(user_id, owner_chat_id), color="p"),
        btn("🧬 الأدوار",   "gov_roles",       data={"aid": alliance_id},
            owner=(user_id, owner_chat_id), color="p"),
    ]
    if has_permission(alliance_id, user_id, "set_tax"):
        buttons.append(btn("💸 الضرائب", "gov_tax",
                           data={"aid": alliance_id},
                           owner=(user_id, owner_chat_id), color="su"))

    layout = [2, 2, 1] if len(buttons) == 5 else [2, 2]

    if edit_call:
        edit_ui(edit_call, text=text, buttons=buttons, layout=layout)
    else:
        send_ui(chat_id, text=text, buttons=buttons, layout=layout,
                owner_id=user_id, reply_to=send_msg.message_id if send_msg else None)


@register_action("gov_main")
def gov_main_cb(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])
    bot.answer_callback_query(call.id)
    _render_gov_main(chat_id, user_id, chat_id, aid, edit_call=call)


# ══════════════════════════════════════════
# 🏦 الخزينة
# ══════════════════════════════════════════

@register_action("gov_treasury")
def show_treasury(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])

    treasury = get_treasury(aid)
    log = get_treasury_log(aid, limit=5)

    tx_ar = {
        "deposit": "⬆️ إيداع", "withdraw": "⬇️ سحب",
        "loot_share": "⚔️ غنائم", "upgrade_cost": "⬆️ ترقية",
        "war_fund": "🪖 تمويل حرب", "reward": "🎁 مكافأة",
        "tax": "💸 ضريبة",
    }

    log_text = ""
    for tx in log:
        sign = "+" if tx["amount"] > 0 else ""
        log_text += f"\n{tx_ar.get(tx['tx_type'], tx['tx_type'])}: {sign}{tx['amount']:.0f}"

    text = (
        f"🏦 <b>خزينة التحالف</b>\n{get_lines()}\n"
        f"💰 الرصيد: <b>{treasury['balance']:.0f}</b> {CURRENCY_ARABIC_NAME}\n"
        f"📥 إجمالي الإيداعات: {treasury['total_deposited']:.0f}\n"
        f"📤 إجمالي السحوبات: {treasury['total_withdrawn']:.0f}\n"
        f"\n📋 آخر المعاملات:{log_text if log_text else ' لا يوجد'}"
    )

    buttons = [
        btn("📥 إيداع", "gov_treasury_deposit", data={"aid": aid},
            owner=(user_id, chat_id), color="su"),
    ]
    if has_permission(aid, user_id, "manage_treasury"):
        buttons.append(btn("📤 سحب", "gov_treasury_withdraw",
                           data={"aid": aid}, owner=(user_id, chat_id), color="d"))
    if has_permission(aid, user_id, "reward_members"):
        buttons.append(btn("🎁 مكافأة عضو", "gov_reward_list",
                           data={"aid": aid, "page": 0},
                           owner=(user_id, chat_id), color="p"))
    buttons.append(btn("📋 السجل الكامل", "gov_treasury_log",
                       data={"aid": aid, "page": 0},
                       owner=(user_id, chat_id), color="p"))
    buttons.append(_back_gov(user_id, chat_id, aid))

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons,
            layout=[2, 1, 1, 1] if len(buttons) == 5 else [1] * len(buttons))


@register_action("gov_treasury_deposit")
def treasury_deposit_prompt(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])

    from utils.pagination.router import set_state
    set_state(user_id, chat_id, "gov_treasury_deposit", data={"aid": aid})

    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=(f"📥 <b>إيداع في الخزينة</b>\n\n"
                  f"أرسل المبلغ الذي تريد إيداعه.\n"
                  f"مثال: <code>500</code>"),
            buttons=[_back_gov(user_id, chat_id, aid)], layout=[1])


@register_action("gov_treasury_withdraw")
def treasury_withdraw_prompt(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])

    if not has_permission(aid, user_id, "manage_treasury"):
        bot.answer_callback_query(call.id, "❌ لا تملك صلاحية السحب.", show_alert=True)
        return

    from utils.pagination.router import set_state
    set_state(user_id, chat_id, "gov_treasury_withdraw", data={"aid": aid})

    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=(f"📤 <b>سحب من الخزينة</b>\n\n"
                  f"أرسل المبلغ الذي تريد سحبه.\n"
                  f"مثال: <code>500</code>"),
            buttons=[_back_gov(user_id, chat_id, aid)], layout=[1])


@register_action("gov_treasury_log")
def show_treasury_log(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])
    page = int(data.get("page", 0))

    log = get_treasury_log(aid, limit=50)
    items, total = paginate_list(log, page, per_page=8)

    tx_ar = {
        "deposit": "⬆️", "withdraw": "⬇️", "loot_share": "⚔️",
        "upgrade_cost": "🔧", "war_fund": "🪖", "reward": "🎁", "tax": "💸",
    }
    text = f"📋 <b>سجل الخزينة</b> (صفحة {page+1}/{total})\n{get_lines()}\n"
    for tx in items:
        sign = "+" if tx["amount"] > 0 else ""
        icon = tx_ar.get(tx["tx_type"], "•")
        text += f"\n{icon} {sign}{tx['amount']:.0f} — {tx.get('note', '')}"

    nav = []
    if page > 0:
        nav.append(btn("◀️", "gov_treasury_log", data={"aid": aid, "page": page - 1},
                       owner=(user_id, chat_id)))
    if page < total - 1:
        nav.append(btn("▶️", "gov_treasury_log", data={"aid": aid, "page": page + 1},
                       owner=(user_id, chat_id)))
    nav.append(_back_gov(user_id, chat_id, aid))

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=nav, layout=[len(nav)])


@register_action("gov_reward_list")
def show_reward_list(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])
    page = int(data.get("page", 0))

    if not has_permission(aid, user_id, "reward_members"):
        bot.answer_callback_query(call.id, "❌ لا تملك صلاحية المكافأة.", show_alert=True)
        return

    alliance = get_alliance_by_id(aid)
    if not alliance:
        bot.answer_callback_query(call.id, "❌ التحالف غير موجود")
        return

    members = [m for m in alliance["members"] if m["user_id"] != user_id]
    items, total = paginate_list(members, page, per_page=6)

    buttons = [
        btn(f"{_role_ar(m['role'])} — {m['user_id']}", "gov_reward_amount",
            data={"aid": aid, "to_uid": m["user_id"]},
            owner=(user_id, chat_id), color="su")
        for m in items
    ]
    nav = []
    if page > 0:
        nav.append(btn("◀️", "gov_reward_list", data={"aid": aid, "page": page - 1},
                       owner=(user_id, chat_id)))
    if page < total - 1:
        nav.append(btn("▶️", "gov_reward_list", data={"aid": aid, "page": page + 1},
                       owner=(user_id, chat_id)))
    nav.append(_back_gov(user_id, chat_id, aid))

    bot.answer_callback_query(call.id)
    edit_ui(call, text="🎁 <b>اختر العضو لمكافأته:</b>",
            buttons=buttons + nav, layout=grid(len(items), 1) + [len(nav)])


@register_action("gov_reward_amount")
def reward_amount_prompt(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])
    to_uid = int(data["to_uid"])

    from utils.pagination.router import set_state
    set_state(user_id, chat_id, "gov_reward_member", data={"aid": aid, "to_uid": to_uid})

    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=f"🎁 <b>مكافأة العضو {to_uid}</b>\n\nأرسل المبلغ:\nمثال: <code>200</code>",
            buttons=[_back_gov(user_id, chat_id, aid)], layout=[1])


# ══════════════════════════════════════════
# ⭐ السمعة
# ══════════════════════════════════════════

@register_action("gov_reputation")
def show_reputation(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])

    rep = get_alliance_reputation(aid)
    top = get_top_alliances_by_reputation(limit=5)

    text = (
        f"⭐ <b>سمعة التحالف</b>\n{get_lines()}\n"
        f"📊 النقاط: <b>{rep.get('score', 0):.0f}</b> / 1000\n"
        f"🏷️ اللقب: {rep.get('title', '😶 غير معروف')}\n\n"
        f"📈 الإحصائيات:\n"
        f"  ⚔️ حروب مكسوبة: {rep.get('wars_won', 0)}\n"
        f"  💀 حروب خسرت: {rep.get('wars_lost', 0)}\n"
        f"  🤝 حلفاء ساعدناهم: {rep.get('allies_helped', 0)}\n"
        f"  🐍 خيانات: {rep.get('betrayals', 0)}\n"
        f"  😴 تجاهل حروب: {rep.get('inactive_wars', 0)}\n\n"
        f"🏆 أفضل 5 تحالفات بالسمعة:\n"
    )
    for i, r in enumerate(top, 1):
        medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i - 1]
        text += f"  {medal} {r['name']} — {r['score']:.0f}\n"

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text,
            buttons=[_back_gov(user_id, chat_id, aid)], layout=[1])


# ══════════════════════════════════════════
# 🏆 الألقاب
# ══════════════════════════════════════════

@register_action("gov_titles")
def show_titles(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])

    my_titles = get_alliance_titles(aid)
    all_titles = get_all_current_titles()

    text = f"🏆 <b>الألقاب</b>\n{get_lines()}\n"

    if my_titles:
        text += "✨ <b>ألقابك الحالية:</b>\n"
        for t in my_titles:
            text += f"  {t['emoji']} {t['title_ar']}\n"
    else:
        text += "لا تملك ألقاباً حالياً.\n"

    text += f"\n🌐 <b>الألقاب العالمية الحالية:</b>\n"
    held = {t["title_key"]: t for t in all_titles}
    for key, (title_ar, emoji) in TITLE_DEFINITIONS.items():
        holder = held.get(key)
        if holder:
            text += f"  {emoji} {title_ar}: <b>{holder['alliance_name']}</b>\n"
        else:
            text += f"  {emoji} {title_ar}: شاغر\n"

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text,
            buttons=[_back_gov(user_id, chat_id, aid)], layout=[1])


# ══════════════════════════════════════════
# 🧬 الأدوار
# ══════════════════════════════════════════

@register_action("gov_roles")
def show_roles(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])
    page = int(data.get("page", 0))

    alliance = get_alliance_by_id(aid)
    if not alliance:
        bot.answer_callback_query(call.id, "❌ التحالف غير موجود")
        return

    members = alliance["members"]
    items, total = paginate_list(members, page, per_page=5)

    text = f"🧬 <b>هيكل التحالف</b> (صفحة {page+1}/{total})\n{get_lines()}\n"
    for m in items:
        text += f"  {_role_ar(m['role'])} — {m['user_id']}\n"

    can_assign = has_permission(aid, user_id, "assign_roles")
    buttons = []
    if can_assign:
        for m in items:
            if m["user_id"] == user_id:
                continue
            role = m["role"]
            if role == "member":
                buttons.append(btn(f"⬆️ ترقية {m['user_id']}", "gov_promote",
                                   data={"aid": aid, "target": m["user_id"]},
                                   owner=(user_id, chat_id), color="su"))
            elif role == "officer":
                buttons.append(btn(f"⬇️ تخفيض {m['user_id']}", "gov_demote",
                                   data={"aid": aid, "target": m["user_id"]},
                                   owner=(user_id, chat_id), color="d"))

    nav = []
    if page > 0:
        nav.append(btn("◀️", "gov_roles", data={"aid": aid, "page": page - 1},
                       owner=(user_id, chat_id)))
    if page < total - 1:
        nav.append(btn("▶️", "gov_roles", data={"aid": aid, "page": page + 1},
                       owner=(user_id, chat_id)))
    nav.append(_back_gov(user_id, chat_id, aid))

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text,
            buttons=buttons + nav,
            layout=[1] * len(buttons) + [len(nav)])


@register_action("gov_promote")
def do_promote(call, data):
    user_id = call.from_user.id
    aid = int(data["aid"])
    target = int(data["target"])

    if not has_permission(aid, user_id, "assign_roles"):
        bot.answer_callback_query(call.id, "❌ لا تملك صلاحية تعيين الأدوار.", show_alert=True)
        return

    ok, msg = promote_member(aid, target)
    bot.answer_callback_query(call.id, msg, show_alert=True)
    if ok:
        try:
            bot.send_message(target, f"⭐ تمت ترقيتك إلى ضابط في تحالفك!")
        except Exception:
            pass


@register_action("gov_demote")
def do_demote(call, data):
    user_id = call.from_user.id
    aid = int(data["aid"])
    target = int(data["target"])

    if not has_permission(aid, user_id, "assign_roles"):
        bot.answer_callback_query(call.id, "❌ لا تملك صلاحية تعيين الأدوار.", show_alert=True)
        return

    ok, msg = demote_member(aid, target)
    bot.answer_callback_query(call.id, msg, show_alert=True)


# ══════════════════════════════════════════
# 💸 الضرائب
# ══════════════════════════════════════════

@register_action("gov_tax")
def show_tax(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])

    if not has_permission(aid, user_id, "set_tax"):
        bot.answer_callback_query(call.id, "❌ لا تملك صلاحية إدارة الضرائب.", show_alert=True)
        return

    tax = get_tax_config(aid)
    status = "✅ مفعّل" if tax["enabled"] else "❌ معطّل"
    text = (
        f"💸 <b>نظام الضرائب</b>\n{get_lines()}\n"
        f"📌 الحالة: {status}\n"
        f"📊 المعدل: {tax['tax_rate']*100:.0f}%\n\n"
        f"الضريبة تُجمع يومياً من رصيد كل عضو وتُودع في الخزينة.\n"
        f"الحد الأقصى: 20%"
    )

    rates = [0, 2, 5, 10, 15, 20]
    rate_buttons = [
        btn(f"{r}%", "gov_tax_set",
            data={"aid": aid, "rate": r / 100, "enabled": 1 if r > 0 else 0},
            owner=(user_id, chat_id),
            color="su" if tax["tax_rate"] * 100 == r else "p")
        for r in rates
    ]
    rate_buttons.append(btn("🚫 تعطيل", "gov_tax_set",
                            data={"aid": aid, "rate": 0, "enabled": 0},
                            owner=(user_id, chat_id), color="d"))
    rate_buttons.append(_back_gov(user_id, chat_id, aid))

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=rate_buttons,
            layout=[3, 3, 1, 1])


@register_action("gov_tax_set")
def set_tax(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])
    rate = float(data["rate"])
    enabled = bool(int(data.get("enabled", 0)))

    if not has_permission(aid, user_id, "set_tax"):
        bot.answer_callback_query(call.id, "❌ لا تملك صلاحية.", show_alert=True)
        return

    ok, msg = set_tax_rate(aid, rate, enabled)
    bot.answer_callback_query(call.id, msg, show_alert=True)
    if ok:
        # إعادة عرض صفحة الضرائب
        show_tax(call, data)


# ══════════════════════════════════════════
# ⌨️ معالجة الإدخال النصي (الحالات)
# ══════════════════════════════════════════

def handle_governance_state(message, state: str, state_data: dict) -> bool:
    """
    يُعالج الإدخال النصي لحالات الحوكمة.
    يُستدعى من flow engine في replies.py.
    يُعيد True إذا عالج الحالة.
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text.strip() if message.text else ""

    if state == "gov_treasury_deposit":
        aid = int(state_data.get("aid", 0))
        try:
            amount = float(text.replace(",", ""))
        except ValueError:
            bot.reply_to(message, "❌ أرسل رقماً صحيحاً.")
            return True
        ok, msg = deposit_treasury(aid, user_id, amount)
        bot.reply_to(message, msg)
        from utils.pagination.router import clear_state
        clear_state(user_id, chat_id)
        return True

    if state == "gov_treasury_withdraw":
        aid = int(state_data.get("aid", 0))
        try:
            amount = float(text.replace(",", ""))
        except ValueError:
            bot.reply_to(message, "❌ أرسل رقماً صحيحاً.")
            return True
        ok, msg = withdraw_treasury(aid, user_id, amount)
        bot.reply_to(message, msg)
        from utils.pagination.router import clear_state
        clear_state(user_id, chat_id)
        return True

    if state == "gov_reward_member":
        aid = int(state_data.get("aid", 0))
        to_uid = int(state_data.get("to_uid", 0))
        try:
            amount = float(text.replace(",", ""))
        except ValueError:
            bot.reply_to(message, "❌ أرسل رقماً صحيحاً.")
            return True
        ok, msg = reward_member(aid, user_id, to_uid, amount)
        bot.reply_to(message, msg)
        if ok:
            try:
                bot.send_message(to_uid,
                    f"🎁 تلقيت مكافأة <b>{amount:.0f} {CURRENCY_ARABIC_NAME}</b> من خزينة تحالفك!",
                    parse_mode="HTML")
            except Exception:
                pass
        from utils.pagination.router import clear_state
        clear_state(user_id, chat_id)
        return True

    return False
