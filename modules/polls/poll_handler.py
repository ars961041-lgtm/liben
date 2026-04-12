"""
نظام التصويت المتقدم — Advanced Poll Engine
- Race-condition safe voting (per-poll lock + BEGIN IMMEDIATE)
- Auto-close via scheduler (no threading.Timer)
- Configurable vote-change limits + lock-before-end
- Batched message updates under high traffic
- show_voters support
- Improved progress bar UI
"""
import time
import threading

from core.bot import bot
from core.state_manager import StateManager
from utils.pagination import btn, send_ui, edit_ui, register_action
from utils.pagination.buttons import build_keyboard
from utils.helpers import get_lines
from database.db_queries.polls_queries import (
    create_poll, add_poll_option, set_poll_message_id,
    get_poll, get_poll_by_message, get_poll_options,
    get_user_vote, get_total_votes, get_option_voters,
    cast_vote, close_poll, reopen_poll, delete_poll, extend_poll_time,
    get_latest_poll_by_creator,
)

_STATE       = "poll_creator"
_TTL         = 900   # 15 دقيقة
_MAX_OPTIONS = 10

# ── Batched update: تأخير 2 ثانية قبل تحديث الرسالة تحت الحمل العالي ──
_pending_updates: dict[int, float] = {}   # poll_id -> scheduled_at
_update_lock = threading.Lock()
_UPDATE_DELAY = 2.0   # ثانيتان

_DURATION_OPTIONS = [
    ("5 دقائق",  5   * 60),
    ("30 دقيقة", 30  * 60),
    ("ساعة",     60  * 60),
    ("6 ساعات",  6   * 3600),
    ("24 ساعة",  24  * 3600),
    ("بلا حد",   0),
]

_EXTEND_OPTIONS = [
    ("30 دقيقة", 30 * 60),
    ("ساعة",     60 * 60),
    ("6 ساعات",  6  * 3600),
    ("24 ساعة",  24 * 3600),
]


# ══════════════════════════════════════════
# نقطة الدخول
# ══════════════════════════════════════════

def open_poll_creator(message):
    uid = message.from_user.id
    cid = message.chat.id

    StateManager.set(uid, cid, {
        "type":  _STATE,
        "step":  "await_target_id",
        "extra": {
            "target": None, "target_type": "group",
            "question": None,
            "q_media_id": None, "q_media_type": None,
            "description": None,
            "desc_media_id": None, "desc_media_type": None,
            "options": [],
            "poll_type": "normal",
            "allow_change": True,
            "max_vote_changes": 0,
            "lock_before_end": 0,
            "is_hidden": False,
            "show_voters": False,
            "duration": 0,
        },
    }, ttl=_TTL)

    owner = (uid, cid)
    text = (
        f"📊 <b>إنشاء تصويت متقدم</b>\n{get_lines()}\n\n"
        "📍 <b>الخطوة 1 — أين تريد نشر التصويت؟</b>\n\n"
        "• اضغط <b>هذه المحادثة</b> للنشر هنا\n"
        "• أو أرسل معرّف القناة/المجموعة\n"
        "  مثال: <code>-1002121901488</code>"
    )
    buttons = [
        btn("📍 هذه المحادثة", "poll_use_current", {}, owner=owner, color="p"),
        btn("❌ إلغاء",        "poll_cancel",       {}, owner=owner, color="d"),
    ]
    msg = send_ui(cid, text=text, buttons=buttons, layout=[1, 1],
                  owner_id=uid, reply_to=message.message_id)
    if msg:
        StateManager.set_mid(uid, cid, msg.message_id)


# ══════════════════════════════════════════
# Callbacks — wizard
# ══════════════════════════════════════════

