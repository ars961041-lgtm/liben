"""
مساعدات واجهة المستخدم — send_result وأزرار موحدة
"""
from core.bot import bot
from utils.pagination import btn
from utils.pagination.buttons import build_keyboard

_B = "p"
_R = "d"


def send_result(
    chat_id: int,
    text: str,
    message_id: int = None,
    buttons: list = None,
    layout: list = None,
    owner_id: int = None,
    parse_mode: str = "HTML",
) -> int | None:
    """
    يعرض نتيجة عملية:
    - إذا كان message_id موجوداً → يحاول تعديل الرسالة
    - إذا فشل التعديل أو لم يكن message_id → يرسل رسالة جديدة
    - يُرجع message_id الفعلي للرسالة المُرسَلة/المُعدَّلة

    الأزرار الافتراضية (إذا لم تُمرَّر):
    ⬅️ رجوع (dev_back_main) + ❌ إغلاق (dev_close)
    """
    if buttons is None and owner_id is not None:
        owner   = (owner_id, chat_id)
        buttons = [
            btn("⬅️ رجوع", "dev_back_main", {}, color=_B, owner=owner),
            btn("❌ إغلاق", "dev_close",     {}, color=_R, owner=owner),
        ]
        layout = layout or [2]

    markup = build_keyboard(buttons, layout or [1], owner_id) if buttons else None

    if message_id:
        try:
            bot.edit_message_text(
                text, chat_id, message_id,
                parse_mode=parse_mode,
                reply_markup=markup,
            )
            return message_id
        except Exception:
            pass   # fallback to send_message

    try:
        sent = bot.send_message(
            chat_id, text,
            parse_mode=parse_mode,
            reply_markup=markup,
        )
        return sent.message_id
    except Exception:
        return None


def cancel_buttons(owner: tuple, back_action: str = "dev_back_main") -> tuple[list, list]:
    """يرجع (buttons, layout) لأزرار رجوع + إغلاق."""
    return [
        btn("⬅️ رجوع", back_action, {}, color=_B, owner=owner),
        btn("❌ إغلاق", "dev_close",  {}, color=_R, owner=owner),
    ], [2]


def prompt_with_cancel(
    chat_id: int,
    uid: int,
    text: str,
    message_id: int = None,
    cancel_action: str = "hub_dev_cancel",
) -> int | None:
    """
    يعرض رسالة طلب إدخال مع زر إلغاء فقط.
    يرجع message_id الفعلي.
    """
    owner      = (uid, chat_id)
    cancel_btn = btn("🚫 إلغاء", cancel_action, {}, color=_R, owner=owner)
    markup     = build_keyboard([cancel_btn], [1], uid)

    if message_id:
        try:
            bot.edit_message_text(
                text, chat_id, message_id,
                parse_mode="HTML",
                reply_markup=markup,
            )
            return message_id
        except Exception:
            pass

    try:
        sent = bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)
        return sent.message_id
    except Exception:
        return None
