"""
modules/whispers/whisper_handler.py

نظام الهمسات — Token + Cache + Inline Popup.
بناء الأزرار مفوَّض بالكامل لـ whispers_keyboards.py.
"""

import re
import time
import random
import threading

from core.bot import bot
from utils.helpers import get_bot_username
from utils.pagination.router import register_action
from modules.whispers.whispers_keyboards import (
    build_whisper_group_buttons,
    build_whisper_create_button,
    clickable_name,
)
from database.db_queries.whispers_queries import (
    save_whisper,
    get_whisper,
    mark_whisper_read,
    get_active_members,
    get_user_by_username,
    get_user_by_id_in_group,
    increment_whisper_sender_count,
)

# ══════════════════════════════════════════
# Constants
# ══════════════════════════════════════════

MAX_WHISPER_LENGTH = 200
MAX_ALL_RECIPIENTS = 50
WHISPER_TRIGGERS   = ("همسة", "همس", "whisper")
TOKEN_TTL          = 600   # 10 min — creation window
PENDING_TTL        = 300   # 5 min  — awaiting text
RATE_WINDOW        = 60
RATE_MAX           = 5

# ══════════════════════════════════════════
# In-memory stores (all thread-safe via _lock)
# ══════════════════════════════════════════

_lock = threading.Lock()

# whisper_cache[token] = {from_user, from_name, group_id, targets, target_names,
#                          is_all, created_at}
whisper_cache: dict[str, dict] = {}

# pending_whispers[uid] = {type, token, ...}
pending_whispers: dict[int, dict] = {}

# rate_limit[uid] = [timestamps]
_rate_limit: dict[int, list] = {}

# read_notified: set of (whisper_id, reader_uid) — prevents duplicate sender alerts
_read_notified: set = set()


# ══════════════════════════════════════════
# Token helpers
# ══════════════════════════════════════════

def _make_token(sender_id: int, group_id: int) -> str:
    rand = random.randint(1000000, 9999999)
    return f"{sender_id}-{group_id}-{rand}"


def _store_token(token: str, data: dict):
    with _lock:
        _evict_tokens()
        whisper_cache[token] = {**data, "created_at": time.time()}


def _get_token(token: str) -> dict | None:
    with _lock:
        entry = whisper_cache.get(token)
    if not entry:
        return None
    if time.time() - entry["created_at"] > TOKEN_TTL:
        with _lock:
            whisper_cache.pop(token, None)
        return None
    return entry


def _delete_token(token: str):
    with _lock:
        whisper_cache.pop(token, None)


def _evict_tokens():
    now = time.time()
    dead = [k for k, v in whisper_cache.items()
            if now - v.get("created_at", 0) > TOKEN_TTL]
    for k in dead:
        del whisper_cache[k]


# ══════════════════════════════════════════
# Pending helpers
# ══════════════════════════════════════════

def _set_pending(uid: int, data: dict):
    with _lock:
        pending_whispers[uid] = {**data, "ts": time.time()}


def _get_pending(uid: int) -> dict | None:
    with _lock:
        entry = pending_whispers.get(uid)
    if not entry:
        return None
    if time.time() - entry["ts"] > PENDING_TTL:
        with _lock:
            pending_whispers.pop(uid, None)
        return None
    return entry


def _clear_pending(uid: int):
    with _lock:
        pending_whispers.pop(uid, None)


# ══════════════════════════════════════════
# Rate limiter
# ══════════════════════════════════════════

def _is_rate_limited(uid: int) -> bool:
    now = time.time()
    with _lock:
        ts = [t for t in _rate_limit.get(uid, []) if now - t < RATE_WINDOW]
        if len(ts) >= RATE_MAX:
            _rate_limit[uid] = ts
            return True
        ts.append(now)
        _rate_limit[uid] = ts
    return False


# ══════════════════════════════════════════
# 1. Group command — create token + send button
# ══════════════════════════════════════════

