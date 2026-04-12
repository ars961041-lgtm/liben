# political history

"""
📜 سجل الحروب السياسية — Political History
Player-facing history: past wars, voting results, who supported/refused.
"""
from core.bot import bot
from utils.pagination import btn, send_ui, edit_ui, register_action, paginate_list
from database.db_queries.countries_queries import get_country_by_owner
from database.db_queries.alliances_queries import get_alliance_by_country
from database.db_queries.political_war_queries import (
    get_wars_for_country, get_wars_for_alliance,
    get_political_war, get_war_votes, get_vote_summary,
    get_war_members, get_war_log, get_total_side_power,
)
from utils.helpers import get_lines


def open_political_history(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    country = get_country_by_owner(user_id)
    if not country:
        from core.personality import send_with_delay
        send_with_delay(chat_id, "❌ لا تملك دولة.", delay=0.3,
                        reply_to=message.message_id)
        return
    country = dict(country)
    alliance = get_alliance_by_country(country["id"])

    wars = get_wars_for_country(country["id"], limit=20)
    if not wars and alliance:
        wars = get_wars_for_alliance(alliance["id"], limit=20)

    if not wars:
        send_ui(chat_id,
                text="📜 <b>سجل الحروب السياسية</b>\n\nلا توجد حروب سياسية في سجلك بعد.",
                buttons=[], layout=[], owner_id=user_id,
                reply_to=message.message_id)
        return

    _render_history_list(chat_id, user_id, chat_id, wars, page=0,
                         send_msg=message)


def _render_history_list(chat_id, user_id, owner_chat_id, wars, page,
                         send_msg=None, edit_call=None):
    items, total = paginate_list(wars, page, per_page=5)

    status_icon = {
        "voting":      "🗳️",
        "preparation": "⏳",
        "active":      "⚔️",
        "ended":       "🏁",
        "cancelled":   "❌",
    }
    winner_ar = {
        "attacker": "⚔️ المهاجمون",
        "defender": "🛡️ المدافعون",
        "draw":     "🤝 تعادل",
    }
    wtype_ar = {
        "country_vs_country":  "دولة/دولة",
        "alliance_vs_alliance":"تحالف/تحالف",
        "hybrid":              "هجين",
    }

    text = f"📜 <b>سجل الحروب السياسية</b> (صفحة {page+1}/{total})\n{get_lines()}\n"
    buttons = []
    for w in items:
        icon = status_icon.get(w["status"], "•")
        wt   = wtype_ar.get(w["war_type"], w["war_type"])
        line = f"{icon} #{w['id']} — {wt}"
        if w["status"] == "ended" and w.get("winner_side"):
            line += f" | 🏆 {winner_ar.get(w['winner_side'], '')}"
        text += f"\n{line}"
        buttons.append(btn(f"{icon} #{w['id']} {wt}", "polhist_war_detail",
                           data={"war_id": w["id"], "page": page},
                           owner=(user_id, owner_chat_id), color="p"))

    nav = []
    if page > 0:
        nav.append(btn("◀️", "polhist_list",
                       data={"page": page - 1}, owner=(user_id, owner_chat_id)))
    if page < total - 1:
        nav.append(btn("▶️", "polhist_list",
                       data={"page": page + 1}, owner=(user_id, owner_chat_id)))

    all_btns = buttons + nav
    layout   = [1] * len(buttons) + ([len(nav)] if nav else [])

    if edit_call:
        edit_ui(edit_call, text=text, buttons=all_btns, layout=layout)
    else:
        send_ui(chat_id, text=text, buttons=all_btns, layout=layout,
                owner_id=user_id, reply_to=send_msg.message_id if send_msg else None)


@register_action("polhist_list")
def polhist_list_cb(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    page    = int(data.get("page", 0))

    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!")
        return
    country = dict(country)
    alliance = get_alliance_by_country(country["id"])
    wars = get_wars_for_country(country["id"], limit=20)
    if not wars and alliance:
        wars = get_wars_for_alliance(alliance["id"], limit=20)

    bot.answer_callback_query(call.id)
    _render_history_list(chat_id, user_id, chat_id, wars, page, edit_call=call)


@register_action("polhist_war_detail")
def polhist_war_detail(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    war_id  = data.get("war_id")
    back_page = int(data.get("page", 0))

    war = get_political_war(war_id)
    if not war:
        bot.answer_callback_query(call.id, "❌ الحرب غير موجودة")
        return

    summary = get_vote_summary(war_id)
    votes   = get_war_votes(war_id)
    att_members = get_war_members(war_id, "attacker")
    def_members = get_war_members(war_id, "defender")
    att_power   = get_total_side_power(war_id, "attacker")
    def_power   = get_total_side_power(war_id, "defender")

    status_ar = {
        "voting":      "🗳️ تصويت",
        "preparation": "⏳ تحضير",
        "active":      "⚔️ نشطة",
        "ended":       "🏁 منتهية",
        "cancelled":   "❌ ملغاة",
    }.get(war["status"], war["status"])

    dtype_ar = {"offensive": "هجومية", "defensive": "دفاعية"}.get(
        war["declaration_type"], war["declaration_type"])
    wtype_ar = {
        "country_vs_country":  "دولة ضد دولة",
        "alliance_vs_alliance":"تحالف ضد تحالف",
        "hybrid":              "هجين",
    }.get(war["war_type"], war["war_type"])

    # شريط التصويت
    def bar(pct):
        f = int(pct / 10)
        return f"{'█'*f}{'░'*(10-f)}"

    text = (
        f"📜 <b>تفاصيل الحرب #{war_id}</b>\n{get_lines()}\n"
        f"📋 {wtype_ar} ({dtype_ar})\n"
        f"📌 الحالة: {status_ar}\n"
    )

    if war.get("reason"):
        text += f"📝 السبب: {war['reason']}\n"

    if war["status"] == "ended" and war.get("winner_side"):
        winner_ar = {"attacker": "⚔️ المهاجمون", "defender": "🛡️ المدافعون",
                     "draw": "🤝 تعادل"}.get(war["winner_side"], "")
        text += f"🏆 الفائز: {winner_ar}\n"

    # نتيجة التصويت
    text += (
        f"\n🗳️ <b>نتيجة التصويت:</b>\n"
        f"[{bar(summary['support_pct'])}] {summary['support_pct']:.1f}%\n"
        f"✅ دعم: {summary['support']:.1f}  "
        f"❌ رفض: {summary['reject']:.1f}  "
        f"⚪ محايد: {summary['neutral']:.1f}\n"
        f"العتبة المطلوبة: {summary['threshold_pct']:.0f}%\n"
    )

    # من صوّت بماذا
    if votes:
        text += f"\n📊 <b>تصويت الدول ({len(votes)}):</b>\n"
        vote_icon = {"support": "✅", "reject": "❌", "neutral": "⚪"}
        for v in votes[:8]:
            icon = vote_icon.get(v["vote"], "•")
            text += f"  {icon} {v['country_name']} (وزن: {v['vote_weight']:.1f})\n"
        if len(votes) > 8:
            text += f"  ... و{len(votes)-8} آخرين\n"

    # الأعضاء المشاركون
    if att_members or def_members:
        text += f"\n⚔️ <b>المهاجمون ({att_power:.0f}):</b>\n"
        for m in att_members[:4]:
            text += f"  • {m['country_name']} ({m['power_contributed']:.0f})\n"
        text += f"🛡️ <b>المدافعون ({def_power:.0f}):</b>\n"
        for m in def_members[:4]:
            text += f"  • {m['country_name']} ({m['power_contributed']:.0f})\n"

    buttons = [
        btn("📋 السجل الكامل", "polhist_full_log",
            data={"war_id": war_id, "page": 0, "back_page": back_page},
            owner=(user_id, chat_id), color="p"),
        btn("🔙 رجوع", "polhist_list",
            data={"page": back_page}, owner=(user_id, chat_id)),
    ]

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons, layout=[1, 1])


@register_action("polhist_full_log")
def polhist_full_log(call, data):
    user_id   = call.from_user.id
    chat_id   = call.message.chat.id
    war_id    = data.get("war_id")
    page      = int(data.get("page", 0))
    back_page = int(data.get("back_page", 0))

    logs = get_war_log(war_id, limit=50)
    if not logs:
        bot.answer_callback_query(call.id, "لا يوجد سجل.")
        return

    items, total = paginate_list(logs, page, per_page=10)
    event_ar = {
        "declared":           "📣 إعلان حرب",
        "voted_support":      "✅ صوّت بالدعم",
        "voted_reject":       "❌ صوّت بالرفض",
        "voted_neutral":      "⚪ صوّت محايداً",
        "preparation_started":"⏳ بدأ التحضير",
        "war_started":        "⚔️ بدأت الحرب",
        "war_ended":          "🏁 انتهت الحرب",
        "withdrew_before":    "🚪 انسحب قبل البدء",
        "withdrew_after":     "⚠️ انسحب بعد البدء",
        "joined_late":        "➕ انضم متأخراً",
        "cancelled":          "❌ أُلغيت",
    }

    import json as _json
    text = f"📋 <b>سجل الحرب #{war_id}</b> (صفحة {page+1}/{total})\n{get_lines()}\n"
    for log in items:
        ev   = event_ar.get(log["event_type"], log["event_type"])
        name = log.get("country_name") or "النظام"
        try:
            extra = _json.loads(log.get("event_data") or "{}")
            weight = extra.get("weight")
            weight_str = f" — وزن: {weight:.1f}" if weight else ""
        except Exception:
            weight_str = ""
        text += f"\n{ev} — {name}{weight_str}"

    nav = []
    if page > 0:
        nav.append(btn("◀️", "polhist_full_log",
                       data={"war_id": war_id, "page": page-1, "back_page": back_page},
                       owner=(user_id, chat_id)))
    if page < total - 1:
        nav.append(btn("▶️", "polhist_full_log",
                       data={"war_id": war_id, "page": page+1, "back_page": back_page},
                       owner=(user_id, chat_id)))
    nav.append(btn("🔙", "polhist_war_detail",
                   data={"war_id": war_id, "page": back_page},
                   owner=(user_id, chat_id)))

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=nav, layout=[len(nav)])
