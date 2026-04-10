"""
قفل الوسائط — نظامان مستقلان:

  enable_lock_stickers : يحذف الستيكرات من غير المشرفين
  enable_lock_media    : يحذف الوسائط (صور/فيديو/ملفات/صوت...) من غير المشرفين

كلاهما لا يمس رسائل المشرفين والمالك.
"""
import threading
import time

from core.bot import bot

# ── أنواع الستيكرات فقط ──
_STICKER_TYPES = frozenset({"sticker"})

# ── أنواع الوسائط (كل شيء عدا الستيكرات والنص) ──
_MEDIA_TYPES = frozenset({
    "photo", "video", "audio", "voice",
    "video_note", "document", "animation",
})


# ══════════════════════════════════════════
# مساعدات
# ══════════════════════════════════════════

def _is_admin(chat_id: int, user_id: int) -> bool:
    try:
        status = bot.get_chat_member(chat_id, user_id).status
        return status in ("administrator", "creator")
    except Exception:
        return False


def _bot_can_delete(chat_id: int) -> bool:
    try:
        bot_id = bot.get_me().id
        member = bot.get_chat_member(chat_id, bot_id)
        return bool(getattr(member, "can_delete_messages", False))
    except Exception:
        return False


def _delete_after(chat_id: int, message_id: int, delay: int = 5):
    """يحذف رسالة بعد تأخير (للتحذيرات المؤقتة)."""
    def _run():
        time.sleep(delay)
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()


def _warn(chat_id: int, text: str):
    """يرسل تحذيراً مؤقتاً يُحذف بعد 5 ثوانٍ."""
    try:
        msg = bot.send_message(chat_id, text, parse_mode="HTML")
        _delete_after(chat_id, msg.message_id, delay=5)
    except Exception:
        pass


def _try_delete(chat_id: int, message_id: int) -> bool:
    """يحاول حذف الرسالة، يرجع True عند النجاح."""
    try:
        bot.delete_message(chat_id, message_id)
        return True
    except Exception:
        return False


# ══════════════════════════════════════════
# نقطة الدخول الرئيسية
# ══════════════════════════════════════════

def handle_media_lock(message) -> bool:
    """
    يُستدعى من _dispatch لكل رسالة في المجموعة — قبل أي معالج آخر.
    يرجع True إذا تم حذف الرسالة (لإيقاف المعالجة).
    """
    if message.chat.type not in ("group", "supergroup"):
        return False

    cid = message.chat.id
    uid = message.from_user.id

    # المشرفون والمالك معفيون دائماً
    if _is_admin(cid, uid):
        return False

    from database.db_queries.group_features_queries import is_feature_enabled

    # ── 1. فحص قفل الستيكرات ──
    if getattr(message, "sticker", None):
        if is_feature_enabled(cid, "enable_lock_stickers"):
            if not _bot_can_delete(cid):
                return False
            if _try_delete(cid, message.message_id):
                _warn(cid, "🎭 الستيكرات غير مسموح بها في هذه المجموعة.")
                return True

    # ── 2. فحص قفل الوسائط ──
    has_media = any(getattr(message, t, None) for t in _MEDIA_TYPES)
    if has_media:
        if is_feature_enabled(cid, "enable_lock_media"):
            if not _bot_can_delete(cid):
                return False
            if _try_delete(cid, message.message_id):
                _warn(cid, "🖼 الوسائط غير مسموح بها في هذه المجموعة.")
                return True

    return False