def handle_whisper_command(message) -> bool:
    """
    يُعالج أمر الهمسة في المجموعة.
    ينشئ token ويرسل زر "✉️ كتابة الهمسة" — لا يقبل النص هنا.
    """
    text = (message.text or "").strip()
    if not text:
        return False

    trigger, content = _parse_trigger(text)
    if not trigger:
        return False

    uid = message.from_user.id
    cid = message.chat.id

    # تحقق من تفعيل الهمسات في هذه المجموعة
    from database.db_queries.group_features_queries import is_feature_enabled
    if not is_feature_enabled(cid, "enable_whispers"):
        bot.reply_to(message, "❌ الهمسات معطّلة في هذه المجموعة.")
        return True

    if _is_rate_limited(uid):
        bot.reply_to(message, "⏳ أرسلت همسات كثيرة، انتظر دقيقة ثم حاول مجدداً.")
        return True

    is_all = content.lower().startswith("@all")

    recipients, error = _resolve_recipients(message, content, cid)
    if error:
        bot.reply_to(message, f"⚠️ {error}", parse_mode="HTML")
        return True
    if not recipients:
        bot.reply_to(message, "⚠️ لم يتم العثور على أي مستقبِل صالح.")
        return True

    targets = [r for r in recipients if r["user_id"] != uid]
    if not targets:
        bot.reply_to(message, "⚠️ لا يمكنك إرسال همسة لنفسك.")
        return True

    target_ids   = [r["user_id"] for r in targets]
    target_names = [r.get("name") or f"مستخدم {r['user_id']}" for r in targets]

    token = _make_token(uid, cid)
    _store_token(token, {
        "from_user":    uid,
        "from_name":    _display_name(message.from_user),
        "group_id":     cid,
        "targets":      target_ids,
        "target_names": target_names,
        "is_all":       is_all,
    })

    bot_uname = get_bot_username()
    deep_link = f"https://t.me/{bot_uname}?start=hms{token}"

    # أسماء قابلة للنقر
    sender_link = clickable_name(_display_name(message.from_user), uid)
    names_links = [
        clickable_name(target_names[i], target_ids[i])
        for i in range(min(5, len(target_ids)))
    ]
    names_text = "، ".join(names_links)
    if len(target_ids) > 5:
        names_text += f" و{len(target_ids) - 5} آخرين"

    markup = build_whisper_create_button(deep_link)

    try:
        bot.reply_to(
            message,
            f"💌 <b>همسة جديدة</b>\n"
            f"👤 من: {sender_link}\n"
            f"👥 إلى: {names_text}\n"
            f"🔒 المحتوى مخفي",
            parse_mode="HTML",
            reply_markup=markup,
        )
        print(f"[WHISPER] token={token} is_all={is_all} targets={target_ids}")
    except Exception as e:
        print(f"[WHISPER] group send error: {e}")

    return True


# ══════════════════════════════════════════
# 2. /start hms<TOKEN> — open private, await text
# ══════════════════════════════════════════

def handle_hms_start(message, token: str):
    """يُعالج /start hms<TOKEN>: يتحقق من الـ token ويطلب النص."""
    uid  = message.from_user.id
    data = _get_token(token)

    if not data:
        bot.send_message(uid, "❌ انتهت صلاحية طلب الهمسة. اطلب من المُرسِل إعادة المحاولة.")
        return

    if data["from_user"] != uid:
        bot.send_message(uid, "🚫 هذا الرابط ليس لك.")
        return

    _set_pending(uid, {"type": "create", "token": token})

    bot.send_message(
        uid,
        "✍️ <b>أرسل الآن نص الهمسة</b>\n\n"
        f"📏 الحد الأقصى: {MAX_WHISPER_LENGTH} حرف\n"
        "📝 نص فقط (لا صور أو ملفات)",
        parse_mode="HTML",
    )
    print(f"[WHISPER] ✅ awaiting text from uid={uid}")


# ══════════════════════════════════════════
# 3. /start hmrp<id> — reply to whisper
# ══════════════════════════════════════════

