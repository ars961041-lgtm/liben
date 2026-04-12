"""
Rankings Handler — ترتيبات المدن والدول والتحالفات
Commands: ترتيبات, تصنيفات
"""
from core.bot import bot
from utils.pagination import btn, send_ui, edit_ui, register_action
from utils.helpers import get_lines

_B  = "p"
_RD = "d"

_MEDALS = ["🥇", "🥈", "🥉"]


def handle_rankings_command(message) -> bool:
    text = (message.text or "").strip()
    if text not in ("ترتيبات", "تصنيفات", "ترتيب المدن", "ترتيب الدول"):
        return False
    uid = message.from_user.id
    cid = message.chat.id
    _send_rankings_menu(cid, uid, reply_to=message.message_id)
    return True


def _send_rankings_menu(cid, uid, reply_to=None, call=None):
    owner = (uid, cid)
    text = (
        f"🏆 <b>ترتيبات اللعبة</b>\n"
        f"{get_lines()}\n\n"
        "اختر فئة الترتيب:"
    )
    buttons = [
        btn("👥 أكبر سكاناً",       "rank_view", {"t": "population"},       owner=owner, color=_B),
        btn("💰 أقوى اقتصاداً",     "rank_view", {"t": "economy"},          owner=owner, color=_B),
        btn("⭐ أعلى مستوى",        "rank_view", {"t": "xp"},               owner=owner, color=_B),
        btn("🪖 الترتيب العسكري",   "rank_view", {"t": "military"},         owner=owner, color=_B),
        btn("🏰 التحالفات — اقتصاد","rank_view", {"t": "alliance_economy"}, owner=owner, color=_B),
        btn("🏰 التحالفات — عسكري", "rank_view", {"t": "alliance_military"},owner=owner, color=_B),
        btn("❌ إغلاق",              "rank_close", {},                        owner=owner, color=_RD),
    ]
    layout = [2, 2, 2, 1]
    if call:
        edit_ui(call, text=text, buttons=buttons, layout=layout)
    else:
        send_ui(cid, text=text, buttons=buttons, layout=layout,
                owner_id=uid, reply_to=reply_to)


@register_action("rank_view")
def on_rank_view(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)
    topic = data.get("t", "population")

    text = _build_ranking(topic)

    back = [
        btn("🔙 رجوع", "rank_back",  {}, owner=owner, color=_B),
        btn("❌ إغلاق", "rank_close", {}, owner=owner, color=_RD),
    ]
    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=back, layout=[2])


def _build_ranking(topic: str) -> str:
    from database.db_queries.tops_queries import (
        get_top_countries_by_population,
        get_top_countries_by_economy,
        get_top_countries_by_xp,
        get_military_ranking,
        get_top_alliances_by_economy,
        get_alliance_military_ranking,
    )

    if topic == "population":
        rows = get_top_countries_by_population(limit=10)
        title = "👥 أكبر الدول سكاناً"
        lines = [
            f"{_MEDALS[i] if i < 3 else f'{i+1}.'} {r['name']} — {int(r['value']):,} نسمة"
            for i, r in enumerate(rows)
        ]

    elif topic == "economy":
        rows = get_top_countries_by_economy(limit=10)
        title = "💰 أقوى الدول اقتصادياً"
        lines = [
            f"{_MEDALS[i] if i < 3 else f'{i+1}.'} {r['name']} — {r['value']:.0f}/ساعة"
            for i, r in enumerate(rows)
        ]

    elif topic == "xp":
        rows = get_top_countries_by_xp(limit=10)
        title = "⭐ أعلى الدول مستوى"
        lines = [
            f"{_MEDALS[i] if i < 3 else f'{i+1}.'} {r['name']} — متوسط مستوى {r.get('avg_level', 1):.1f}"
            for i, r in enumerate(rows)
        ]

    elif topic == "military":
        rows = get_military_ranking(limit=10)
        title = "🪖 الترتيب العسكري للدول"
        lines = [f"{_MEDALS[i] if i < 3 else f'{i+1}.'} {r['name']}" for i, r in enumerate(rows)]
        lines.append("\n⚠️ القوة الفعلية لا تُعرض لأسباب أمنية.")

    elif topic == "alliance_economy":
        rows = get_top_alliances_by_economy(limit=10)
        title = "🏰 أقوى التحالفات اقتصادياً"
        lines = [
            f"{_MEDALS[i] if i < 3 else f'{i+1}.'} {r['name']} — {r['value']:.0f}/ساعة"
            for i, r in enumerate(rows)
        ]

    elif topic == "alliance_military":
        rows = get_alliance_military_ranking(limit=10)
        title = "🏰 الترتيب العسكري للتحالفات"
        lines = [f"{_MEDALS[i] if i < 3 else f'{i+1}.'} {r['name']}" for i, r in enumerate(rows)]
        lines.append("\n⚠️ القوة الفعلية لا تُعرض لأسباب أمنية.")

    else:
        return "❌ فئة غير معروفة"

    body = "\n".join(lines) if lines else "لا توجد بيانات بعد."
    return f"🏆 <b>{title}</b>\n{get_lines()}\n\n{body}"


@register_action("rank_back")
def on_rank_back(call, data):
    bot.answer_callback_query(call.id)
    _send_rankings_menu(call.message.chat.id, call.from_user.id, call=call)


@register_action("rank_close")
def on_rank_close(call, data):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
