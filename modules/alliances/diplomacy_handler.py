# diplomacy handler

"""
معالج الدبلوماسية الاستراتيجية — واجهة المستخدم
Alliance Diplomacy Handler — UI & Callbacks
"""
from core.bot import bot
from utils.pagination import btn, send_ui, edit_ui, register_action, paginate_list, grid
from database.db_queries.countries_queries import get_country_by_owner
from database.db_queries.alliances_queries import (
    get_alliance_by_user, get_alliance_by_id, get_all_active_alliances,
)
from database.db_queries.alliance_diplomacy_queries import (
    get_alliance_treaties, get_pending_treaties_for_alliance,
    get_pending_expansion_for_alliance, get_federation_by_alliance,
    get_federation_members, get_all_active_federations,
    get_intelligence, get_all_intelligence_ranked,
    get_balance_log, get_influence,
)
from modules.alliances.diplomacy_service import (
    send_treaty_proposal, respond_to_treaty, betray_treaty,
    send_expansion_proposal, execute_expansion,
    get_diplomacy_vote_bonus, _treaty_ar, _expansion_ar,
)
from utils.helpers import get_lines
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME


def _back_dip(user_id, chat_id, aid):
    return btn("🔙 رجوع", "dip_main", data={"aid": aid}, owner=(user_id, chat_id))


# ══════════════════════════════════════════
# 🏠 القائمة الرئيسية
# ══════════════════════════════════════════

def open_diplomacy_menu(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    alliance = get_alliance_by_user(user_id)
    if not alliance:
        from core.personality import send_with_delay
        send_with_delay(chat_id, "❌ لست في أي تحالف.", delay=0.3,
                        reply_to=message.message_id)
        return
    alliance = dict(alliance)
    _render_dip_main(chat_id, user_id, chat_id, alliance["id"], send_msg=message)


def _render_dip_main(chat_id, user_id, owner_chat_id, aid,
                     send_msg=None, edit_call=None):
    alliance = get_alliance_by_id(aid)
    if not alliance:
        return

    treaties = get_alliance_treaties(aid, status="active")
    pending  = get_pending_treaties_for_alliance(aid)
    fed      = get_federation_by_alliance(aid)
    intel    = get_intelligence(aid)
    bonus    = get_diplomacy_vote_bonus(aid)

    fed_line = f"🌐 الاتحاد: {fed['name']}" if fed else "🌐 لا اتحاد"
    text = (
        f"🤝 <b>دبلوماسية تحالف: {alliance['name']}</b>\n"
        f"{get_lines()}\n"
        f"📜 معاهدات نشطة: {len(treaties)}\n"
        f"📩 معاهدات معلقة: {len(pending)}\n"
        f"{fed_line}\n"
        f"🗳️ مكافأة التصويت: +{bonus*100:.0f}%\n"
        f"🧠 جاهزية الحرب: {intel.get('war_readiness', 0):.0f}/100\n\n"
        f"اختر ما تريد:"
    )

    buttons = [
        btn("📜 المعاهدات",    "dip_treaties",   data={"aid": aid},
            owner=(user_id, owner_chat_id), color="p"),
        btn("🌍 التوسع",       "dip_expansion",  data={"aid": aid},
            owner=(user_id, owner_chat_id), color="p"),
        btn("🌐 الاتحادات",   "dip_federations", data={"aid": aid},
            owner=(user_id, owner_chat_id), color="p"),
        btn("🧠 الاستخبارات", "dip_intel",       data={"aid": aid},
            owner=(user_id, owner_chat_id), color="p"),
        btn("⚖️ التوازن",     "dip_balance",     data={"aid": aid},
            owner=(user_id, owner_chat_id), color="su"),
    ]
    if pending:
        buttons.insert(0, btn(f"📩 {len(pending)} معاهدة معلقة", "dip_pending_treaties",
                              data={"aid": aid}, owner=(user_id, owner_chat_id), color="d"))

    layout = [2, 2, 1] if not pending else [1, 2, 2, 1]

    if edit_call:
        edit_ui(edit_call, text=text, buttons=buttons, layout=layout)
    else:
        send_ui(chat_id, text=text, buttons=buttons, layout=layout,
                owner_id=user_id, reply_to=send_msg.message_id if send_msg else None)


@register_action("dip_main")
def dip_main_cb(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])
    bot.answer_callback_query(call.id)
    _render_dip_main(chat_id, user_id, chat_id, aid, edit_call=call)


