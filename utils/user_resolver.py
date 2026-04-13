"""
utils/user_resolver.py — Canonical user resolution for all commands.

Single source of truth for resolving a target user from:
  1. Reply to message
  2. @username  → looked up in the users table
  3. Numeric user_id

All commands (mute, ban, promote, permissions, etc.) must use these functions.
No command should implement its own user-parsing logic.
"""
from database.db_queries.users_queries import get_user_id_by_username


_NO_TARGET_MSG = (
    "❌ حدد المستخدم بإحدى الطرق:\n"
    "• الرد على رسالته\n"
    "• <code>@username</code>\n"
    "• رقم المعرف مثل: <code>123456789</code>"
)

# Set to True to enable resolution debug logs (disable in production)
_DEBUG = True


def _dbg(tag: str, **kwargs):
    if not _DEBUG:
        return
    parts = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    print(f"[PERMS_DEBUG] {tag} | {parts}")


def resolve_user(message) -> tuple[int | None, str, str | None]:
    """
    Resolves the target user from three sources (priority order):
      1. Reply to message
      2. @username token in command text → looked up in users table
      3. Numeric user_id token in command text → name fetched from users table

    Returns:
      (user_id: int, display_name: str, error_msg: None)  — on success
      (None, "", error_msg: str)                           — on failure with reason
      (None, "", None)                                     — no target found at all
    """
    raw_text = (message.text or "").strip()
    # _dbg("input", text=repr(raw_text))

    # 1. Reply to message
    if message.reply_to_message and message.reply_to_message.from_user:
        u = message.reply_to_message.from_user
        # _dbg("source=reply", user_id=u.id, name=u.first_name)
        return u.id, u.first_name or str(u.id), None

    tokens = raw_text.split()
    # _dbg("tokens", args=tokens[1:])

    for token in tokens[1:]:   # skip the command itself
        # 2. @username
        if token.startswith("@") and len(token) > 1:
            uid, name = get_user_id_by_username(token)
            if uid:
                # _dbg("source=username", token=token, user_id=uid, name=name)
                return uid, name or token, None
            # _dbg("source=username", token=token, user_id=None, result="not_in_db")
            return None, "", (
                f"❌ المستخدم <code>{token}</code> غير موجود في قاعدة البيانات.\n"
                "يجب أن يكون قد تفاعل مع البوت مسبقاً."
            )

        # 3. Numeric user_id
        if token.lstrip("-").isdigit():
            uid = int(token)
            if uid <= 0:
                # _dbg("source=id", token=token, result="invalid_negative")
                continue
            try:
                from database.connection import get_db_conn as _conn
                cur = _conn().cursor()
                cur.execute("SELECT name FROM users WHERE user_id = ?", (uid,))
                row = cur.fetchone()
                name = (row[0] or "").strip() if row else ""
            except Exception:
                name = ""
            # _dbg("source=id", token=token, user_id=uid, name=name or "(unknown)")
            return uid, name or str(uid), None

    # _dbg("result=no_target_found")
    return None, "", None   # no target found


def get_target_user_id(message, text: str = None) -> int | None:
    """
    Lightweight resolver — returns only the user_id (or None).
    Use resolve_user() when you also need the display name or error message.
    """
    # 1. Reply to message
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id

    tokens = ((text or message.text or "").strip()).split()

    for token in tokens[1:]:
        # 2. @username
        if token.startswith("@") and len(token) > 1:
            try:
                uid, _ = get_user_id_by_username(token)
                return uid  # None if not found
            except Exception:
                return None

        # 3. Numeric user_id
        if token.lstrip("-").isdigit():
            uid = int(token)
            return uid if uid > 0 else None

    return None
