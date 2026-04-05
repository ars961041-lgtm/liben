# handlers/group_admin/permissions.py
from core.config import developers_id
from core.bot import bot


# ── Developer check ───────────────────────────────────────────────────────────

def is_developer(message):
    return message.from_user.id in developers_id


# ── Sender role ───────────────────────────────────────────────────────────────

def is_admin(message):
    try:
        member = bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


def get_sender_member(message):
    """Returns the ChatMember object for the message sender, or None."""
    try:
        return bot.get_chat_member(message.chat.id, message.from_user.id)
    except Exception:
        return None


def get_bot_member(chat_id):
    """Returns the bot's ChatMember object, or None."""
    try:
        return bot.get_chat_member(chat_id, bot.get_me().id)
    except Exception:
        return None


# ── Sender-level permission checks ───────────────────────────────────────────
# These verify that the *admin who sent the command* actually holds the
# required permission — not just that the bot does.

def sender_can_delete(message) -> tuple[bool, str]:
    """
    Returns (True, "") if the sender may delete messages.
    Returns (False, reason) otherwise.
    """
    member = get_sender_member(message)
    if not member:
        return False, "❌ تعذّر التحقق من صلاحياتك."
    if member.status == "creator":
        return True, ""
    if member.status != "administrator":
        return False, "❌ أنت لست مشرفاً في هذه المجموعة."
    if not member.can_delete_messages:
        return False, (
            "⛔ ليس لديك صلاحية <b>حذف الرسائل</b>.\n"
            "You don't have the <b>Delete Messages</b> permission."
        )
    return True, ""


def sender_can_pin(message) -> tuple[bool, str]:
    member = get_sender_member(message)
    if not member:
        return False, "❌ تعذّر التحقق من صلاحياتك."
    if member.status == "creator":
        return True, ""
    if member.status != "administrator":
        return False, "❌ أنت لست مشرفاً في هذه المجموعة."
    if not member.can_pin_messages:
        return False, (
            "⛔ ليس لديك صلاحية <b>تثبيت الرسائل</b>.\n"
            "You don't have the <b>Pin Messages</b> permission."
        )
    return True, ""


def sender_can_restrict(message) -> tuple[bool, str]:
    member = get_sender_member(message)
    if not member:
        return False, "❌ تعذّر التحقق من صلاحياتك."
    if member.status == "creator":
        return True, ""
    if member.status != "administrator":
        return False, "❌ أنت لست مشرفاً في هذه المجموعة."
    if not member.can_restrict_members:
        return False, (
            "⛔ ليس لديك صلاحية <b>تقييد الأعضاء</b>.\n"
            "You don't have the <b>Restrict Members</b> permission."
        )
    return True, ""


# ── Bot-level permission checks ───────────────────────────────────────────────

def bot_is_admin(chat_id) -> bool:
    m = get_bot_member(chat_id)
    return m is not None and m.status == "administrator"


def can_delete_messages(chat_id) -> bool:
    m = get_bot_member(chat_id)
    return bool(m and m.can_delete_messages)


def can_pin_messages(chat_id) -> bool:
    m = get_bot_member(chat_id)
    return bool(m and m.can_pin_messages)


def can_restrict_members(chat_id) -> bool:
    m = get_bot_member(chat_id)
    return bool(m and m.can_restrict_members)


def can_change_info(chat_id) -> bool:
    m = get_bot_member(chat_id)
    return bool(m and m.can_change_info)
