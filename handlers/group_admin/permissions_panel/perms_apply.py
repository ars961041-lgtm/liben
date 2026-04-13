"""
Applies admin permission changes via promoteChatMember.

Return contract:
  (True,  "")     — applied (or soft-skipped)
  (False, msg)    — hard API failure
"""
import time as _time
from core.bot import bot
from utils.logger import log_event
from .perms_config import (
    PROMOTE_KEYS,
    bot_can_promote,
    get_bot_available_promote_perms,
    friendly_error,
)

_FRIENDLY_FAIL = "❌ فشل تطبيق الصلاحيات"

_DEMOTE_KWARGS = {k: False for k in PROMOTE_KEYS}


def _log(tag: str, **kwargs):
    parts = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    print(f"[{tag}] {parts}")


def _apply_promote(cid: int, target_uid: int, promote: dict) -> str | None:
    wants_admin = any(promote.values())

    if wants_admin:
        if not bot_can_promote(cid):
            _log("DEBUG_PROMOTE_SKIPPED", chat_id=cid, user_id=target_uid,
                 reason="bot_cannot_promote")
            return None   # soft skip

        available    = get_bot_available_promote_perms(cid)
        safe_promote = {k: v for k, v in promote.items() if k in available or not v}

        _log("DEBUG_PRE_PROMOTE", chat_id=cid, user_id=target_uid,
             requested={k: v for k, v in promote.items() if v},
             safe={k: v for k, v in safe_promote.items() if v})

        try:
            result = bot.promote_chat_member(cid, target_uid, **safe_promote)
            _log("DEBUG_POST_PROMOTE", chat_id=cid, user_id=target_uid,
                 result=repr(result))
            return None
        except Exception as e:
            _log("DEBUG_PROMOTE_ERROR", chat_id=cid, user_id=target_uid, error=str(e))
            return friendly_error(e)

    else:
        # All False → demote silently
        if bot_can_promote(cid):
            _log("DEBUG_PRE_DEMOTE", chat_id=cid, user_id=target_uid)
            try:
                bot.promote_chat_member(cid, target_uid, **_DEMOTE_KWARGS)
                _log("DEBUG_POST_DEMOTE", chat_id=cid, user_id=target_uid, status="ok")
            except Exception as e:
                err = str(e).lower()
                if "chat_admin_required" not in err and "not enough rights" not in err:
                    _log("DEBUG_DEMOTE_IGNORED", chat_id=cid, user_id=target_uid,
                         error=str(e))
        return None


def _verify_applied(cid: int, target_uid: int, promote: dict) -> list[str]:
    """
    Verifies the applied permissions match Telegram's real state.
    Returns a list of mismatched permission keys (empty = all good).
    """
    try:
        member = bot.get_chat_member(cid, target_uid)
        mismatches = []
        for k, expected in promote.items():
            actual = bool(getattr(member, k, False))
            if actual != expected:
                mismatches.append(k)
        if mismatches:
            log_event("perms_apply_mismatch", chat=cid, user=target_uid,
                      mismatches=mismatches)
        return mismatches
    except Exception as e:
        _log("DEBUG_VERIFY_ERROR", chat_id=cid, user_id=target_uid, error=str(e))
        return []


def apply_permissions(cid: int, target_uid: int,
                      promote: dict) -> tuple[bool, str]:
    """
    Applies admin permissions via promoteChatMember, then verifies via get_chat_member.
    Returns (True, "") on success or soft skip.
    Returns (False, msg) on hard API failure.
    """
    _log("DEBUG_APPLY_START", chat_id=cid, user_id=target_uid,
         enabled=[k for k, v in promote.items() if v])

    err = _apply_promote(cid, target_uid, promote)

    if err:
        _log("DEBUG_APPLY_FAILED", chat_id=cid, user_id=target_uid, error=err)
        return False, err

    # Post-apply verification — log mismatches, don't fail on them
    _verify_applied(cid, target_uid, promote)

    _log("DEBUG_APPLY_DONE", chat_id=cid, user_id=target_uid, status="success")
    return True, ""
