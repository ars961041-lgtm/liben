"""
Government Decision Handler
Command: قرار حكومي / قرارات الدولة
"""
from core.bot import bot
from utils.pagination import btn, send_ui, edit_ui, register_action
from utils.helpers import get_lines
from modules.city.government_decisions import DECISIONS, get_active_decision, can_make_decision, make_decision

_B  = "p"
_GR = "su"
_RD = "d"


def handle_government_command(message) -> bool:
    from modules.country.services.city_service import CityService
    from database.db_queries.countries_queries import get_country_by_owner
    uid = message.from_user.id
    cid = message.chat.id

    country = get_country_by_owner(uid)
    if not country:
        bot.reply_to(message, "❌ ليس لديك دولة.")
        return True

    country = dict(country)
    _send_decisions_menu(cid, uid, country["id"], reply_to=message.message_id)
    return True


def _send_decisions_menu(cid, uid, country_id, reply_to=None, call=None):
    owner = (uid, cid)
    active = get_active_decision(country_id)
    can, reason = can_make_decision(country_id)

    if active:
        defn = active.get("definition", {})
        import time
        remaining = max(0, active["expires_at"] - int(time.time()))
        from utils.helpers import format_remaining_time
        status_text = (
            f"🟢 <b>القرار النشط:</b> {defn.get('emoji','')} {defn.get('name_ar','')}\n"
            f"📝 {defn.get('description_ar','')}\n"
            f"⏱️ ينتهي خلال: {format_remaining_time(remaining)}\n\n"
        )
    else:
        status_text = f"⚪ لا يوجد قرار نشط\n{reason}\n\n"

    text = (
        f"🏛 <b>القرارات الحكومية</b>\n"
        f"{get_lines()}\n\n"
        f"{status_text}"
        f"اختر قراراً لتفعيله:"
    )

    buttons = []
    for key, defn in DECISIONS.items():
        color = _GR if can else "w"
        buttons.append(btn(
            f"{defn['emoji']} {defn['name_ar']}",
            "gov_decision",
            {"key": key, "cid": country_id},
            owner=owner, color=color
        ))
    buttons.append(btn("❌ إغلاق", "gov_close", {}, owner=owner, color=_RD))

    layout = [2] * (len(DECISIONS) // 2) + ([1] if len(DECISIONS) % 2 else []) + [1]

    if call:
        edit_ui(call, text=text, buttons=buttons, layout=layout)
    else:
        send_ui(cid, text=text, buttons=buttons, layout=layout,
                owner_id=uid, reply_to=reply_to)


@register_action("gov_decision")
def on_gov_decision(call, data):
    uid        = call.from_user.id
    cid        = call.message.chat.id
    owner      = (uid, cid)
    decision_key = data.get("key")
    country_id   = data.get("cid")

    success, msg = make_decision(country_id, decision_key)
    bot.answer_callback_query(call.id, msg[:200], show_alert=True)

    if success:
        _send_decisions_menu(cid, uid, country_id, call=call)


@register_action("gov_close")
def on_gov_close(call, data):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
