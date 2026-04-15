"""
modules/whispers/whispers_keyboards.py

كل منطق بناء أزرار الهمسات — مفصول تماماً عن whisper_handler.
"""

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.pagination.cache import store_cache


def build_whisper_group_buttons(
    sender_id: int,
    group_id: int,
    whisper_ids: dict,   # {r_uid: wid} خاصة  أو  {None: wid} لـ @all
    is_all: bool,
) -> InlineKeyboardMarkup:
    """
    يبني أزرار رسالة الهمسة في المجموعة.

    @all  → زر عرض فقط (wid واحد، to_user=NULL في DB)
    خاصة → زر عرض + زر رد
    """
    markup = InlineKeyboardMarkup()

    # استخراج أول wid صالح
    first_wid = next(
        (v for v in whisper_ids.values() if v is not None),
        None
    )
    if not first_wid:
        return markup

    # wids للـ callback — None key يصبح "all"
    wids_payload = {
        ("all" if k is None else str(k)): v
        for k, v in whisper_ids.items()
        if v is not None
    }

    payload_v = {"a": "wsp_view", "d": {
        "wid":    first_wid,
        "is_all": 1 if is_all else 0,
        "sid":    sender_id,
        "wids":   wids_payload,
    }}
    key_v = store_cache(None, None, payload_v, owner=None)
    markup.add(InlineKeyboardButton("🔐 عرض الهمسة", callback_data=f"k:{key_v}", style="success"))

    if not is_all:
        payload_r = {"a": "wsp_reply", "d": {
            "wids": wids_payload,
            "sid":  sender_id,
            "gid":  group_id,
        }}
        key_r = store_cache(None, None, payload_r, owner=None)
        markup.add(InlineKeyboardButton("↩️ الرد على الهمسة", callback_data=f"k:{key_r}", style="danger"))

    return markup


def build_whisper_create_button(deep_link: str) -> InlineKeyboardMarkup:
    """زر "✉️ كتابة الهمسة" في المجموعة قبل إرسال النص."""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✉️ كتابة الهمسة", url=deep_link, style="primary"))
    return markup


def clickable_name(name: str, user_id: int) -> str:
    """يُنشئ رابط HTML قابل للنقر يفتح ملف المستخدم في تيليغرام."""
    from utils.html_sanitizer import escape_html
    safe = escape_html(name)
    return f'<a href="tg://user?id={user_id}">{safe}</a>'