# ══════════════════════════════════════════
# 📜 المعاهدات
# ══════════════════════════════════════════

@register_action("dip_treaties")
def show_treaties(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])
    page = int(data.get("page", 0))

    treaties = get_alliance_treaties(aid)
    status_ar = {"active": "✅", "pending": "⏳", "expired": "⌛", "broken": "💔", "rejected": "❌"}
    type_ar   = {"non_aggression": "عدم اعتداء", "military_alliance": "تحالف عسكري",
                 "trade": "تجارة", "protectorate": "حماية"}

    items, total = paginate_list(treaties, page, per_page=5)
    text = f"📜 <b>معاهدات التحالف</b> (صفحة {page+1}/{total})\n{get_lines()}\n"
    buttons = []
    for t in items:
        other = t["name_b"] if t["alliance_a"] == aid else t["name_a"]
        s = status_ar.get(t["status"], t["status"])
        tp = type_ar.get(t["treaty_type"], t["treaty_type"])
        text += f"\n{s} {tp} مع <b>{other}</b>"
        if t["status"] == "active":
            buttons.append(btn(f"💔 كسر مع {other}", "dip_break_treaty",
                               data={"aid": aid, "tid": t["id"]},
                               owner=(user_id, chat_id), color="d"))

    # زر اقتراح معاهدة جديدة
    buttons.append(btn("➕ اقتراح معاهدة", "dip_propose_treaty_target",
                       data={"aid": aid, "page": 0},
                       owner=(user_id, chat_id), color="su"))

    nav = []
    if page > 0:
        nav.append(btn("◀️", "dip_treaties", data={"aid": aid, "page": page-1},
                       owner=(user_id, chat_id)))
    if page < total - 1:
        nav.append(btn("▶️", "dip_treaties", data={"aid": aid, "page": page+1},
                       owner=(user_id, chat_id)))
    nav.append(_back_dip(user_id, chat_id, aid))

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons + nav,
            layout=[1]*len(buttons) + [len(nav)])


@register_action("dip_pending_treaties")
def show_pending_treaties(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])

    pending = get_pending_treaties_for_alliance(aid)
    if not pending:
        bot.answer_callback_query(call.id, "لا توجد معاهدات معلقة.")
        return

    text = f"📩 <b>معاهدات معلقة</b>\n{get_lines()}\n"
    buttons = []
    for t in pending[:5]:
        tp = _treaty_ar(t["treaty_type"])
        text += f"\n📜 {tp} من <b>{t['name_a']}</b>"
        buttons.append(btn(f"✅ قبول — {tp}", "dip_accept_treaty",
                           data={"aid": aid, "tid": t["id"]},
                           owner=(user_id, chat_id), color="su"))
        buttons.append(btn(f"❌ رفض", "dip_reject_treaty",
                           data={"aid": aid, "tid": t["id"]},
                           owner=(user_id, chat_id), color="d"))

    buttons.append(_back_dip(user_id, chat_id, aid))
    layout = [2] * len(pending[:5]) + [1]
    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons, layout=layout)


@register_action("dip_accept_treaty")
def accept_treaty_cb(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])
    tid = int(data["tid"])
    ok, msg = respond_to_treaty(user_id, tid, accept=True)
    bot.answer_callback_query(call.id, msg, show_alert=True)
    if ok:
        _render_dip_main(chat_id, user_id, chat_id, aid, edit_call=call)


@register_action("dip_reject_treaty")
def reject_treaty_cb(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])
    tid = int(data["tid"])
    ok, msg = respond_to_treaty(user_id, tid, accept=False)
    bot.answer_callback_query(call.id, msg, show_alert=True)
    _render_dip_main(chat_id, user_id, chat_id, aid, edit_call=call)


