"""
news_handler.py — Upgraded magazine UI with categories, importance filter,
                  "latest news" and "top news" views.

Commands handled:
  الأخبار / آخر الأخبار   → latest news (all categories)
  أهم الأخبار             → top news (HIGH + CRITICAL, last 7 days)
  أخبار الحرب             → war category
  أخبار الاقتصاد          → economy category
  أخبار التحالفات         → alliance category
  أخبار الترتيب           → rankings category
"""
import time
from core.bot import bot
from utils.pagination import btn, send_ui, edit_ui, register_action, paginate_list
from utils.helpers import get_lines
from modules.magazine import news_db as db

_IMPORTANCE_EMOJI = {
    "LOW":      "🔵",
    "MEDIUM":   "🟡",
    "HIGH":     "🔴",
    "CRITICAL": "🚨",
}

_CATEGORY_LABELS = {
    "war":       "⚔️ الحرب",
    "economy":   "💰 الاقتصاد",
    "rankings":  "🏆 الترتيب",
    "alliance":  "🏰 التحالفات",
    "rebellion": "🔴 التمردات",
    "event":     "🌍 الأحداث",
    "general":   "📋 عام",
}

_COMMANDS = {
    "الأخبار", "آخر الأخبار", "أخبار اليوم",
    "أهم الأخبار",
    "أخبار الحرب",
    "أخبار الاقتصاد",
    "أخبار التحالفات",
    "أخبار الترتيب",
}

RTL = "\u200F"

def handle_news_command(message) -> bool:
    text = (message.text or "").strip()
    if text not in _COMMANDS:
        return False

    uid = message.from_user.id
    cid = message.chat.id

    if text == "أهم الأخبار":
        posts = db.get_top_posts(limit=20)
        header = "🔥 <b>أهم الأخبار</b>"
    elif text == "أخبار الحرب":
        posts = db.get_latest_posts(limit=20, category="war")
        header = "⚔️ <b>أخبار الحرب</b>"
    elif text == "أخبار الاقتصاد":
        posts = db.get_latest_posts(limit=20, category="economy")
        header = "💰 <b>أخبار الاقتصاد</b>"
    elif text == "أخبار التحالفات":
        posts = db.get_latest_posts(limit=20, category="alliance")
        header = "🏰 <b>أخبار التحالفات</b>"
    elif text == "أخبار الترتيب":
        posts = db.get_latest_posts(limit=20, category="rankings")
        header = "🏆 <b>أخبار الترتيب</b>"
    else:
        posts = db.get_today_news()
        header = "📰 <b>آخر الأخبار</b>"

    if not posts:
        bot.reply_to(message, f"{header}\n\nلا توجد أخبار حالياً. تابعنا لاحقاً!")
        return True

    _send_news_page(cid, uid, posts, page=0, header=header,
                    reply_to=message.message_id)
    return True



def _send_news_page( cid, uid, posts, page=0, header="📰 <b>الأخبار</b>", reply_to=None, call=None ):
    items, total_pages = paginate_list(posts, page, per_page=3)
    owner = (uid, cid)

    # Header (RTL fixed)
    text = (
        f"{RTL}{header}  ({page+1}/{total_pages})\n"
        f"{RTL}{get_lines()}\n\n"
    )

    for p in items:
        ts = time.strftime("%H:%M %d/%m", time.localtime(p["created_at"]))
        imp = _IMPORTANCE_EMOJI.get(p.get("importance", "MEDIUM"), "🟡")
        cat = _CATEGORY_LABELS.get(p.get("category", "general"), "📋")

        title = p.get("title", "")
        body = p.get("body", "")

        text += (
            f"{RTL}{imp} <b>{title}</b>\n"
            f"{RTL}{cat} │ {ts}\n"
            f"{RTL}{body}\n\n"
        )

    # Navigation buttons
    nav = []
    if page > 0:
        nav.append(
            btn("◀️", "news_page",
                {"p": page - 1, "h": header}, owner=owner)
        )
    if page < total_pages - 1:
        nav.append(
            btn("▶️", "news_page",
                {"p": page + 1, "h": header}, owner=owner)
        )

    # Category buttons
    cat_buttons = [
        btn("⚔️ حرب", "news_cat", {"cat": "war", "p": 0}, owner=owner),
        btn("💰 اقتصاد", "news_cat", {"cat": "economy", "p": 0}, owner=owner),
        btn("🏰 تحالفات", "news_cat", {"cat": "alliance", "p": 0}, owner=owner),
        btn("🏆 ترتيب", "news_cat", {"cat": "rankings", "p": 0}, owner=owner),
        btn("🔥 الأهم", "news_top", {"p": 0}, owner=owner, color="su"),
        btn("❌ إغلاق", "news_close", {}, owner=owner, color="d"),
    ]

    all_buttons = nav + cat_buttons

    # Layout safe for RTL UI
    layout = ([len(nav)] if nav else []) + [2, 2, 2]

    if call:
        edit_ui(call, text=text, buttons=all_buttons, layout=layout)
    else:
        send_ui( cid, text=text, buttons=all_buttons, layout=layout, owner_id=uid, reply_to=reply_to)



@register_action("news_page")
def on_news_page(call, data):
    uid    = call.from_user.id
    cid    = call.message.chat.id
    page   = int(data.get("p", 0))
    header = data.get("h", "📰 <b>آخر الأخبار</b>")
    posts  = db.get_today_news()
    if not posts:
        bot.answer_callback_query(call.id, "لا توجد أخبار.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    _send_news_page(cid, uid, posts, page=page, header=header, call=call)


@register_action("news_cat")
def on_news_cat(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    cat  = data.get("cat", "general")
    page = int(data.get("p", 0))
    posts = db.get_latest_posts(limit=20, category=cat)
    header = _CATEGORY_LABELS.get(cat, "📋 عام")
    bot.answer_callback_query(call.id)
    if not posts:
        bot.answer_callback_query(call.id, "لا توجد أخبار في هذه الفئة.", show_alert=True)
        return
    _send_news_page(cid, uid, posts, page=page,
                    header=f"<b>{header}</b>", call=call)


@register_action("news_top")
def on_news_top(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    page  = int(data.get("p", 0))
    posts = db.get_top_posts(limit=20)
    bot.answer_callback_query(call.id)
    if not posts:
        bot.answer_callback_query(call.id, "لا توجد أخبار مهمة.", show_alert=True)
        return
    _send_news_page(cid, uid, posts, page=page,
                    header="🔥 <b>أهم الأخبار</b>", call=call)


@register_action("news_close")
def on_news_close(call, data):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