def handle_hmrp_start(message, whisper_id_str: str):
    """
    يُعالج /start hmrp<id> في الخاص.

    إذا كانت الحالة محفوظة مسبقاً (من on_wsp_reply) → يطلب النص مباشرة.
    إذا لم تكن (دخول مباشر للرابط) → يتحقق من DB ويحفظ الحالة ثم يطلب النص.
    في كلتا الحالتين: نقرة واحدة → طلب النص فوراً.
    """
    uid = message.from_user.id

    # فحص إذا كانت الحالة محفوظة مسبقاً من on_wsp_reply
    existing = _get_pending(uid)
    if existing and existing.get("type") == "reply":
        from utils.html_sanitizer import escape_html, safe_send_message
        from_name = existing.get("from_name", "مستخدم")
        safe_from_name = escape_html(from_name)
        safe_send_message(
            uid,
            f"↩️ <b>رد على همسة من {safe_from_name}</b>\n\n"
            f"اكتب ردك على الهمسة الآن\n"
            f"📏 الحد الأقصى: {MAX_WHISPER_LENGTH} حرف",
            parse_mode="HTML",
        )
        return

    # دخول مباشر — تحقق من DB وأنشئ الحالة
    try:
        whisper_id = int(whisper_id_str)
    except ValueError:
        bot.send_message(uid, "❌ معرّف الهمسة غير صالح.")
        return

    whisper = get_whisper(whisper_id)
    if not whisper:
        bot.send_message(uid, "⏳ هذه الهمسة انتهت صلاحيتها أو حُذفت.")
        return

    if whisper["to_user"] != uid:
        bot.send_message(uid, "🚫 لا يمكنك الرد على هذه الهمسة.")
        return

    from_name = whisper["from_name"] or f"مستخدم {whisper['from_user']}"

    _set_pending(uid, {
        "type":        "reply",
        "original_id": whisper_id,
        "to_user":     whisper["from_user"],
        "group_id":    whisper["group_id"],
        "from_name":   from_name,
    })

    from utils.html_sanitizer import escape_html, safe_send_message
    safe_from_name = escape_html(from_name)
    safe_send_message(
        uid,
        f"↩️ <b>رد على همسة من {safe_from_name}</b>\n\n"
        f"اكتب ردك على الهمسة الآن\n"
        f"📏 الحد الأقصى: {MAX_WHISPER_LENGTH} حرف",
        parse_mode="HTML",
    )


# ══════════════════════════════════════════
# 4. Private input handler (awaiting text)
# ══════════════════════════════════════════

def handle_whisper_private_input(message) -> bool:
    """
    يُعالج الرسائل في الخاص عندما يكون المستخدم في حالة انتظار.
    يرجع True إذا تم التعامل مع الرسالة.
    """
    uid     = message.from_user.id
    pending = _get_pending(uid)
    if not pending:
        return False

    ptype = pending.get("type")
    if ptype == "create":
        _process_whisper_text(message, pending)
        return True
    if ptype == "reply":
        _process_reply_text(message, pending)
        return True

    return False


