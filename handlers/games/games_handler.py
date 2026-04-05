"""
معالج الألعاب — قائمة الألعاب مع دليل شامل لكل لعبة
"""
from core.bot import bot
from database.db_queries.bank_queries import update_bank_balance
from handlers.games.games_data import GAMES
from utils.pagination import btn, edit_ui, register_action, send_ui
from utils.constants import lines
from utils.helpers import get_lines

B  = "p"
BK = "d"
R  = "d"


# ══════════════════════════════════════════
# نقطة الدخول
# ══════════════════════════════════════════

def games_command(message):
    """يرجع True إذا تم التعامل مع الأمر."""
    if not message.text:
        return False
    normalized = message.text.strip().lower()
    if normalized in ["الألعاب", "الالعاب", "العاب", "ألعاب", "دليل الألعاب"]:
        _send_games_menu(message)
        return True
    return False


def _send_games_menu(message):
    uid   = message.from_user.id
    chat_id = message.chat.id
    owner = (uid, chat_id)

    text = (
        f"🎮 <b>دليل الألعاب</b>\n"
        f"{get_lines()}\n\n"
        f"اختر لعبة لعرض شرحها الكامل:"
    )
    buttons = [
        btn(f"{g['emoji']} {g['name']}", "game_detail",
            {"gid": gid, "p": 0}, color=B, owner=owner)
        for gid, g in GAMES.items()
    ]
    buttons.append(btn("❌ إخفاء", "game_hide", color=R, owner=owner))

    layout = _grid(len(buttons) - 1, 2) + [1]
    send_ui(chat_id, text=text, buttons=buttons,
            layout=layout, owner_id=uid,
            # رد على الرسالة الأصلية
            )
    # حذف رسالة الأمر لتقليل الفوضى في المجموعات
    try:
        if message.chat.type != "private":
            bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass


# ══════════════════════════════════════════
# عرض تفاصيل اللعبة
# ══════════════════════════════════════════

@register_action("game_detail")
def _on_game_detail(call, data):
    gid   = data.get("gid")
    page  = int(data.get("p", 0))
    owner = (call.from_user.id, call.message.chat.id)
    game  = GAMES.get(gid)

    if not game:
        bot.answer_callback_query(call.id, "❌ اللعبة غير موجودة", show_alert=True)
        return

    pages = game["pages"]
    total = len(pages)
    page  = max(0, min(page, total - 1))
    pg    = pages[page]

    text = (
        f"{game['emoji']} <b>{game['name']}</b>\n"
        f"{get_lines()}\n"
        f"📝 {game['desc_ar']}\n\n"
        f"📋 <b>{pg['title']}</b>\n"
        f"{get_lines()}\n\n"
        f"{pg['content']}"
    )
    if total > 1:
        text += f"\n\n📄 صفحة {page + 1} / {total}"

    buttons = []
    nav = []
    if page < total - 1:
        nav.append(btn("التالي ◀️", "game_detail", {"gid": gid, "p": page + 1}, color=B, owner=owner))
    if page > 0:
        nav.append(btn("▶️ السابق", "game_detail", {"gid": gid, "p": page - 1}, color=B, owner=owner))

    if nav:
        buttons.extend(nav)

    buttons.append(btn("🔙 قائمة الألعاب", "game_back_menu", color=BK, owner=owner))
    buttons.append(btn("❌ إخفاء",          "game_hide",       color=R,  owner=owner))

    layout = ([len(nav)] if nav else []) + [2]
    edit_ui(call, text=text, buttons=buttons, layout=layout)


# ══════════════════════════════════════════
# التنقل
# ══════════════════════════════════════════

@register_action("game_back_menu")
def _on_back_menu(call, data):
    owner = (call.from_user.id, call.message.chat.id)
    text  = (
        f"🎮 <b>دليل الألعاب</b>\n"
        f"{get_lines()}\n\n"
        f"اختر لعبة لعرض شرحها الكامل:"
    )
    buttons = [
        btn(f"{g['emoji']} {g['name']}", "game_detail",
            {"gid": gid, "p": 0}, color=B, owner=owner)
        for gid, g in GAMES.items()
    ]
    buttons.append(btn("❌ إخفاء", "game_hide", color=R, owner=owner))
    layout = _grid(len(buttons) - 1, 2) + [1]
    edit_ui(call, text=text, buttons=buttons, layout=layout)


@register_action("game_hide")
def _on_hide(call, data):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


# ══════════════════════════════════════════
# مساعد
# ══════════════════════════════════════════

def _grid(n: int, cols: int = 2) -> list:
    layout, rem = [], n
    while rem > 0:
        layout.append(min(cols, rem))
        rem -= cols
    return layout or [1]