@register_action("dip_break_treaty")
def break_treaty_cb(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])
    tid = int(data["tid"])

    edit_ui(call,
            text="⚠️ <b>تأكيد كسر المعاهدة</b>\n\nسيُخصم من سمعة تحالفك. هل أنت متأكد؟",
            buttons=[
                btn("✅ نعم، اكسر", "dip_break_treaty_confirm",
                    data={"aid": aid, "tid": tid}, owner=(user_id, chat_id), color="d"),
                btn("🔙 إلغاء", "dip_treaties",
                    data={"aid": aid}, owner=(user_id, chat_id)),
            ], layout=[2])


@register_action("dip_break_treaty_confirm")
def break_treaty_confirm(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])
    tid = int(data["tid"])
    ok, msg = betray_treaty(user_id, tid)
    bot.answer_callback_query(call.id, msg, show_alert=True)
    _render_dip_main(chat_id, user_id, chat_id, aid, edit_call=call)


@register_action("dip_propose_treaty_target")
def propose_treaty_target(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])
    page = int(data.get("page", 0))

    alliances = get_all_active_alliances(exclude_id=aid)
    items, total = paginate_list(alliances, page, per_page=6)

    buttons = [
        btn(f"🏰 {a['name']}", "dip_propose_treaty_type",
            data={"aid": aid, "target": a["id"]},
            owner=(user_id, chat_id), color="p")
        for a in items
    ]
    nav = []
    if page > 0:
        nav.append(btn("◀️", "dip_propose_treaty_target",
                       data={"aid": aid, "page": page-1}, owner=(user_id, chat_id)))
    if page < total - 1:
        nav.append(btn("▶️", "dip_propose_treaty_target",
                       data={"aid": aid, "page": page+1}, owner=(user_id, chat_id)))
    nav.append(_back_dip(user_id, chat_id, aid))

    bot.answer_callback_query(call.id)
    edit_ui(call, text="🏰 <b>اختر التحالف للمعاهدة:</b>",
            buttons=buttons + nav, layout=grid(len(items), 2) + [len(nav)])


@register_action("dip_propose_treaty_type")
def propose_treaty_type(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])
    target = int(data["target"])

    types = [
        ("non_aggression",    "🕊️ عدم اعتداء",    "su"),
        ("military_alliance", "⚔️ تحالف عسكري",   "d"),
        ("trade",             "💰 تجارة",           "p"),
        ("protectorate",      "🛡️ حماية",          "p"),
    ]
    buttons = [
        btn(label, "dip_do_propose_treaty",
            data={"aid": aid, "target": target, "ttype": ttype},
            owner=(user_id, chat_id), color=color)
        for ttype, label, color in types
    ]
    buttons.append(_back_dip(user_id, chat_id, aid))

    from modules.alliances.diplomacy_service import TREATY_COST
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=f"📜 <b>نوع المعاهدة</b>\nالتكلفة: {TREATY_COST} {CURRENCY_ARABIC_NAME}\n\nاختر النوع:",
            buttons=buttons, layout=[2, 2, 1])


@register_action("dip_do_propose_treaty")
def do_propose_treaty(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])
    target = int(data["target"])
    ttype = data["ttype"]

    ok, msg = send_treaty_proposal(user_id, target, ttype)
    bot.answer_callback_query(call.id, msg, show_alert=True)
    if ok:
        _render_dip_main(chat_id, user_id, chat_id, aid, edit_call=call)
    else:
        edit_ui(call, text=msg, buttons=[_back_dip(user_id, chat_id, aid)], layout=[1])


# ══════════════════════════════════════════
# 🌍 التوسع
# ══════════════════════════════════════════