@register_action("poll_use_current")
def on_use_current(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not StateManager.is_state(uid, cid, _STATE):
        bot.answer_callback_query(call.id); return
    bot.answer_callback_query(call.id)
    _set_extra(uid, cid, target=cid)
    StateManager.update(uid, cid, {"step": "await_poll_type"})
    _panel(uid, cid, call=call)


@register_action("poll_back_target")
def on_back_target(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not StateManager.is_state(uid, cid, _STATE):
        bot.answer_callback_query(call.id); return
    bot.answer_callback_query(call.id)
    _set_extra(uid, cid, target=None)
    StateManager.update(uid, cid, {"step": "await_target_id"})
    _panel(uid, cid, call=call)


@register_action("poll_target_type")
def on_target_type(call, data):
    # kept for backward-compat with any in-flight sessions
    uid = call.from_user.id
    cid = call.message.chat.id
    if not StateManager.is_state(uid, cid, _STATE):
        bot.answer_callback_query(call.id); return
    bot.answer_callback_query(call.id)
    _set_extra(uid, cid, target_type=data.get("t", "group"))
    StateManager.update(uid, cid, {"step": "await_target_id"})
    _panel(uid, cid, call=call)


@register_action("poll_type_select")
def on_poll_type(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not StateManager.is_state(uid, cid, _STATE):
        bot.answer_callback_query(call.id); return
    bot.answer_callback_query(call.id)
    _set_extra(uid, cid, poll_type=data.get("pt", "normal"))
    StateManager.update(uid, cid, {"step": "await_question"})
    _panel(uid, cid, call=call)


@register_action("poll_q_media_skip")
def on_q_media_skip(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not StateManager.is_state(uid, cid, _STATE):
        bot.answer_callback_query(call.id); return
    bot.answer_callback_query(call.id)
    StateManager.update(uid, cid, {"step": "await_description"})
    _panel(uid, cid, call=call)


@register_action("poll_desc_skip")
def on_desc_skip(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not StateManager.is_state(uid, cid, _STATE):
        bot.answer_callback_query(call.id); return
    bot.answer_callback_query(call.id)
    StateManager.update(uid, cid, {"step": "await_options"})
    _panel(uid, cid, call=call)


@register_action("poll_option_done")
def on_option_done(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not StateManager.is_state(uid, cid, _STATE):
        bot.answer_callback_query(call.id); return
    extra = StateManager.get_extra(uid, cid)
    if len(extra.get("options", [])) < 2:
        bot.answer_callback_query(call.id, "⚠️ أضف خيارين على الأقل!", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    StateManager.update(uid, cid, {"step": "await_settings"})
    _panel(uid, cid, call=call)


_COLOR_LABELS = [
    ("🔵 أزرق",  "p"),
    ("🟢 أخضر",  "su"),
    ("🔴 أحمر",  "d"),
    ("⚪ افتراضي", "de"),
]


def _ask_option_color(uid, cid):
    mid   = StateManager.get_mid(uid, cid)
    owner = (uid, cid)
    extra = StateManager.get_extra(uid, cid)
    text  = (
        f"📊 <b>إنشاء تصويت</b>  ·  لون الخيار\n\n"
        f"✏️ <b>الخيار:</b> {extra.get('_pending_opt', '')}\n\n"
        "اختر لون الزر:"
    )
    buttons = [
        btn(label, "poll_opt_color", {"c": color}, owner=owner, color=color)
        for label, color in _COLOR_LABELS
    ]
    markup = build_keyboard(buttons, [2, 2], uid)
    _edit_or_send(cid, mid, text, markup, uid)


@register_action("poll_opt_color")
def on_opt_color(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    if not StateManager.is_state(uid, cid, _STATE):
        bot.answer_callback_query(call.id); return
    bot.answer_callback_query(call.id)

    color = data.get("c", "p")
    extra = StateManager.get_extra(uid, cid)
    opts  = extra.get("options", [])
    text  = extra.get("_pending_opt", "")

    if not text:
        StateManager.update(uid, cid, {"step": "await_options"})
        _panel(uid, cid, call=call)
        return

    opts.append({"text": text, "color": color})
    _set_extra(uid, cid, options=opts, _pending_opt=None)
    StateManager.update(uid, cid, {"step": "await_options"})
    _panel(uid, cid, call=call)


@register_action("poll_setting")
def on_setting(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not StateManager.is_state(uid, cid, _STATE):
        bot.answer_callback_query(call.id); return
    bot.answer_callback_query(call.id)
    key = data.get("k")
    val = data.get("v")
    # boolean toggles
    if isinstance(val, str) and val in ("0", "1"):
        val = bool(int(val))
    _set_extra(uid, cid, **{key: val})
    _panel(uid, cid, call=call)


@register_action("poll_duration")
def on_duration(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not StateManager.is_state(uid, cid, _STATE):
        bot.answer_callback_query(call.id); return
    bot.answer_callback_query(call.id)
    _set_extra(uid, cid, duration=int(data.get("d", 0)))
    _panel(uid, cid, call=call)


@register_action("poll_publish")
def on_publish(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not StateManager.is_state(uid, cid, _STATE):
        bot.answer_callback_query(call.id); return

    extra    = StateManager.get_extra(uid, cid)
    target   = extra.get("target")
    question = extra.get("question", "")
    options  = extra.get("options", [])

    if not target or not question or len(options) < 2:
        bot.answer_callback_query(call.id, "❌ البيانات غير مكتملة.", show_alert=True)
        return

    duration = extra.get("duration", 0)
    end_time = int(time.time()) + duration if duration else None

    poll_id = create_poll(
        chat_id=target, question=question,
        poll_type=extra.get("poll_type", "normal"),
        allow_change=extra.get("allow_change", True),
        is_hidden=extra.get("is_hidden", False),
        created_by=uid,
        question_media_id=extra.get("q_media_id"),
        question_media_type=extra.get("q_media_type"),
        description=extra.get("description"),
        description_media_id=extra.get("desc_media_id"),
        description_media_type=extra.get("desc_media_type"),
        end_time=end_time,
        max_vote_changes=extra.get("max_vote_changes", 0),
        lock_before_end=extra.get("lock_before_end", 0),
        show_voters=extra.get("show_voters", False),
    )
    if not poll_id:
        bot.answer_callback_query(call.id, "❌ فشل إنشاء التصويت.", show_alert=True)
        return

    for opt in options:
        add_poll_option(poll_id, opt["text"], opt.get("color", "p"))

    poll_data = get_poll(poll_id)
    poll_opts = get_poll_options(poll_id)
    text, markup = _build_poll_message(poll_id, poll_data, poll_opts)

    try:
        q_mid = extra.get("q_media_id")
        q_mtp = extra.get("q_media_type")
        if q_mid and q_mtp:
            sent = _send_media(target, q_mid, q_mtp, text, markup)
        else:
            sent = bot.send_message(target, text, parse_mode="HTML", reply_markup=markup)

        if sent:
            set_poll_message_id(poll_id, sent.message_id)

        StateManager.clear(uid, cid)
        bot.answer_callback_query(call.id, "✅ تم نشر التصويت!", show_alert=True)
        _send_creator_panel(cid, uid, poll_id, call.message.message_id)

    except Exception as e:
        err = str(e).lower()
        if "chat not found" in err or "invalid" in err:
            msg = "❌ تعذّر الوصول للوجهة، تأكد من المعرّف أو أن البوت موجود هناك."
        elif "not enough rights" in err or "have no rights" in err:
            msg = "❌ البوت لا يملك صلاحية النشر في هذه الوجهة.\nتأكد أن البوت مشرف بصلاحية نشر الرسائل."
        elif "bot was blocked" in err or "user is deactivated" in err:
            msg = "❌ تعذّر الإرسال — المستخدم حجب البوت أو الحساب غير نشط."
        else:
            msg = "❌ فشل النشر، حاول مجدداً."
        print(f"[poll.on_publish] uid={uid} target={target} error={e}")
        bot.answer_callback_query(call.id, msg, show_alert=True)


@register_action("poll_cancel")
def on_cancel(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    bot.answer_callback_query(call.id)
    StateManager.clear(uid, cid)
    try:
        bot.edit_message_text("❌ <b>تم إلغاء إنشاء التصويت.</b>",
                              cid, call.message.message_id,
                              parse_mode="HTML", reply_markup=None)
    except Exception:
        pass


# ══════════════════════════════════════════
# Callback — التصويت الفعلي (batched updates)
# ══════════════════════════════════════════

@register_action("poll_vote")
def on_vote(call, data):
    uid       = call.from_user.id
    poll_id   = int(data.get("pid", 0))
    option_id = int(data.get("oid", 0))

    if not poll_id or not option_id:
        bot.answer_callback_query(call.id, "❌ بيانات غير صحيحة.", show_alert=True)
        return

    ok, reason = cast_vote(poll_id, uid, option_id)

    if not ok:
        msgs = {
            "closed":        "🔒 التصويت مغلق.",
            "no_change":     "⚠️ لا يمكن تغيير صوتك في هذا التصويت.",
            "change_limit":  "⚠️ وصلت للحد الأقصى لتغيير الصوت.",
            "locked":        "⏳ لا يمكن تغيير الصوت قبل انتهاء التصويت.",
            "invalid_option":"❌ خيار غير صالح.",
            "not_found":     "❌ التصويت غير موجود.",
            "error":         "❌ حدث خطأ، حاول مجدداً.",
        }
        bot.answer_callback_query(call.id, msgs.get(reason, "❌ خطأ."), show_alert=True)
        return

    if reason == "same":
        bot.answer_callback_query(call.id, "✅ صوتك مسجّل بالفعل لهذا الخيار.")
        return

    feedback = "✅ تم تسجيل صوتك!" if reason == "new" else "🔄 تم تغيير صوتك!"
    bot.answer_callback_query(call.id, feedback)

    # Batched update: جدوِل تحديث الرسالة بعد _UPDATE_DELAY ثانية
    _schedule_message_update(call.message, poll_id)


def _schedule_message_update(msg, poll_id: int):
    """
    يُجدوِل تحديث رسالة التصويت بعد تأخير قصير.
    إذا وصلت أصوات متعددة في نفس الوقت، يُرسَل تحديث واحد فقط.
    """
    now = time.time()
    with _update_lock:
        already_scheduled = poll_id in _pending_updates
        _pending_updates[poll_id] = now

    if not already_scheduled:
        def _do_update():
            time.sleep(_UPDATE_DELAY)
            with _update_lock:
                _pending_updates.pop(poll_id, None)
            _refresh_poll_message(msg, poll_id)

        threading.Thread(target=_do_update, daemon=True).start()


# ══════════════════════════════════════════
# Callbacks — لوحة تحكم المنشئ
# ══════════════════════════════════════════

@register_action("poll_admin_stop")
def on_admin_stop(call, data):
    uid     = call.from_user.id
    poll_id = int(data.get("pid", 0))
    poll    = get_poll(poll_id)
    if not poll or poll["created_by"] != uid:
        bot.answer_callback_query(call.id, "❌ غير مصرح.", show_alert=True); return
    close_poll(poll_id)
    bot.answer_callback_query(call.id, "🔒 تم إيقاف التصويت.")
    _refresh_poll_in_chat(get_poll(poll_id))
    _edit_creator_panel(call, poll_id)


@register_action("poll_admin_reopen")
def on_admin_reopen(call, data):
    uid     = call.from_user.id
    poll_id = int(data.get("pid", 0))
    poll    = get_poll(poll_id)
    if not poll or poll["created_by"] != uid:
        bot.answer_callback_query(call.id, "❌ غير مصرح.", show_alert=True); return
    reopen_poll(poll_id)
    bot.answer_callback_query(call.id, "🔓 تم إعادة فتح التصويت.")
    _refresh_poll_in_chat(get_poll(poll_id))
    _edit_creator_panel(call, poll_id)


@register_action("poll_admin_delete")
def on_admin_delete(call, data):
    uid     = call.from_user.id
    poll_id = int(data.get("pid", 0))
    poll    = get_poll(poll_id)
    if not poll or poll["created_by"] != uid:
        bot.answer_callback_query(call.id, "❌ غير مصرح.", show_alert=True); return
    if poll.get("message_id"):
        try:
            bot.delete_message(poll["chat_id"], poll["message_id"])
        except Exception:
            pass
    delete_poll(poll_id)
    bot.answer_callback_query(call.id, "🗑 تم حذف التصويت.")
    try:
        bot.edit_message_text("🗑 <b>تم حذف التصويت.</b>",
                              call.message.chat.id, call.message.message_id,
                              parse_mode="HTML", reply_markup=None)
    except Exception:
        pass


@register_action("poll_admin_extend")
def on_admin_extend(call, data):
    uid     = call.from_user.id
    cid     = call.message.chat.id
    poll_id = int(data.get("pid", 0))
    poll    = get_poll(poll_id)
    if not poll or poll["created_by"] != uid:
        bot.answer_callback_query(call.id, "❌ غير مصرح.", show_alert=True); return
    bot.answer_callback_query(call.id)
    owner   = (uid, cid)
    buttons = [
        btn(label, "poll_admin_do_extend", {"pid": poll_id, "s": secs}, owner=owner, color="p")
        for label, secs in _EXTEND_OPTIONS
    ]
    buttons.append(btn("🔙 رجوع", "poll_admin_panel", {"pid": poll_id}, owner=owner, color="d"))
    markup = build_keyboard(buttons, [2, 2, 1], uid)
    try:
        bot.edit_message_text(
            f"⏳ <b>تمديد التصويت #{poll_id}</b>\n{get_lines()}\n\nاختر مدة التمديد:",
            cid, call.message.message_id, parse_mode="HTML", reply_markup=markup,
        )
    except Exception:
        pass


@register_action("poll_admin_do_extend")
def on_admin_do_extend(call, data):
    uid     = call.from_user.id
    poll_id = int(data.get("pid", 0))
    secs    = int(data.get("s", 3600))
    poll    = get_poll(poll_id)
    if not poll or poll["created_by"] != uid:
        bot.answer_callback_query(call.id, "❌ غير مصرح.", show_alert=True); return
    extend_poll_time(poll_id, secs)
    bot.answer_callback_query(call.id, "⏳ تم تمديد التصويت.")
    _refresh_poll_in_chat(get_poll(poll_id))
    _edit_creator_panel(call, poll_id)


@register_action("poll_admin_stats")
def on_admin_stats(call, data):
    uid     = call.from_user.id
    poll_id = int(data.get("pid", 0))
    poll    = get_poll(poll_id)
    if not poll or poll["created_by"] != uid:
        bot.answer_callback_query(call.id, "❌ غير مصرح.", show_alert=True); return
    bot.answer_callback_query(call.id)
    cid     = call.message.chat.id
    owner   = (uid, cid)
    text    = _build_stats_text(poll_id, poll, show_voters=True)
    buttons = [btn("🔙 رجوع", "poll_admin_panel", {"pid": poll_id}, owner=owner, color="d")]
    markup  = build_keyboard(buttons, [1], uid)
    try:
        bot.edit_message_text(text, cid, call.message.message_id,
                              parse_mode="HTML", reply_markup=markup)
    except Exception:
        pass


@register_action("poll_admin_panel")
def on_admin_panel(call, data):
    uid     = call.from_user.id
    poll_id = int(data.get("pid", 0))
    poll    = get_poll(poll_id)
    if not poll or poll["created_by"] != uid:
        bot.answer_callback_query(call.id, "❌ غير مصرح.", show_alert=True); return
    bot.answer_callback_query(call.id)
    _edit_creator_panel(call, poll_id)


# ══════════════════════════════════════════
# Panel renderer (wizard)
# ══════════════════════════════════════════

def _panel(uid, cid, call=None):
    state = StateManager.get(uid, cid)
    if not state:
        return
    step  = state.get("step", "")
    extra = state.get("extra", {})
    owner = (uid, cid)
    mid   = StateManager.get_mid(uid, cid)

    target_type  = extra.get("target_type", "group")
    target_label = "📢 قناة" if target_type == "channel" else "👥 مجموعة"

    if step == "await_target_id":
        text = (
            f"📊 <b>إنشاء تصويت</b>  ·  الخطوة 1\n{get_lines()}\n\n"
            "📍 أرسل معرّف القناة/المجموعة أو اختر من الزر:\n"
            "مثال: <code>-1002121901488</code>"
        )
        buttons = [
            btn("📍 هذه المحادثة", "poll_use_current", {}, owner=owner, color="p"),
            btn("❌ إلغاء",        "poll_cancel",       {}, owner=owner, color="d"),
        ]
        layout = [1, 1]

    elif step == "await_poll_type":
        text = (
            f"📊 <b>إنشاء تصويت</b>  ·  الخطوة 2\n{get_lines()}\n\n"
            "🧠 <b>اختر نوع التصويت:</b>"
        )
        buttons = [
            btn("📊 تصويت عادي", "poll_type_select", {"pt": "normal"}, owner=owner, color="p"),
            btn("🧠 اختبار",     "poll_type_select", {"pt": "quiz"},   owner=owner, color="su"),
            btn("🔙 رجوع",       "poll_back_target", {},               owner=owner, color="p"),
            btn("❌ إلغاء",      "poll_cancel",       {},               owner=owner, color="d"),
        ]
        layout = [2, 2]

    elif step == "await_question":
        text = (
            f"📊 <b>إنشاء تصويت</b>  ·  الخطوة 3\n{get_lines()}\n\n"
            "✏️ <b>أرسل نص السؤال:</b>"
        )
        buttons = [btn("❌ إلغاء", "poll_cancel", {}, owner=owner, color="d")]
        layout = [1]

    elif step == "await_question_media":
        text = (
            f"📊 <b>إنشاء تصويت</b>  ·  الخطوة 4\n{get_lines()}\n\n"
            f"❓ <b>السؤال:</b> {extra.get('question', '')}\n\n"
            "🖼 <b>هل تريد إضافة وسائط للسؤال؟</b>\n"
            "أرسل صورة / فيديو، أو اضغط تخطي."
        )
        buttons = [
            btn("⏭ تخطي",  "poll_q_media_skip", {}, owner=owner, color="p"),
            btn("❌ إلغاء", "poll_cancel",        {}, owner=owner, color="d"),
        ]
        layout = [2]

    elif step == "await_description":
        text = (
            f"📊 <b>إنشاء تصويت</b>  ·  الخطوة 5\n{get_lines()}\n\n"
            "📝 <b>هل تريد إضافة وصف؟</b>\n"
            "أرسل نصاً أو صورة/فيديو، أو اضغط تخطي."
        )
        buttons = [
            btn("⏭ تخطي",  "poll_desc_skip", {}, owner=owner, color="p"),
            btn("❌ إلغاء", "poll_cancel",    {}, owner=owner, color="d"),
        ]
        layout = [2]

    elif step == "await_options":
        opts = extra.get("options", [])
        _COLOR_EMOJI = {"p": "🔵", "su": "🟢", "d": "🔴", "de": "⚪"}
        opts_text = "".join(
            f"  {i}. {_COLOR_EMOJI.get(o.get('color','p'),'🔵')} {o['text']}\n"
            for i, o in enumerate(opts, 1)
        )
        text = (
            f"📊 <b>إنشاء تصويت</b>  ·  الخطوة 5\n{get_lines()}\n\n"
            f"🔘 <b>الخيارات ({len(opts)}/{_MAX_OPTIONS}):</b>\n"
            f"{opts_text if opts_text else '  <i>لا توجد خيارات بعد</i>'}\n\n"
            "أرسل نص الخيار التالي."
        )
        buttons = []
        if len(opts) >= 2:
            buttons.append(btn("✅ انتهيت", "poll_option_done", {}, owner=owner, color="su"))
        buttons.append(btn("❌ إلغاء", "poll_cancel", {}, owner=owner, color="d"))
        layout = [len(buttons)]

    elif step == "await_settings":
        allow_ch     = extra.get("allow_change", True)
        is_hidden    = extra.get("is_hidden", False)
        show_voters  = extra.get("show_voters", False)
        max_changes  = extra.get("max_vote_changes", 0)
        lock_secs    = extra.get("lock_before_end", 0)
        duration     = extra.get("duration", 0)
        dur_label    = next((l for l, s in _DURATION_OPTIONS if s == duration), "بلا حد")
        lock_label   = "بلا قفل" if not lock_secs else f"قفل آخر {lock_secs//60}د"
        changes_label = "غير محدود" if not max_changes else f"حد {max_changes}"

        text = (
            f"📊 <b>إنشاء تصويت</b>  ·  الإعدادات\n{get_lines()}\n\n"
            f"{'✅' if allow_ch    else '❌'} تغيير الصوت  ({changes_label})\n"
            f"{'✅' if is_hidden   else '❌'} إخفاء النتائج\n"
            f"{'✅' if show_voters else '❌'} عرض المصوتين\n"
            f"⏳ المدة: <b>{dur_label}</b>\n"
            f"🔒 القفل: <b>{lock_label}</b>\n\n"
            "اضبط الإعدادات ثم اضغط <b>نشر</b>."
        )
        dur_btns = [
            btn(label, "poll_duration", {"d": secs}, owner=owner,
                color="su" if secs == duration else "p")
            for label, secs in _DURATION_OPTIONS
        ]
        lock_btns = [
            btn(lbl, "poll_setting", {"k": "lock_before_end", "v": s}, owner=owner,
                color="su" if s == lock_secs else "p")
            for lbl, s in [("بلا قفل", 0), ("قفل آخر 5د", 300), ("قفل آخر 15د", 900)]
        ]
        change_btns = [
            btn(lbl, "poll_setting", {"k": "max_vote_changes", "v": n}, owner=owner,
                color="su" if n == max_changes else "p")
            for lbl, n in [("غير محدود", 0), ("مرة واحدة", 1), ("3 مرات", 3)]
        ]
        buttons = [
            btn(f"{'✅' if allow_ch else '❌'} تغيير الصوت",
                "poll_setting", {"k": "allow_change", "v": int(not allow_ch)},
                owner=owner, color="p"),
            btn(f"{'✅' if is_hidden else '❌'} إخفاء النتائج",
                "poll_setting", {"k": "is_hidden", "v": int(not is_hidden)},
                owner=owner, color="p"),
            btn(f"{'✅' if show_voters else '❌'} عرض المصوتين",
                "poll_setting", {"k": "show_voters", "v": int(not show_voters)},
                owner=owner, color="p"),
        ] + dur_btns + lock_btns + change_btns + [
            btn("🚀 نشر التصويت", "poll_publish", {}, owner=owner, color="su"),
            btn("❌ إلغاء",       "poll_cancel",  {}, owner=owner, color="d"),
        ]
        layout = [3, 3, 3, 3, 3, 1, 1]

    else:
        return

    markup = build_keyboard(buttons, layout, uid)
    _edit_or_send(cid, mid, text, markup, uid)


# ══════════════════════════════════════════
# معالجات الإدخال
# ══════════════════════════════════════════

def handle_poll_input(message) -> bool:
    uid = message.from_user.id
    cid = message.chat.id
    if not StateManager.is_state(uid, cid, _STATE):
        return False

    state = StateManager.get(uid, cid)
    step  = state.get("step", "")
    extra = state.get("extra", {})
    _delete(cid, message.message_id)

    if step == "await_target_id":
        raw = (message.text or "").strip()
        if not raw.lstrip("-").isdigit():
            _toast(cid, "❌ أرسل معرّفاً رقمياً صحيحاً.")
            return True
        target_id = int(raw)
        valid, err = _validate_target(target_id, uid)
        if not valid:
            mid = StateManager.get_mid(uid, cid)
            owner = (uid, cid)
            if mid:
                try:
                    markup = build_keyboard([
                        btn("📍 هذه المحادثة", "poll_use_current", {}, owner=owner, color="p"),
                        btn("❌ إلغاء",        "poll_cancel",       {}, owner=owner, color="d"),
                    ], [1, 1], uid)
                    bot.edit_message_text(
                        f"❌ <b>تعذّر الوصول للوجهة</b>\n\n{err}\n\n"
                        "أرسل معرّفاً آخر أو اختر من الزر:",
                        cid, mid, parse_mode="HTML", reply_markup=markup,
                    )
                except Exception:
                    pass
            return True
        _set_extra(uid, cid, target=target_id)
        StateManager.update(uid, cid, {"step": "await_poll_type"})
        _panel(uid, cid)
        return True

    if step == "await_question":
        q = (message.text or "").strip()
        if not q:
            _toast(cid, "❌ السؤال لا يمكن أن يكون فارغاً.")
            return True
        _set_extra(uid, cid, question=q)
        StateManager.update(uid, cid, {"step": "await_question_media"})
        _panel(uid, cid)
        return True

    if step == "await_question_media":
        _toast(cid, "📎 أرسل صورة / فيديو، أو اضغط <b>تخطي</b>.")
        return True

    if step == "await_description":
        raw = (message.text or "").strip()
        if raw:
            _set_extra(uid, cid, description=raw)
            StateManager.update(uid, cid, {"step": "await_options"})
            _panel(uid, cid)
        else:
            _toast(cid, "📎 أرسل نصاً أو وسائط، أو اضغط <b>تخطي</b>.")
        return True

    if step == "await_options":
        opt_text = (message.text or "").strip()
        if not opt_text:
            return True
        opts = extra.get("options", [])
        if len(opts) >= _MAX_OPTIONS:
            _toast(cid, f"❌ الحد الأقصى {_MAX_OPTIONS} خيارات.")
            return True
        # save text temporarily and ask for color
        _set_extra(uid, cid, _pending_opt=opt_text)
        StateManager.update(uid, cid, {"step": "await_opt_color"})
        _ask_option_color(uid, cid)
        return True

    return False


def handle_poll_media(message) -> bool:
    uid = message.from_user.id
    cid = message.chat.id
    if not StateManager.is_state(uid, cid, _STATE):
        return False

    step = StateManager.get_step(uid, cid)
    file_id, media_type = _extract_media(message)
    if not file_id:
        return False

    _delete(cid, message.message_id)

    if step == "await_question_media":
        _set_extra(uid, cid, q_media_id=file_id, q_media_type=media_type)
        StateManager.update(uid, cid, {"step": "await_description"})
        _panel(uid, cid)
        return True

    if step == "await_description":
        _set_extra(uid, cid, desc_media_id=file_id, desc_media_type=media_type)
        StateManager.update(uid, cid, {"step": "await_options"})
        _panel(uid, cid)
        return True

    return False


# ══════════════════════════════════════════
# تفاصيل التصويت (بالرد)
# ══════════════════════════════════════════

_DETAIL_TRIGGERS = {"تفاصيل", "كشف التصويت", "/poll_info", "stats"}


def handle_poll_control_panel(message) -> bool:
    """
    أمر: لوحة التصويت
    يعمل بطريقتين:
    1. رد على رسالة التصويت → يفتح لوحة التحكم لذلك التصويت
    2. بدون رد → يبحث عن آخر تصويت أنشأه المستخدم في هذه المحادثة
    المنشئ فقط يمكنه الوصول.
    """
    text = (message.text or "").strip()
    if text != "لوحة التصويت":
        return False

    uid = message.from_user.id
    cid = message.chat.id

    poll = None

    # طريقة 1: رد على رسالة التصويت
    if message.reply_to_message:
        poll = get_poll_by_message(cid, message.reply_to_message.message_id)

    # طريقة 2: آخر تصويت أنشأه المستخدم في هذه المحادثة
    if not poll:
        poll = get_latest_poll_by_creator(cid, uid)

    try:
        bot.delete_message(cid, message.message_id)
    except Exception:
        pass

    if not poll:
        bot.send_message(
            cid,
            "❌ <b>لم يتم العثور على تصويت.</b>\n\n"
            "رد على رسالة التصويت واكتب <code>لوحة التصويت</code>.",
            parse_mode="HTML",
        )
        return True

    if poll["created_by"] != uid:
        bot.send_message(
            cid,
            "❌ <b>لوحة التحكم متاحة للمنشئ فقط.</b>",
            parse_mode="HTML",
        )
        return True

    _send_creator_panel(cid, uid, poll["id"])
    return True


def handle_poll_details(message) -> bool:
    text = (message.text or "").strip().lower()
    if text not in _DETAIL_TRIGGERS:
        return False
    if not message.reply_to_message:
        return False

    uid     = message.from_user.id
    cid     = message.chat.id
    rep_msg = message.reply_to_message

    poll = get_poll_by_message(cid, rep_msg.message_id)
    if not poll:
        return False

    # المنشئ يرى قائمة المصوتين دائماً؛ الآخرون فقط إذا show_voters=1
    show_v = bool(poll.get("show_voters")) or (uid == poll["created_by"])
    stats  = _build_stats_text(poll["id"], poll, show_voters=show_v)

    try:
        bot.delete_message(cid, message.message_id)
    except Exception:
        pass
    bot.send_message(cid, stats, parse_mode="HTML",
                     reply_to_message_id=rep_msg.message_id)
    return True


def _build_stats_text(poll_id: int, poll: dict, show_voters: bool = False) -> str:
    opts   = get_poll_options(poll_id)
    total  = get_total_votes(poll_id)
    type_l = "🧠 اختبار" if poll.get("poll_type") == "quiz" else "📊 تصويت"
    status = "🔒 مغلق" if poll.get("is_closed") else "🟢 مفتوح"

    _DIV = "─────────────────"

    lines = [
        f"<b>{type_l} — #{poll_id}</b>",
        _DIV,
        "",
        f"❓ <b>{poll['question']}</b>",
        "",
        f"الحالة: {status}",
    ]

    if poll.get("end_time") and not poll.get("is_closed"):
        left = poll["end_time"] - int(time.time())
        if left > 0:
            lines.append(f"⏳ الوقت المتبقي: <b>{_fmt_duration(left)}</b>")

    lines += [f"👥 إجمالي الأصوات: <b>{total}</b>", "", _DIV]

    for opt in opts:
        pct = int((opt["votes_count"] / total) * 100) if total else 0
        bar = _progress_bar(pct)
        lines.append(f"\n{bar} {opt['text']}")
        lines.append(f"   {pct}% — {opt['votes_count']} صوت")

        if show_voters and opt["votes_count"] > 0:
            voters = get_option_voters(opt["id"], limit=10)
            if voters:
                ids_str = " | ".join(f"<code>{v}</code>" for v in voters)
                lines.append(f"   👤 {ids_str}")

    return "\n".join(lines)


# ══════════════════════════════════════════
# بناء رسالة التصويت المنشورة
# ══════════════════════════════════════════

def _build_poll_message(poll_id: int, poll: dict, options: list) -> tuple:
    total      = get_total_votes(poll_id)
    type_label = "🧠 اختبار" if poll.get("poll_type") == "quiz" else "📊 تصويت"
    is_hidden  = bool(poll.get("is_hidden"))
    is_closed  = bool(poll.get("is_closed"))

    _DIV = "─────────────────"

    lines = [f"<b>{type_label}</b>", _DIV, ""]

    lines.append(f"❓ <b>{poll['question']}</b>")

    if poll.get("description"):
        lines.append(f"📝 {poll['description']}")

    if is_closed:
        lines.append("🔒 <b>التصويت مغلق</b>")
    elif poll.get("end_time"):
        left = poll["end_time"] - int(time.time())
        if left > 0:
            lines.append(f"⏳ ينتهي خلال: <b>{_fmt_duration(left)}</b>")

    lines.append("")

    if not is_hidden and total > 0:
        for opt in options:
            pct = int((opt["votes_count"] / total) * 100) if total else 0
            bar = _colored_bar(pct)
            lines.append(f"{opt['text']}\n{bar}  {pct}% ({opt['votes_count']})\n\n")
    else:
        for opt in options:
            lines.append(f"🔘 {opt['text']}")

    lines += ["", _DIV, f"👥 {total}"]

    text = "\n".join(lines)

    if is_closed:
        markup = None
    else:
        buttons = [
            btn(opt["text"], "poll_vote",
                {"pid": poll_id, "oid": opt["id"]},
                owner=None,
                color=opt.get("color") or "p")
            for opt in options
        ]
        cols = 2 if len(options) <= 4 else 3
        layout = []
        rem = len(buttons)
        while rem > 0:
            layout.append(min(cols, rem))
            rem -= cols
        markup = build_keyboard(buttons, layout, None)

    return text, markup


def _colored_bar(pct: int, width: int = 10) -> str:
    """شريط تقدم ملوّن: أخضر للأغلبية، أحمر للأقلية، رمادي للصفر."""
    filled = round(pct / 100 * width)
    if pct == 0:
        return "⬜" * width
    if pct >= 50:
        return "🟩" * filled + "⬜" * (width - filled)
    return "🟥" * filled + "⬜" * (width - filled)


def _progress_bar(pct: int, width: int = 10) -> str:
    """شريط نصي للإحصائيات التفصيلية."""
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


def _fmt_duration(secs: int) -> str:
    if secs >= 3600:
        h = secs // 3600
        m = (secs % 3600) // 60
        return f"{h}س {m}د" if m else f"{h}س"
    if secs >= 60:
        return f"{secs // 60}د"
    return f"{secs}ث"


# ══════════════════════════════════════════
# لوحة تحكم المنشئ
# ══════════════════════════════════════════

def _send_creator_panel(cid: int, uid: int, poll_id: int, edit_mid: int = None):
    poll = get_poll(poll_id)
    if not poll:
        return
    owner = (uid, cid)
    text, buttons, layout = _creator_panel_content(poll_id, poll, owner)
    markup = build_keyboard(buttons, layout, uid)
    if edit_mid:
        try:
            bot.edit_message_text(text, cid, edit_mid,
                                  parse_mode="HTML", reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(cid, text, parse_mode="HTML", reply_markup=markup)


def _edit_creator_panel(call, poll_id: int):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    poll  = get_poll(poll_id)
    if not poll:
        return
    owner = (uid, cid)
    text, buttons, layout = _creator_panel_content(poll_id, poll, owner)
    markup = build_keyboard(buttons, layout, uid)
    try:
        bot.edit_message_text(text, cid, call.message.message_id,
                              parse_mode="HTML", reply_markup=markup)
    except Exception:
        pass


def _creator_panel_content(poll_id: int, poll: dict, owner: tuple):
    total     = get_total_votes(poll_id)
    is_closed = bool(poll.get("is_closed"))
    status    = "🔒 مغلق" if is_closed else "🟢 مفتوح"

    text = (
        f"🎛 <b>لوحة تحكم التصويت #{poll_id}</b>\n{get_lines()}\n\n"
        f"❓ {poll['question']}\n"
        f"الحالة: {status}  |  👥 {total} صوت\n"
    )
    if poll.get("end_time") and not is_closed:
        left = poll["end_time"] - int(time.time())
        if left > 0:
            text += f"⏳ متبقي: {_fmt_duration(left)}\n"

    buttons = []
    if is_closed:
        buttons.append(btn("🔓 إعادة فتح", "poll_admin_reopen", {"pid": poll_id}, owner=owner, color="su"))
    else:
        buttons.append(btn("⛔ إيقاف",     "poll_admin_stop",   {"pid": poll_id}, owner=owner, color="d"))

    buttons += [
        btn("⏳ تمديد",    "poll_admin_extend", {"pid": poll_id}, owner=owner, color="p"),
        btn("📊 إحصائيات", "poll_admin_stats",  {"pid": poll_id}, owner=owner, color="p"),
        btn("🗑 حذف",      "poll_admin_delete", {"pid": poll_id}, owner=owner, color="d"),
    ]
    layout = [1, 2, 1]
    return text, buttons, layout


# ══════════════════════════════════════════
# تحديث رسالة التصويت
# ══════════════════════════════════════════

def _refresh_poll_message(msg, poll_id: int):
    poll = get_poll(poll_id)
    if not poll:
        return
    opts = get_poll_options(poll_id)
    text, markup = _build_poll_message(poll_id, poll, opts)
    try:
        if poll.get("question_media_id"):
            bot.edit_message_caption(
                caption=text, chat_id=msg.chat.id, message_id=msg.message_id,
                parse_mode="HTML", reply_markup=markup,
            )
        else:
            bot.edit_message_text(
                text, msg.chat.id, msg.message_id,
                parse_mode="HTML", reply_markup=markup,
            )
    except Exception:
        pass


def _refresh_poll_in_chat(poll: dict):
    """يُستدعى من لوحة التحكم أو poll_closer."""
    if not poll or not poll.get("message_id"):
        return
    opts = get_poll_options(poll["id"])
    text, markup = _build_poll_message(poll["id"], poll, opts)
    try:
        if poll.get("question_media_id"):
            bot.edit_message_caption(
                caption=text, chat_id=poll["chat_id"], message_id=poll["message_id"],
                parse_mode="HTML", reply_markup=markup,
            )
        else:
            bot.edit_message_text(
                text, poll["chat_id"], poll["message_id"],
                parse_mode="HTML", reply_markup=markup,
            )
    except Exception:
        pass


# ══════════════════════════════════════════
# التحقق من الصلاحيات
# ══════════════════════════════════════════

def _validate_target(target_id: int, user_id: int) -> tuple:
    try:
        chat = bot.get_chat(target_id)
    except Exception as e:
        err = str(e).lower()
        if "chat not found" in err or "invalid" in err:
            return False, "❌ الشات غير موجود أو المعرّف خاطئ."
        return False, "❌ تعذّر الوصول للوجهة، تأكد من المعرّف أو أن البوت موجود هناك."

    try:
        bot_id     = bot.get_me().id
        bot_member = bot.get_chat_member(target_id, bot_id)
        if bot_member.status in ("left", "kicked"):
            return False, "❌ البوت ليس عضواً في هذا الشات. أضفه أولاً."
        if chat.type == "channel" and bot_member.status != "administrator":
            return False, "❌ البوت يحتاج صلاحية المشرف في القناة."
        if chat.type == "channel" and not getattr(bot_member, "can_post_messages", False):
            return False, "❌ البوت لا يملك صلاحية نشر الرسائل في القناة."
    except Exception as e:
        err = str(e).lower()
        if "member list is inaccessible" in err or "not enough rights" in err:
            # القناة لا تسمح بفحص الأعضاء — نفترض أن البوت مشرف
            pass
        else:
            return False, "❌ لا يمكن التحقق من صلاحيات البوت.\nتأكد أن البوت مشرف في القناة."

    try:
        user_member = bot.get_chat_member(target_id, user_id)
        if user_member.status not in ("administrator", "creator"):
            return False, "❌ يجب أن تكون مشرفاً أو مالكاً في هذا الشات لإنشاء تصويت."
    except Exception as e:
        err = str(e).lower()
        if "member list is inaccessible" in err or "not enough rights" in err:
            # لا يمكن التحقق من المستخدم — نسمح بالمتابعة وسيظهر الخطأ عند النشر
            pass
        else:
            return False, "❌ تعذّر التحقق من صلاحياتك، تأكد أنك مشرف في هذا الشات."

    return True, ""


# ══════════════════════════════════════════
# مساعدات خاصة
# ══════════════════════════════════════════

def _set_extra(uid, cid, **kwargs):
    extra = StateManager.get_extra(uid, cid)
    extra.update(kwargs)
    StateManager.update(uid, cid, {"extra": extra})


def _extract_media(message):
    if message.photo:
        return message.photo[-1].file_id, "photo"
    if message.video:
        return message.video.file_id, "video"
    if message.document:
        return message.document.file_id, "document"
    if message.animation:
        return message.animation.file_id, "animation"
    return None, None


def _send_media(chat_id, file_id, media_type, caption, markup):
    if media_type == "photo":
        return bot.send_photo(chat_id, file_id, caption=caption,
                              parse_mode="HTML", reply_markup=markup)
    if media_type == "video":
        return bot.send_video(chat_id, file_id, caption=caption,
                              parse_mode="HTML", reply_markup=markup)
    if media_type == "document":
        return bot.send_document(chat_id, file_id, caption=caption,
                                 parse_mode="HTML", reply_markup=markup)
    if media_type == "animation":
        return bot.send_animation(chat_id, file_id, caption=caption,
                                  parse_mode="HTML", reply_markup=markup)
    return None


def _edit_or_send(cid, mid, text, markup, uid):
    if mid:
        try:
            bot.edit_message_text(text, cid, mid,
                                  parse_mode="HTML", reply_markup=markup)
            return
        except Exception as e:
            err = str(e).lower()
            if "message is not modified" in err:
                return   # not an error
            print(f"[poll._edit_or_send] edit failed cid={cid} mid={mid}: {e}")
    try:
        msg = bot.send_message(cid, text, parse_mode="HTML", reply_markup=markup)
        if msg:
            StateManager.set_mid(uid, cid, msg.message_id)
    except Exception as e:
        print(f"[poll._edit_or_send] send failed cid={cid}: {e}")


def _delete(cid, mid):
    try:
        bot.delete_message(cid, mid)
    except Exception:
        pass


def _toast(cid, text, ttl=4.0):
    try:
        msg = bot.send_message(cid, text, parse_mode="HTML")
        threading.Timer(ttl, lambda: _delete(cid, msg.message_id)).start()
    except Exception:
        pass
