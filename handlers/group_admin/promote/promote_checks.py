"""
Pre-checks before showing the promote UI.
Returns (ok: bool, error_msg: str | None, target_member)
"""
from core.bot import bot


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
        return False, f"❌ تعذّر التحقق من صلاحياتك: {e}", None

    # 3. Bot must be admin with can_promote_members
    try:
        bot_info = bot.get_me()
        bot_member = bot.get_chat_member(cid, bot_info.id)
        if bot_member.status != "administrator" or not bot_member.can_promote_members:
            return False, "❌ البوت لا يملك صلاحية ترقية الأعضاء.", None
    except Exception as e:
        return False, f"❌ تعذّر التحقق من صلاحيات البوت: {e}", None

    # 4. Target must be a member
    try:
        target = bot.get_chat_member(cid, target_uid)
        if target.status == "left" or target.status == "kicked":
            return False, "❌ المستخدم المستهدف ليس في المجموعة.", None
    except Exception as e:
        return False, f"❌ تعذّر التحقق من المستخدم المستهدف: {e}", None

    return True, None, bot_member