def _process_whisper_text(message, pending: dict):
    """يحفظ نص الهمسة ويرسل إشعار المجموعة."""
    uid = message.from_user.id

    if not message.text or message.text.startswith("/"):
        bot.send_message(uid, "⚠️ يُقبل النص فقط. أرسل نص الهمسة:")
        return

    text = message.text.strip()
    if len(text) > MAX_WHISPER_LENGTH:
        bot.send_message(uid,
            f"⚠️ النص طويل جداً ({len(text)}/{MAX_WHISPER_LENGTH} حرف).\nأرسل نصاً أقصر:")
        return

    token = pending.get("token")
    data  = _get_token(token) if token else None
    if not data:
        bot.send_message(uid, "❌ انتهت صلاحية الطلب. اطلب من المُرسِل إعادة المحاولة.")
        _clear_pending(uid)
        return

    # مسح الحالة فوراً
    _clear_pending(uid)
    _delete_token(token)

    group_id    = data["group_id"]
    target_ids  = data["targets"]
    is_all      = data.get("is_all", False)
    sender_name = data["from_name"]

    if is_all:
        # همسة عامة — صف واحد في DB، to_user=None
        wid = save_whisper(uid, None, group_id, text)
        if not wid:
            bot.send_message(uid, "⚠️ لم يتم إرسال الهمسة.")
            return
        increment_whisper_sender_count(uid, group_id)
        bot.send_message(
            uid,
            "✅ <b>تم إرسال الهمسة للجميع</b>",
            parse_mode="HTML",
        )
        _send_group_notification(uid, sender_name, group_id, [], {None: wid}, is_all=True)
    else:
        # همسة خاصة — صف لكل مستقبِل
        saved_to    = []
        whisper_ids = {}

        for r_uid in target_ids:
            if r_uid == uid:
                continue
            wid = save_whisper(uid, r_uid, group_id, text)
            if wid:
                saved_to.append(r_uid)
                whisper_ids[r_uid] = wid

        if not saved_to:
            bot.send_message(uid, "⚠️ لم يتم إرسال أي همسة.")
            return

        increment_whisper_sender_count(uid, group_id)
        bot.send_message(
            uid,
            f"✅ <b>تم إرسال الهمسة بنجاح</b>\n👥 عدد المستلمين: {len(saved_to)}",
            parse_mode="HTML",
        )
        _send_group_notification(uid, sender_name, group_id, saved_to, whisper_ids, is_all=False)


def _process_reply_text(message, pending: dict):
    """
    يحفظ نص الرد ويرسل همسة جديدة في المجموعة من المستقبِل إلى المُرسِل الأصلي.
    الرد يعود للمجموعة — البوت وسيط فقط.
    """
    uid = message.from_user.id

    if not message.text or message.text.startswith("/"):
        bot.send_message(uid, "⚠️ يُقبل النص فقط. أرسل نص الرد:")
        return

    text = message.text.strip()
    if len(text) > MAX_WHISPER_LENGTH:
        bot.send_message(uid,
            f"⚠️ النص طويل جداً ({len(text)}/{MAX_WHISPER_LENGTH} حرف).\nأرسل نصاً أقصر:")
        return

    original_id = pending.get("original_id")
    to_user     = pending.get("to_user")     # المُرسِل الأصلي
    group_id    = pending.get("group_id")
    from_name   = pending.get("from_name", "مستخدم")

    _clear_pending(uid)

    # حفظ الرد كهمسة جديدة
    wid = save_whisper(uid, to_user, group_id, text, reply_to=original_id)
    if not wid:
        bot.send_message(uid, "❌ فشل حفظ الرد. حاول مجدداً.")
        return

    bot.send_message(uid, "✅ <b>تم إرسال ردك</b>", parse_mode="HTML")

    # ── إرسال إشعار الرد في المجموعة (نفس المجموعة الأصلية) ──
    replier_name = _display_name(message.from_user)
    whisper_ids  = {to_user: wid}

    _send_group_notification(
        sender_id    = uid,
        sender_name  = replier_name,
        group_id     = group_id,
        recipient_ids= [to_user],
        whisper_ids  = whisper_ids,
        is_all       = False,
    )


# ══════════════════════════════════════════
# 5. Group notification with inline popup buttons
# ══════════════════════════════════════════

def _send_group_notification(sender_id: int, sender_name: str, group_id: int,
                              recipient_ids: list, whisper_ids: dict, is_all: bool):
    """
    يرسل إشعار المجموعة بعد إرسال الهمسة.

    @all  → whisper_ids = {None: wid}، names_text = "الجميع"
    خاصة → whisper_ids = {r_uid: wid, ...}
    """
    if is_all:
        names_text = "الجميع 👥"
    else:
        names = []
        for r_uid in recipient_ids:
            wid = whisper_ids.get(r_uid)
            if not wid:
                continue
            w      = get_whisper(wid)
            r_name = (w["to_name"] if w else None) or f"مستخدم {r_uid}"
            names.append(clickable_name(r_name, r_uid))
        if not names:
            return
        names_text = "، ".join(names[:5])
        if len(names) > 5:
            names_text += f" و{len(names) - 5} آخرين"

    sender_link = clickable_name(sender_name, sender_id)
    markup      = build_whisper_group_buttons(sender_id, group_id, whisper_ids, is_all)

    try:
        bot.send_message(
            group_id,
            f"💌 <b>همسة جديدة</b>\n"
            f"👤 من: {sender_link}\n"
            f"👥 إلى: {names_text}\n"
            f"🔒 المحتوى مخفي",
            parse_mode="HTML",
            reply_markup=markup,
        )
    except Exception as e:
        print(f"[WHISPER] group notification error: {e}")