@register_action("dip_expansion")
def show_expansion(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])

    pending = get_pending_expansion_for_alliance(aid)
    text = f"🌍 <b>التوسع الاستراتيجي</b>\n{get_lines()}\n"
    if pending:
        text += f"📩 {len(pending)} اقتراح توسع معلق\n"

    buttons = [
        btn("🔴 استيعاب تحالف", "dip_expand_target",
            data={"aid": aid, "etype": "absorb", "page": 0},
            owner=(user_id, chat_id), color="d"),
        btn("🔵 اندماج", "dip_expand_target",
            data={"aid": aid, "etype": "merge", "page": 0},
            owner=(user_id, chat_id), color="p"),
        btn("🟢 تأسيس اتحاد", "dip_expand_target",
            data={"aid": aid, "etype": "federate", "page": 0},
            owner=(user_id, chat_id), color="su"),
    ]
    if pending:
        buttons.insert(0, btn(f"📩 اقتراحات واردة ({len(pending)})",
                              "dip_expansion_incoming",
                              data={"aid": aid}, owner=(user_id, chat_id), color="su"))
    buttons.append(_back_dip(user_id, chat_id, aid))

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons,
            layout=[1] * len(buttons))


@register_action("dip_expand_target")
def expand_target(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])
    etype = data["etype"]
    page = int(data.get("page", 0))

    alliances = get_all_active_alliances(exclude_id=aid)
    items, total = paginate_list(alliances, page, per_page=6)

    etype_ar = _expansion_ar(etype)
    buttons = [
        btn(f"🏰 {a['name']} (قوة: {a['power']:.0f})", "dip_do_expand",
            data={"aid": aid, "etype": etype, "target": a["id"]},
            owner=(user_id, chat_id), color="p")
        for a in items
    ]
    nav = []
    if page > 0:
        nav.append(btn("◀️", "dip_expand_target",
                       data={"aid": aid, "etype": etype, "page": page-1},
                       owner=(user_id, chat_id)))
    if page < total - 1:
        nav.append(btn("▶️", "dip_expand_target",
                       data={"aid": aid, "etype": etype, "page": page+1},
                       owner=(user_id, chat_id)))
    nav.append(btn("🔙", "dip_expansion", data={"aid": aid}, owner=(user_id, chat_id)))

    bot.answer_callback_query(call.id)
    edit_ui(call, text=f"🌍 <b>اختر هدف {etype_ar}:</b>",
            buttons=buttons + nav, layout=grid(len(items), 1) + [len(nav)])


@register_action("dip_do_expand")
def do_expand(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])
    etype = data["etype"]
    target = int(data["target"])

    ok, msg = send_expansion_proposal(user_id, target, etype)
    bot.answer_callback_query(call.id, msg, show_alert=True)
    if ok:
        _render_dip_main(chat_id, user_id, chat_id, aid, edit_call=call)


@register_action("dip_expansion_incoming")
def expansion_incoming(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])

    pending = get_pending_expansion_for_alliance(aid)
    if not pending:
        bot.answer_callback_query(call.id, "لا توجد اقتراحات.")
        return

    text = f"📩 <b>اقتراحات التوسع الواردة</b>\n{get_lines()}\n"
    buttons = []
    for p in pending[:4]:
        etype_ar = _expansion_ar(p["expansion_type"])
        text += f"\n🌍 {etype_ar} من <b>{p['initiator_name']}</b>"
        buttons.append(btn(f"✅ قبول — {etype_ar}", "dip_accept_expand",
                           data={"aid": aid, "eid": p["id"]},
                           owner=(user_id, chat_id), color="su"))
        buttons.append(btn("❌ رفض", "dip_reject_expand",
                           data={"aid": aid, "eid": p["id"]},
                           owner=(user_id, chat_id), color="d"))

    buttons.append(_back_dip(user_id, chat_id, aid))
    layout = [2] * len(pending[:4]) + [1]
    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons, layout=layout)


@register_action("dip_accept_expand")
def accept_expand_cb(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])
    eid = int(data["eid"])
    ok, msg = execute_expansion(user_id, eid, accept=True)
    bot.answer_callback_query(call.id, msg, show_alert=True)
    _render_dip_main(chat_id, user_id, chat_id, aid, edit_call=call)


