"""
State management for the unified permissions panel.
State shape:
{
    "type": "perms_panel",
    "step": "main" | "await_title",
    "extra": {
        "target_uid":      int,
        "target_name":     str,
        "target_is_admin": bool,
        "promote":         {key: bool},
        "title":           str,
        "mid":             int,
        "page":            int,
    }
}
"""
from core.state_manager import StateManager
from .perms_config import ADMIN_PERMS

STATE_TYPE = "perms_panel"


def _default_promote() -> dict:
    return {k: False for k, _ in ADMIN_PERMS}


def init_state(uid: int, cid: int, target_uid: int, target_name: str,
               target_is_admin: bool, promote: dict = None):
    StateManager.set(uid, cid, {
        "type": STATE_TYPE,
        "step": "main",
        "extra": {
            "target_uid":      target_uid,
            "target_name":     target_name,
            "target_is_admin": target_is_admin,
            "promote":         promote or _default_promote(),
            "title":           "",
            "mid":             None,
            "page":            0,
        },
    }, ttl=600)


def get_extra(uid: int, cid: int) -> dict | None:
    state = StateManager.get(uid, cid)
    if not state or state.get("type") != STATE_TYPE:
        return None
    return state.get("extra") or {}


def set_extra(uid: int, cid: int, **kwargs):
    extra = get_extra(uid, cid)
    if extra is None:
        return
    extra.update(kwargs)
    StateManager.update(uid, cid, {"extra": extra})


def toggle_perm(uid: int, cid: int, key: str):
    extra = get_extra(uid, cid)
    if extra is None:
        return
    perms = extra.get("promote", {})
    perms[key] = not perms.get(key, False)
    set_extra(uid, cid, promote=perms)


def set_step(uid: int, cid: int, step: str):
    StateManager.update(uid, cid, {"step": step})


def get_step(uid: int, cid: int) -> str | None:
    state = StateManager.get(uid, cid)
    return state.get("step") if state else None


def clear(uid: int, cid: int):
    StateManager.clear(uid, cid)