# ══════════════════════════════════════════
# 6. Callback: wsp_view — inline popup
# ══════════════════════════════════════════

@register_action("wsp_view")
def on_wsp_view(call, data: dict):
    """
    يُعالج ضغط زر "🔐 عرض الهمسة".
    التحقق من الصلاحية يتم من DB مباشرة — لا owner في الكاش.
    يعرض الهمسة الصحيحة لكل مستخدم بناءً على wids map.
    """
    uid    = call.from_user.id
    is_all = bool(data.get("is_all", 0))
    sid    = data.get("sid")          # sender_id
    wids   = data.get("wids", {})     # {str(r_uid): wid}
    wid    = data.get("wid")          # fallback للهمسة الأولى

    # تحديد الـ wid الصحيح لهذا المستخدم
    # wids مخزنة بـ str keys (JSON)
    user_wid = wids.get(str(uid)) or wids.get(uid)

    # إذا لم يجد همسة خاصة به، استخدم الـ wid الأول (للمُرسِل أو @all)
    target_wid = user_wid or wid

    if not target_wid:
        bot.answer_callback_query(call.id, "⚠️ همسة غير صالحة.", show_alert=True)
        return

    whisper = get_whisper(target_wid)
    if not whisper:
        bot.answer_callback_query(call.id, "⏳ انتهت صلاحية هذه الهمسة.", show_alert=True)
        return

    # ── التحقق من الصلاحية من DB ──
    # to_user IS NULL → همسة عامة (@all) → الجميع يقرأ
    # to_user NOT NULL → خاصة → فقط المُرسِل أو المُستقبِل
    if whisper["to_user"] is not None and not is_all:
        allowed = (uid == whisper["to_user"]) or (uid == whisper["from_user"])
        if not allowed:
            bot.answer_callback_query(call.id, "🚫 هذه الهمسة ليست لك.", show_alert=True)
            return

    from_name  = whisper["from_name"] or f"مستخدم {whisper['from_user']}"
    # alert_text = f"📩 همسة من {from_name}\n{'─' * 20}\n{whisper['message']}"
    alert_text = f"{whisper['message']}"

    bot.answer_callback_query(call.id, alert_text, show_alert=True)

    if not whisper["is_read"]:
        mark_whisper_read(target_wid)

    # إشعار المُرسِل عند أول قراءة (خاصة فقط)
    if not is_all and uid != whisper["from_user"]:
        _notify_sender_on_read(whisper["from_user"], uid, target_wid)


@register_action("wsp_reply")
def on_wsp_reply(call, data: dict):
    """
    يُعالج ضغط زر "↩️ الرد على الهمسة".

    التدفق المُحسَّن (نقرة واحدة):
      1. يتحقق من الصلاحية من DB
      2. يحفظ الحالة في pending_whispers فوراً
      3. يُجيب بـ show_alert يحتوي رابط مباشر لفتح الخاص
         → المستخدم يضغط الرابط → يفتح الخاص → handle_hmrp_start يجد الحالة جاهزة
            ويطلب النص مباشرة بدون خطوات إضافية
    """
    uid  = call.from_user.id
    wids = data.get("wids", {})
    gid  = data.get("gid")

    user_wid = wids.get(str(uid)) or wids.get(uid)

    if not user_wid:
        bot.answer_callback_query(call.id, "🚫 لا يمكنك الرد على هذه الهمسة.", show_alert=True)
        return

    whisper = get_whisper(user_wid)
    if not whisper:
        bot.answer_callback_query(call.id, "⏳ انتهت صلاحية هذه الهمسة.", show_alert=True)
        return

    if whisper["to_user"] != uid:
        bot.answer_callback_query(call.id, "🚫 لا يمكنك الرد على هذه الهمسة.", show_alert=True)
        return

    from_name = whisper["from_name"] or f"مستخدم {whisper['from_user']}"

    # حفظ الحالة فوراً — handle_hmrp_start سيجدها جاهزة
    _set_pending(uid, {
        "type":        "reply",
        "original_id": user_wid,
        "to_user":     whisper["from_user"],
        "group_id":    whisper["group_id"],
        "from_name":   from_name,
    })

    # رابط مباشر — نقرة واحدة تفتح الخاص وتبدأ الرد فوراً
    bot_uname = get_bot_username()
    deep_link = f"https://t.me/{bot_uname}?start=hmrp{user_wid}"
    bot.answer_callback_query(
        call.id,
        f"↩️ اضغط هنا للرد على همسة {from_name}",
        show_alert=True,
        url=deep_link,
    )