@register_action("dip_reject_expand")
def reject_expand_cb(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])
    eid = int(data["eid"])
    ok, msg = execute_expansion(user_id, eid, accept=False)
    bot.answer_callback_query(call.id, msg, show_alert=True)
    _render_dip_main(chat_id, user_id, chat_id, aid, edit_call=call)


# ══════════════════════════════════════════
# 🌐 الاتحادات
# ══════════════════════════════════════════

@register_action("dip_federations")
def show_federations(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])

    my_fed = get_federation_by_alliance(aid)
    all_feds = get_all_active_federations()

    text = f"🌐 <b>الاتحادات</b>\n{get_lines()}\n"
    if my_fed:
        members = get_federation_members(my_fed["id"])
        text += f"✅ أنت في اتحاد: <b>{my_fed['name']}</b>\n"
        text += f"👥 الأعضاء: {len(members)}\n"
        for m in members:
            text += f"  • {m['name']} (قوة: {m['power']:.0f})\n"
    else:
        text += "لست في أي اتحاد.\n"

    text += f"\n🌍 الاتحادات النشطة: {len(all_feds)}\n"
    for f in all_feds[:5]:
        text += f"  🌐 {f['name']} — {f['member_count']} تحالفات\n"

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text,
            buttons=[_back_dip(user_id, chat_id, aid)], layout=[1])


# ══════════════════════════════════════════
# 🧠 الاستخبارات
# ══════════════════════════════════════════

@register_action("dip_intel")
def show_intel(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])

    from database.db_queries.alliance_diplomacy_queries import compute_intelligence
    intel = compute_intelligence(aid)
    ranked = get_all_intelligence_ranked()

    def bar(val):
        filled = int(val / 10)
        return "█" * filled + "░" * (10 - filled)

    text = (
        f"🧠 <b>تقرير الاستخبارات</b>\n{get_lines()}\n"
        f"📊 النشاط:       {bar(intel['activity_score'])} {intel['activity_score']:.0f}\n"
        f"⚔️ جاهزية الحرب: {bar(intel['war_readiness'])} {intel['war_readiness']:.0f}\n"
        f"💰 الاستقرار:    {bar(intel['economic_stability'])} {intel['economic_stability']:.0f}\n"
        f"☠️ مستوى التهديد:{bar(intel['threat_level'])} {intel['threat_level']:.0f}\n\n"
        f"🌍 <b>أخطر التحالفات:</b>\n"
    )
    for i, r in enumerate(ranked[:5], 1):
        text += f"  {i}. {r['name']} — تهديد: {r['threat_level']:.0f}\n"

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text,
            buttons=[_back_dip(user_id, chat_id, aid)], layout=[1])


# ══════════════════════════════════════════
# ⚖️ التوازن
# ══════════════════════════════════════════

@register_action("dip_balance")
def show_balance(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    aid = int(data["aid"])

    log = get_balance_log(aid, limit=8)
    rule_ar = {
        "diminishing_returns": "📉 تناقص العوائد",
        "internal_instability": "⚠️ عدم استقرار",
        "betrayal_chain": "🐍 سلسلة خيانات",
    }

    text = f"⚖️ <b>سجل قواعد التوازن</b>\n{get_lines()}\n"
    if log:
        for entry in log:
            rule = rule_ar.get(entry["rule_type"], entry["rule_type"])
            text += f"\n{rule}: {entry['note']}"
    else:
        text += "لا توجد عقوبات مُطبَّقة."

    text += (
        f"\n\n📋 <b>قواعد التوازن:</b>\n"
        f"• ≥{7} أعضاء: -2% قوة لكل عضو زائد\n"
        f"• ≥{9} أعضاء: -سمعة (عدم استقرار)\n"
        f"• ≥2 خيانات/30 يوم: -سمعة مضاعفة"
    )

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text,
            buttons=[_back_dip(user_id, chat_id, aid)], layout=[1])


# ══════════════════════════════════════════
# ⌨️ معالجة الإدخال النصي (مستقبلاً)
# ══════════════════════════════════════════

def handle_diplomacy_state(message, state: str, state_data: dict) -> bool:
    """نقطة توسع للحالات النصية المستقبلية في نظام الدبلوماسية."""
    return False
