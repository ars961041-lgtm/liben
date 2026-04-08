"""
تعطيل الوسائط — يحذف وسائط غير المشرفين تلقائياً عند تفعيل feat_media_lock.
"""
from core.bot import bot

# أنواع المحتوى التي تُعدّ وسائط
_MEDIA_TYPES = frozenset({
    "photo", "video", "audio", "voice", "video_note",
    "document", "sticker", "animation",
})


def _is_media(message) -> bool:
    """يتحقق إذا كانت الرسالة تحتوي على وسائط."""
    return any(getattr(message, t, None) for t in _MEDIA_TYPES)


def _is_group_admin(chat_id: int, user_id: int) -> bool:
    """يتحقق إذا كان المستخدم مشرفاً أو مالكاً."""
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


def _bot_can_delete(chat_id: int) -> bool:
    """يتحقق إذا كان البوت يملك صلاحية حذف الرسائل."""
    try:
        bot_id = bot.get_me().id
        member = bot.get_chat_member(chat_id, bot_id)
        return getattr(member, "can_delete_messages", False)
    except Exception:
        return False


def handle_media_lock(message) -> bool:
    """
    يُستدعى من _dispatch لكل رسالة في المجموعة.
    يرجع True إذا تم حذف الرسالة (لإيقاف المعالجة).
    """
    if message.chat.type not in ("group", "supergroup"):
        return False

    if not _is_media(message):
        return False

    cid = message.chat.id
    uid = message.from_user.id

    from database.db_queries.group_features_queries import is_feature_enabled
    if not is_feature_enabled(cid, "feat_media_lock"):
        return False

    # المشرفون مسموح لهم دائماً
    if _is_group_admin(cid, uid):
        return False

    # تحقق من صلاحية الحذف قبل المحاولة
    if not _bot_can_delete(cid):
        return False

    try:
        bot.delete_message(cid, message.message_id)
    except Exception:
        return False

    try:
        warning = bot.send_message(
            cid,
            f"❌ الوسائط غير مسموح بها في هذه المجموعة.",
            parse_mode="HTML",
        )
        # حذف رسالة التحذير بعد 5 ثوانٍ لإبقاء المجموعة نظيفة
        import threading
        def _delete_warning():
            import time
            time.sleep(5)
            try:
                bot.delete_message(cid, warning.message_id)
            except Exception:
                pass
        threading.Thread(target=_delete_warning, daemon=True).start()
    except Exception:
        pass

    return True
