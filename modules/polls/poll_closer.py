"""
poll_closer.py — إغلاق التصويتات المنتهية.
يُستدعى من المُجدوِل (daily_tasks.py) كل 5 دقائق.
لا يستخدم threading.Timer — موثوق حتى بعد إعادة تشغيل البوت.
"""
from database.db_queries.polls_queries import close_poll, get_poll_options, get_total_votes


def close_expired_poll(poll: dict):
    """
    يُغلق تصويتاً منتهياً ويُحدّث رسالته ويُرسل إشعاراً.
    poll: dict من get_expired_polls()
    """
    poll_id = poll["id"]
    close_poll(poll_id)

    # تحديث الرسالة المنشورة
    _refresh_closed_message(poll)

    # إشعار في نفس الشات
    _notify_closed(poll)


def _refresh_closed_message(poll: dict):
    try:
        from core.bot import bot
        from modules.polls.poll_handler import _build_poll_message
        from database.db_queries.polls_queries import get_poll

        # أعد قراءة التصويت بعد الإغلاق
        fresh = get_poll(poll["id"])
        if not fresh or not fresh.get("message_id"):
            return

        opts = get_poll_options(fresh["id"])
        text, markup = _build_poll_message(fresh["id"], fresh, opts)

        if fresh.get("question_media_id"):
            bot.edit_message_caption(
                caption=text,
                chat_id=fresh["chat_id"],
                message_id=fresh["message_id"],
                parse_mode="HTML",
                reply_markup=markup,
            )
        else:
            bot.edit_message_text(
                text,
                fresh["chat_id"],
                fresh["message_id"],
                parse_mode="HTML",
                reply_markup=markup,
            )
    except Exception as e:
        print(f"[poll_closer] تعذّر تحديث رسالة التصويت #{poll['id']}: {e}")


def _notify_closed(poll: dict):
    try:
        from core.bot import bot
        total = get_total_votes(poll["id"])
        bot.send_message(
            poll["chat_id"],
            f"🔒 <b>انتهى وقت التصويت #{poll['id']}</b>\n"
            f"❓ {poll['question']}\n"
            f"👥 إجمالي الأصوات: <b>{total}</b>",
            parse_mode="HTML",
        )
    except Exception as e:
        print(f"[poll_closer] تعذّر إرسال إشعار التصويت #{poll['id']}: {e}")
