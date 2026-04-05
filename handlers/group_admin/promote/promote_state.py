"""
State helpers and permission definitions for the promote flow.
State type: "promote"
State shape:
{
    "type": "promote",
    "step": "select" | "await_title",
    "extra": {
        "target_uid": int,
        "target_name": str,
        "perms": {perm_key: bool, ...},   # current toggle state
        "title": str,                      # custom admin title
        "mid": int,                        # message_id of the UI message
        "mode": "promote" | "edit",
    }
}
"""
from core.state_manager import StateManager

# ── Permission definitions ──────────────────────────────────────────────────
PERMISSIONS = [
    ("can_change_info",       "تغيير معلومات المجموعة"),
    ("can_delete_messages",   "حذف الرسائل"),
    ("can_invite_users",      "دعوة المستخدمين"),
    ("can_restrict_members",  "تقييد الأعضاء"),
    ("can_pin_messages",      "تثبيت الرسائل"),
    ("can_promote_members",   "ترقية الأعضاء"),
    ("can_manage_chat",       "إدارة المحادثة"),
    ("can_manage_video_chats","إدارة المكالمات"),
]

DEFAULT_PERMS = {k: False for k, _ in PERMISSIONS}

STATE_TYPE = "promote"


# ── Setters / Getters ────────────────────────────────────────────────────────

def init_promote_state(uid: int, cid: int, target_uid: int, target_name: str,
                       perms: dict = None, mode: str = "promote"):
    StateManager.set(uid, cid, {
        "type": STATE_TYPE,
        "step": "select",
        "extra": {
            "target_uid":  target_uid,
            "target_name": target_name,
            "perms":       perms or dict(DEFAULT_PERMS),
            "title":       "",
            "mid":         None,
            "mode":        mode,
        },
    }, ttl=600)


def get_promote_extra(uid: int, cid: int) -> dict | None:
    state = StateManager.get(uid, cid)
    if not state or state.get("type") != STATE_TYPE:
        return None
    return state.get("extra") or {}


def set_promote_extra(uid: int, cid: int, **kwargs):
    extra = get_promote_extra(uid, cid)
    if extra is None:
        return
    extra.update(kwargs)
    StateManager.update(uid, cid, {"extra": extra})


def toggle_perm(uid: int, cid: int, perm_key: str):
    extra = get_promote_extra(uid, cid)
    if extra is None:
        return
    perms = extra.get("perms", {})
    perms[perm_key] = not perms.get(perm_key, False)
    set_promote_extra(uid, cid, perms=perms)


def set_step(uid: int, cid: int, step: str):
    StateManager.update(uid, cid, {"step": step})


def clear_state(uid: int, cid: int):
    StateManager.clear(uid, cid)
