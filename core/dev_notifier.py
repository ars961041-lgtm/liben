"""
مُرسِل آمن لمجموعة المطورين
يمنع انهيار البوت عند:
- خطأ 400: chat not found
- خطأ 403: bot was kicked
- معرف مجموعة غير صالح (-1)
"""
import logging
from typing import Optional

log = logging.getLogger("DevNotifier")


def _get_group_id() -> Optional[int]:
    """يجلب معرف مجموعة المطورين من bot_constants ديناميكياً."""
    try:
        from core.admin import get_const_int
        gid = get_const_int("dev_group_id", -1)
        return gid if gid != -1 else None
    except Exception:
        return None


def send_to_dev_group(text: str, parse_mode: str = "HTML",
                      reply_markup=None, **kwargs) -> Optional[int]:
    """
    يرسل رسالة لمجموعة المطورين بأمان.
    يرجع message_id عند النجاح، أو None عند الفشل.
    لا يرفع أي استثناء.
    """
    gid = _get_group_id()
    if gid is None:
        log.debug("dev_group_id not set — skipping dev group message.")
        return None

    try:
        from core.bot import bot
        sent = bot.send_message(
            gid, text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            **kwargs,
        )
        return sent.message_id

    except Exception as e:
        err = str(e)
        # أخطاء متوقعة — سجّل فقط ولا تنهار
        if "chat not found" in err or "bot was kicked" in err or "400" in err or "403" in err:
            log.warning(f"[DevNotifier] Cannot reach dev group {gid}: {e}")
            _notify_primary_dev_on_failure(gid, err)
        else:
            log.error(f"[DevNotifier] Unexpected error sending to dev group: {e}")
        return None


def edit_dev_group_message(message_id: int, text: str,
                           parse_mode: str = "HTML",
                           reply_markup=None) -> bool:
    """
    يعدّل رسالة في مجموعة المطورين بأمان.
    يرجع True عند النجاح.
    """
    gid = _get_group_id()
    if gid is None:
        return False

    try:
        from core.bot import bot
        bot.edit_message_text(
            text, gid, message_id,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
        return True
    except Exception as e:
        log.warning(f"[DevNotifier] Cannot edit dev group message: {e}")
        return False


def _notify_primary_dev_on_failure(group_id: int, error: str):
    """
    يُشعر المطور الأساسي عبر الخاص إذا فشل الإرسال للمجموعة.
    يُستدعى مرة واحدة فقط لكل نوع خطأ (throttled).
    """
    try:
        from core.config import developers_id
        from core.bot import bot
        primary = next(iter(developers_id), None)
        if not primary:
            return
        bot.send_message(
            primary,
            f"⚠️ <b>تحذير: مجموعة المطورين غير متاحة</b>\n\n"
            f"المعرف: <code>{group_id}</code>\n"
            f"الخطأ: <code>{error[:200]}</code>\n\n"
            f"تحقق من أن البوت لا يزال عضواً في المجموعة.",
            parse_mode="HTML",
        )
    except Exception:
        pass   # لا تنهار إذا فشل الإشعار الخاص أيضاً