# ══════════════════════════════════════════
# Sender read notification
# ══════════════════════════════════════════

def _notify_sender_on_read(sender_id: int, reader_id: int, whisper_id: int):
    """
    يُشعر المُرسِل عند أول قراءة للهمسة.
    يتجنب الإشعارات المكررة.
    """
    key = (whisper_id, reader_id)
    with _lock:
        if key in _read_notified:
            return
        _read_notified.add(key)

    # جلب اسم القارئ
    try:
        reader_chat = bot.get_chat(reader_id)
        reader_name = (reader_chat.first_name or "") + (
            " " + reader_chat.last_name if reader_chat.last_name else ""
        )
        reader_name = reader_name.strip() or f"مستخدم {reader_id}"
    except Exception:
        reader_name = f"مستخدم {reader_id}"

    try:
        bot.send_message(
            sender_id,
            f"📩 <b>تم فتح همستك</b>\n👤 بواسطة: {reader_name}",
            parse_mode="HTML",
        )
    except Exception:
        pass  # المُرسِل لم يبدأ محادثة مع البوت


# ══════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════

def _parse_trigger(text: str) -> tuple:
    lower = text.lower()
    for t in WHISPER_TRIGGERS:
        if lower.startswith(t):
            return t, text[len(t):].strip()
    return None, ""


def _resolve_recipients(message, content: str, cid: int) -> tuple:
    """يحدد المستقبِلين من محتوى الرسالة."""

    # رد على رسالة
    if message.reply_to_message and message.reply_to_message.from_user:
        u = message.reply_to_message.from_user
        if u.is_bot:
            return [], "لا يمكن إرسال همسة للبوت."
        return [{"user_id": u.id, "name": _display_name(u)}], None

    # @all
    if content.lower().startswith("@all"):
        members   = get_active_members(cid, limit=MAX_ALL_RECIPIENTS)
        sender_id = message.from_user.id
        members   = [m for m in members if m["user_id"] != sender_id]
        if not members:
            return [], "لا يوجد أعضاء نشطون آخرون في المجموعة."
        return members, None

    # user_id رقمي
    parts = content.split()
    if parts and parts[0].isdigit():
        u = get_user_by_id_in_group(int(parts[0]), cid)
        if not u:
            return [], f"المستخدم {parts[0]} غير موجود أو غير نشط."
        return [u], None

    # @username
    mentions = re.findall(r"@(\w+)", content)
    if mentions:
        found, missing = [], []
        for uname in mentions:
            u = get_user_by_username(uname, cid)
            if u:
                found.append(u)
            else:
                missing.append(f"@{uname}")
        if not found:
            return [], f"المستخدمون غير موجودين: {', '.join(missing)}"
        return found, None

    return [], "حدد المستقبِل: رد على رسالة، أو @username، أو user_id، أو @all."


def _display_name(user) -> str:
    first = getattr(user, "first_name", "") or ""
    last  = getattr(user, "last_name",  "") or ""
    return (first + " " + last).strip() or f"مستخدم {user.id}"
