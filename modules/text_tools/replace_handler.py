"""
معالج أمر الاستبدال الذكي
"""
from core.bot import bot
from modules.text_tools.replacer import parse_replace_command, replace_word
from utils.helpers import get_bot_link, get_lines


def handle_replace_command(message) -> bool:
    """
    يعالج أمر: تعديل [قديم] [جديد] [عدد؟]
    يجب أن يكون رداً على رسالة.
    يرجع True إذا تم التعامل مع الأمر.
    """
    text = (message.text or "").strip()
    if not text.startswith("تعديل "):
        return False

    # يجب أن يكون رداً على رسالة
    if not message.reply_to_message:
        bot.reply_to(
            message,
            "❌ <b>استخدام خاطئ</b>\n\n"
            "رد على الرسالة التي تريد تعديلها بـ:\n"
            "<code>تعديل كلمة كلمة</code>\n"
            "أو:\n"
            "<code>تعديل |</code>النص القديم<code>|</code> <code>|</code>النص الجديد<code>|</code>\n"
            "أو مع عدد:\n"
            "<code>تعديل |</code>قديم| |جديد<code>|</code> 2",
            parse_mode="HTML",
        )
        return True

    parsed = parse_replace_command(text)
    if parsed is None:
        bot.reply_to(
            message,
             "❌ <b>استخدام خاطئ</b>\n\n"
            "رد على الرسالة التي تريد تعديلها بـ:\n"
            "<code>تعديل كلمة كلمة</code>\n"
            "أو:\n"
            "<code>تعديل |النص القديم| |النص الجديد|</code>\n"
            "أو مع عدد:\n"
            "<code>تعديل |قديم| |جديد| 2</code>",
            parse_mode="HTML",
        )
        return True

    old, new, count = parsed

    # جلب النص الأصلي
    original = (
        message.reply_to_message.text
        or message.reply_to_message.caption
        or ""
    )
    if not original.strip():
        bot.reply_to(message, "❌ الرسالة المردود عليها لا تحتوي على نص.")
        return True

    # تنفيذ الاستبدال
    result, n = replace_word(original, old, new, count)

    if n == 0:
        bot.reply_to(
            message,
            f"⚠️ لم يتم العثور على الكلمة <b>{old}</b> في النص.",
            parse_mode="HTML",
        )
        return True

    # بناء الرد
    count_note = f"تم استبدال <b>{n}</b> تكرار" + (
        f" من أصل {count} مطلوب" if count > 0 and n < count else ""
    )
    
    total_words = len(result.split())
    total_characters = len(result)
    line = get_lines()
    
    reply = (
        f"{line}\n"
        f"🔢 <b>{count_note}</b>\n"
        f"📄 عدد الكلمات{total_words}، عدد الحروف {total_characters}\n"
        f"{line}\n"
        f"🤖 via {get_bot_link()}"
    )

    bot.reply_to(message, _escape(result), parse_mode="HTML")
    bot.reply_to(message, reply, parse_mode="HTML")
    return True


def _escape(text: str) -> str:
    """HTML escape بسيط."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
