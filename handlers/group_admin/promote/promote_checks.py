"""
Pre-checks before showing the promote UI.
Returns (ok: bool, error_msg: str | None, bot_member)
"""
from core.bot import bot

# All permissions the bot can potentially grant
_ALL_PROMOTABLE = {
    "can_change_info",
    "can_delete_messages",
    "can_invite_users",
    "can_restrict_members",
    "can_pin_messages",
    "can_promote_members",
    "can_manage_chat",
    "can_manage_video_chats",
    "can_post_stories",
    "can_edit_stories",
    "can_delete_stories",
    "is_anonymous",
    "can_manage_tags",
}


def get_bot_available_perms(cid: int) -> set[str]:
    """
    Returns the set of permission keys the bot actually holds —
    it can only grant permissions it has itself.
    Returns empty set on failure.
    """
    try:
        bot_member = bot.get_chat_member(cid, bot.get_me().id)
        return {p for p in _ALL_PROMOTABLE if bool(getattr(bot_member, p, False))}
    except Exception:
        return set()


def run_promote_checks(message, target_uid: int) -> tuple:
    """
    Returns (True, None, bot_member) on success.
    Returns (False, error_text, None) on any failure.
    """
    cid = message.chat.id
    uid = message.from_user.id

    # 1. Must be a group
    if message.chat.type not in ("group", "supergroup"):
        return False, "❌ هذا الأمر يعمل في المجموعات فقط.", None

    # 2. Sender must be admin
    try:
        sender = bot.get_chat_member(cid, uid)
        if sender.status not in ("administrator", "creator"):
            return False, "❌ أنت لست مشرفاً في هذه المجموعة.", None
    except Exception as e:
        print(f"[promote_checks] sender check error: {e}")
        return False, "❌ تعذّر التحقق من صلاحياتك.", None

    # 3. Bot must be admin with can_promote_members
    try:
        bot_info   = bot.get_me()
        bot_member = bot.get_chat_member(cid, bot_info.id)
        if bot_member.status != "administrator":
            return False, "❌ البوت ليس مشرفاً في هذه المجموعة.", None
        if not bot_member.can_promote_members:
            return False, "❌ البوت لا يملك صلاحية ترقية الأعضاء.", None
    except Exception as e:
        print(f"[promote_checks] bot check error: {e}")
        return False, "❌ تعذّر التحقق من صلاحيات البوت.", None

    # 4. Target must be a member (not left/kicked)
    try:
        target = bot.get_chat_member(cid, target_uid)
        if target.status in ("left", "kicked"):
            return False, "❌ المستخدم المستهدف ليس في المجموعة.", None
    except Exception as e:
        print(f"[promote_checks] target check error: {e}")
        return False, "❌ تعذّر التحقق من المستخدم المستهدف.", None

    return True, None, bot_member
