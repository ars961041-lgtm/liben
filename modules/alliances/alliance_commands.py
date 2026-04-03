"""
أوامر التحالفات — نقطة الدخول النصية
"""
from core.bot import bot
from database.db_queries.countries_queries import get_country_by_owner
from modules.alliances.alliance_handler import open_alliance_menu


ALLIANCE_COMMANDS = {
    "تحالفي", "التحالفات", "إنشاء تحالف", "انشاء تحالف",
    "دعوات التحالف", "الانسحاب من التحالف", "قوة التحالف",
}


def alliance_commands(message):
    if not message.text:
        return False
    text = message.text.strip()
    normalized = text.lower()

    if normalized in ["تحالفي", "التحالفات", "تحالف"]:
        open_alliance_menu(message)
        return True

    if text.startswith("إنشاء تحالف") or text.startswith("انشاء تحالف"):
        _create_alliance(message, text)
        return True

    if normalized == "دعوات التحالف":
        _show_invites(message)
        return True

    if normalized in ["الانسحاب من التحالف", "انسحاب من التحالف"]:
        _leave_alliance(message)
        return True

    if normalized in ["حل التحالف", "حل تحالفي"]:
        _dissolve_alliance(message)
        return True

    return False


def _create_alliance(message, text):
    user_id = message.from_user.id
    name = text.replace("إنشاء تحالف", "").replace("انشاء تحالف", "").strip()
    if not name:
        bot.reply_to(message, "❌ اكتب اسم التحالف.\nمثال: إنشاء تحالف [الاسم]")
        return

    country = get_country_by_owner(user_id)
    if not country:
        bot.reply_to(message, "❌ يجب أن تملك دولة لإنشاء تحالف.")
        return
    country = dict(country)

    from database.db_queries.alliances_queries import (
        get_alliance_by_user, alliance_name_exists, create_alliance
    )
    from database.db_queries.bank_queries import get_user_balance, deduct_user_balance

    if get_alliance_by_user(user_id):
        bot.reply_to(message, "❌ أنت بالفعل في تحالف.")
        return

    if alliance_name_exists(name):
        bot.reply_to(message, "❌ اسم التحالف مستخدم.")
        return

    COST = 500
    if get_user_balance(user_id) < COST:
        bot.reply_to(message, f"❌ تحتاج {COST} Liben لإنشاء تحالف.")
        return

    deduct_user_balance(user_id, COST)
    alliance_id = create_alliance(name, user_id, country["id"])
    bot.reply_to(message, f"🏰 تم إنشاء تحالف <b>{name}</b> بنجاح!\nاستخدم: تحالفي", parse_mode="HTML")


def _show_invites(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    from database.db_queries.alliances_queries import get_user_pending_invites
    from utils.pagination import btn, send_ui

    invites = get_user_pending_invites(user_id)
    if not invites:
        bot.reply_to(message, "📭 لا توجد دعوات معلقة.")
        return

    text = "📩 <b>دعوات التحالف المعلقة:</b>\n\n"
    buttons = []
    for inv in invites[:5]:
        text += f"🏰 {inv['name']}\n"
        buttons.append(btn(f"✅ قبول — {inv['name']}", "alliance_accept_invite",
                           data={"invite_id": inv["id"]}, owner=(user_id, chat_id), color="su"))
        buttons.append(btn(f"❌ رفض — {inv['name']}", "alliance_reject_invite",
                           data={"invite_id": inv["id"]}, owner=(user_id, chat_id), color="d"))

    layout = [2] * len(invites[:5])
    send_ui(chat_id, text=text, buttons=buttons, layout=layout, owner_id=user_id)


def _leave_alliance(message):
    user_id = message.from_user.id
    from database.db_queries.alliances_queries import leave_alliance
    ok, msg = leave_alliance(user_id, penalty=True)
    bot.reply_to(message, msg)


def _dissolve_alliance(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    from database.db_queries.alliances_queries import get_alliance_by_user
    from utils.pagination import btn, send_ui

    alliance = get_alliance_by_user(user_id)
    if not alliance:
        bot.reply_to(message, "❌ لست في أي تحالف.")
        return
    alliance = dict(alliance)
    if alliance["leader_id"] != user_id:
        bot.reply_to(message, "❌ فقط القائد يمكنه بدء تصويت الحل.")
        return

    send_ui(chat_id,
            text=f"💥 <b>حل تحالف {alliance['name']}</b>\n\nهل تريد بدء التصويت؟",
            buttons=[
                btn("✅ ابدأ التصويت", "alliance_dissolve_vote_send",
                    data={"aid": alliance["id"]}, owner=(user_id, chat_id), color="d"),
            ], layout=[1], owner_id=user_id)
