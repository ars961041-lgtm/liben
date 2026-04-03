# utils/pagination/router.py
import threading
import time
from core.bot import bot
from .cache import get_cache

# Action handlers
ACTION_HANDLERS = {}

def register_action(name: str):
    def decorator(func):
        ACTION_HANDLERS[name] = func
        return func
    return decorator

# User state
USER_STATE = {}
TEMP_STATE_TIMEOUT = 60

def set_state(user_id, chat_id, state, data=None, precheck=None):
    key = (user_id, chat_id)
    USER_STATE[key] = {"state": state, "data": data or {}, "precheck": precheck}
    def clear_later():
        time.sleep(TEMP_STATE_TIMEOUT)
        USER_STATE.pop(key, None)
    threading.Thread(target=clear_later, daemon=True).start()

def get_state(user_id, chat_id): return USER_STATE.get((user_id, chat_id), {})
def clear_state(user_id, chat_id): USER_STATE.pop((user_id, chat_id), None)
def is_busy(user_id, chat_id): return (user_id, chat_id) in USER_STATE

# Pagination

def paginate_list(items, page=0, per_page=10):
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    start, end = page * per_page, page * per_page + per_page
    return items[start:end], total_pages

# Callback handler
@bot.callback_query_handler(func=lambda call: True)
def handle_buttons(call):
    data = call.data
    if not data.startswith("k:"): return
    key = data.split(":", 1)[1]

    # check if entry exists at all (for expiry vs ownership distinction)
    from .cache import _CACHE, _CACHE_LOCK, CACHE_TTL
    import time
    with _CACHE_LOCK:
        entry = _CACHE.get(key)

    if not entry:
        bot.answer_callback_query(call.id, "⏳ انتهت صلاحية هذا الزر، أعد فتح القائمة.", show_alert=True)
        return

    if time.time() - entry["ts"] > CACHE_TTL:
        bot.answer_callback_query(call.id, "⏳ انتهت صلاحية هذا الزر، أعد فتح القائمة.", show_alert=True)
        return

    # ownership check
    owner = entry.get("owner")
    if owner:
        owner_uid, owner_cid = owner
        if owner_uid != call.from_user.id:
            bot.answer_callback_query(call.id, "❌ هذا الزر ليس لك", show_alert=True)
            return
        if owner_cid is not None and owner_cid != call.message.chat.id:
            bot.answer_callback_query(call.id, "❌ هذا الزر ليس لك", show_alert=True)
            return

    payload = entry["data"]
    action  = payload.get("a")
    extra   = payload.get("d", {})
    handler = ACTION_HANDLERS.get(action)
    if handler:
        handler(call, extra)
    else:
        bot.answer_callback_query(call.id, f"⚠️ لا يوجد إجراء: {action}")