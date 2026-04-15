"""
إنشاء منشور — أداة المطور.  v3 — Production Grade

Single-panel flow: one message is edited at every step.
Real preview: edit_message_media (photo) or edit_message_text (text-only).
Photo input: handled directly in handle_post_creator_input().

Button input format (per line):
    نص | https://url          → URL button, default color
    نص | https://url | 1      → URL button, primary (blue)
    نص | https://url | 2      → URL button, success (green)
    نص | https://url | 3      → URL button, danger (red)
    نص | callback:action_name → internal callback button
"""
import os
import threading

from core.bot import bot
from core.admin import is_any_dev
from core.state_manager import StateManager
from utils.pagination import btn, send_ui, register_action
from utils.pagination.buttons import build_keyboard
from utils.helpers import get_lines, build_colored_buttons
from telebot.types import InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo

_STATE    = "post_creator"
_TTL      = 600          # 10 min
_MAX_BTNS = 10           # max buttons per post

_COLOR_MAP = {"1": "primary", "2": "success", "3": "danger"}

_COLOR_LEGEND = (
    "🎨 <b>ألوان الأزرار:</b>\n"
    "  1️⃣ أساسي (أزرق)\n"
    "  2️⃣ ثانوي (أخضر)\n"
    "  3️⃣ مميز (أحمر)\n"
    "  <i>(اتركه فارغاً = افتراضي)</i>"
)

# ══════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════

def open_post_creator(message):
    uid = message.from_user.id
    cid = message.chat.id
    if not is_any_dev(uid):
        bot.reply_to(message, "❌ هذا الأمر للمطورين فقط.")
        return

    StateManager.set(uid, cid, {
        "type":  _STATE,
        "step":  "await_target",
        "extra": {"photo": None, "text": "", "buttons_raw": [], "layout": 1, "target": None},
    }, ttl=_TTL)

    owner = (uid, cid)
    text  = (
        f"📝 <b>إنشاء منشور جديد</b>\n{get_lines()}\n\n"
        "📍 <b>الخطوة 1 — اختر وجهة النشر</b>\n\n"
        "• اضغط <b>هذه المحادثة</b> للنشر هنا\n"
        "• أو أرسل معرّف القناة/المجموعة\n"
        "  مثال: <code>-1002121901488</code>"
    )
    buttons = [
        btn("📍 هذه المحادثة", "pc_use_current", {}, owner=owner, color="p"),
        btn("❌ إلغاء",        "pc_cancel",       {}, owner=owner, color="d"),
    ]
    msg = send_ui(cid, text=text, buttons=buttons, layout=[1, 1],
                  owner_id=uid, reply_to=message.message_id)
    if msg:
        StateManager.set_mid(uid, cid, msg.message_id)


# ══════════════════════════════════════════
# Callbacks
# ══════════════════════════════════════════

@register_action("pc_use_current")
def on_use_current(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_any_dev(uid):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    _set_extra(uid, cid, target=cid)
    StateManager.update(uid, cid, {"step": "await_has_image"})
    StateManager.set_mid(uid, cid, call.message.message_id)
    _panel(uid, cid, call=call)


@register_action("pc_has_image")
def on_has_image(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_any_dev(uid):
        bot.answer_callback_query(call.id)
        return
    bot.answer_callback_query(call.id)
    StateManager.update(uid, cid, {
        "step": "await_image" if int(data.get("v", 0)) else "await_text"
    })
    _panel(uid, cid, call=call)


@register_action("pc_has_buttons")
def on_has_buttons(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_any_dev(uid):
        bot.answer_callback_query(call.id)
        return
    bot.answer_callback_query(call.id)
    StateManager.update(uid, cid, {
        "step": "await_buttons" if int(data.get("v", 0)) else "preview"
    })
    _panel(uid, cid, call=call)


@register_action("pc_more_buttons")
def on_more_buttons(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_any_dev(uid):
        bot.answer_callback_query(call.id)
        return
    bot.answer_callback_query(call.id)
    StateManager.update(uid, cid, {"step": "await_buttons"})
    _panel(uid, cid, call=call)


@register_action("pc_layout")
def on_layout(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_any_dev(uid):
        bot.answer_callback_query(call.id)
        return
    bot.answer_callback_query(call.id)
    _set_extra(uid, cid, layout=int(data.get("l", 1)))
    StateManager.update(uid, cid, {"step": "preview"})
    _panel(uid, cid, call=call)


@register_action("pc_publish")
def on_publish(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_any_dev(uid):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return

    extra       = StateManager.get_extra(uid, cid)
    post_text   = extra.get("text", "")
    photo       = extra.get("photo")
    media_type  = extra.get("media_type", "photo")  # Default to photo for backward compatibility
    buttons_raw = extra.get("buttons_raw", [])
    cols        = extra.get("layout", 1)
    target      = extra.get("target", cid)
    post_markup = build_colored_buttons(buttons_raw, cols)

    # Sanitize user-generated post text
    from utils.html_sanitizer import sanitize_html_tags, safe_send_message
    safe_post_text = sanitize_html_tags(post_text)

    try:
        if photo:
            if media_type == "video":
                bot.send_video(target, photo, caption=safe_post_text,
                              parse_mode="HTML", reply_markup=post_markup)
            else:  # photo or default
                bot.send_photo(target, photo, caption=safe_post_text,
                              parse_mode="HTML", reply_markup=post_markup)
        else:
            safe_send_message(target, safe_post_text, parse_mode="HTML", reply_markup=post_markup)
        bot.answer_callback_query(call.id, "✅ تم النشر بنجاح!", show_alert=True)
        StateManager.clear(uid, cid)
        try:
            bot.edit_message_text(
                f"✅ <b>تم نشر المنشور بنجاح!</b>\n📍 الهدف: <code>{target}</code>",
                cid, call.message.message_id,
                parse_mode="HTML", reply_markup=None,
            )
        except Exception:
            pass
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
        print(f"[post_creator.on_publish] uid={uid} target={target} error={e}")
        bot.answer_callback_query(call.id, msg, show_alert=True)


@register_action("pc_back")
def on_back(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_any_dev(uid):
        bot.answer_callback_query(call.id)
        return
    bot.answer_callback_query(call.id)
    step = data.get("s", "await_has_image")
    StateManager.update(uid, cid, {"step": step})
    _panel(uid, cid, call=call)


@register_action("pc_edit_text")
def on_edit_text(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_any_dev(uid):
        bot.answer_callback_query(call.id)
        return
    bot.answer_callback_query(call.id)
    StateManager.update(uid, cid, {"step": "await_text"})
    _panel(uid, cid, call=call)


@register_action("pc_edit_image")
def on_edit_image(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_any_dev(uid):
        bot.answer_callback_query(call.id)
        return
    bot.answer_callback_query(call.id)
    StateManager.update(uid, cid, {"step": "await_image"})
    _panel(uid, cid, call=call)


@register_action("pc_edit_buttons")
def on_edit_buttons(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_any_dev(uid):
        bot.answer_callback_query(call.id)
        return
    bot.answer_callback_query(call.id)
    _set_extra(uid, cid, buttons_raw=[])
    StateManager.update(uid, cid, {"step": "await_buttons"})
    _panel(uid, cid, call=call)


@register_action("pc_cancel")
def on_cancel(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    bot.answer_callback_query(call.id)
    StateManager.clear(uid, cid)
    try:
        bot.edit_message_text(
            "❌ <b>تم إلغاء إنشاء المنشور.</b>",
            cid, call.message.message_id,
            parse_mode="HTML", reply_markup=None,
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# Central panel renderer
# ══════════════════════════════════════════

def _panel(uid, cid, call=None):
    """
    Renders the correct UI for the current step.
    Always edits the single panel message.
    In preview mode: uses edit_message_media (photo) or edit_message_text.
    """
    state = StateManager.get(uid, cid)
    if not state:
        return
    step  = state.get("step", "")
    extra = state.get("extra", {})
    owner = (uid, cid)
    mid   = StateManager.get_mid(uid, cid)

    # ── status bar shown on most steps ──
    photo       = extra.get("photo")
    post_text   = extra.get("text", "")
    buttons_raw = extra.get("buttons_raw", [])
    status = (
        f"\n{get_lines()}\n"
        f"{'📷 صورة محفوظة' if photo else '🚫 لا توجد صورة'}  "
        f"│  🔘 أزرار: {len(buttons_raw)}"
        f"\n{get_lines()}\n\n"
    )

    # ── step definitions ──
    if step == "await_has_image":
        text = (
            f"📝 <b>إنشاء منشور</b>  ·  الخطوة 1/4\n"
            f"{status}"
            "🖼 <b>هل عندك صورة للمنشور؟</b>"
        )
        buttons = [
            btn("✅ نعم، سأرسل صورة", "pc_has_image", {"v": 1}, owner=owner, color="su"),
            btn("➡️ لا، بدون صورة",  "pc_has_image", {"v": 0}, owner=owner, color="p"),
            btn("❌ إلغاء",           "pc_cancel",     {},       owner=owner, color="d"),
        ]
        layout = [1, 1, 1]

    elif step == "await_image":
        text = (
            f"📝 <b>إنشاء منشور</b>  ·  الخطوة 1/4\n"
            f"{status}"
            "📸 <b>أرسل الصورة أو الفيديو الآن</b>\n\n"
            "أرسلها كـ <b>صورة أو فيديو</b> (وليس ملفاً مضغوطاً).\n"
            "💡 يمكنك إضافة نص مع الصورة/الفيديو كتعليق."
        )
        buttons = [
            btn("🔙 رجوع", "pc_back",   {"s": "await_has_image"}, owner=owner),
            btn("❌ إلغاء", "pc_cancel", {},                       owner=owner, color="d"),
        ]
        layout = [2]

    elif step == "await_text":
        text = (
            f"📝 <b>إنشاء منشور</b>  ·  الخطوة 2/4\n"
            f"{status}"
            "✍️ <b>أرسل نص المنشور</b>\n\n"
            "يدعم HTML:\n"
            "<code>&lt;b&gt;عريض&lt;/b&gt;</code>  "
            "<code>&lt;i&gt;مائل&lt;/i&gt;</code>  "
            "<code>&lt;code&gt;كود&lt;/code&gt;</code>\n"
            "<code>&lt;a href='URL'&gt;رابط&lt;/a&gt;</code>"
        )
        buttons = [
            btn("🔙 رجوع", "pc_back",   {"s": "await_has_image"}, owner=owner),
            btn("❌ إلغاء", "pc_cancel", {},                       owner=owner, color="d"),
        ]
        layout = [2]

    elif step == "await_has_buttons":
        text = (
            f"📝 <b>إنشاء منشور</b>  ·  الخطوة 3/4\n"
            f"{status}"
            "🔘 <b>هل يوجد أزرار في المنشور؟</b>"
        )
        buttons = [
            btn("✅ نعم، أضف أزرار", "pc_has_buttons", {"v": 1}, owner=owner, color="su"),
            btn("➡️ لا، بدون أزرار", "pc_has_buttons", {"v": 0}, owner=owner, color="p"),
            btn("🔙 رجوع",           "pc_back",         {"s": "await_text"}, owner=owner),
            btn("❌ إلغاء",           "pc_cancel",        {},                  owner=owner, color="d"),
        ]
        layout = [1, 1, 2]

    elif step == "await_buttons":
        saved = f"\n\n✅ أزرار محفوظة: <b>{len(buttons_raw)}</b>" if buttons_raw else ""
        text = (
            f"📝 <b>إنشاء منشور</b>  ·  الخطوة 3/4\n"
            f"{status}"
            "🔘 <b>أضف الأزرار</b>\n\n"
            "أرسل كل زر في سطر:\n"
            "<code>نص | https://رابط | رقم_اللون</code>\n"
            "<code>نص | callback:action_name | رقم_اللون</code>\n\n"
            f"{_COLOR_LEGEND}"
            "\n\n<b>مثال:</b>\n"
            "<code>زيارة الموقع | https://example.com | 1</code>\n"
            "<code>📢 قناة التحديثات | https://t.me/BotBeloPro | 3</code>\n"
            f"{saved}"
        )
        buttons = [
            btn("🔙 رجوع", "pc_back",   {"s": "await_has_buttons"}, owner=owner),
            btn("❌ إلغاء", "pc_cancel", {},                         owner=owner, color="d"),
        ]
        layout = [2]

    elif step == "await_layout":
        count = len(buttons_raw)
        text  = (
            f"📝 <b>إنشاء منشور</b>  ·  الخطوة 3/4\n"
            f"{status}"
            f"📐 <b>اختر تخطيط الأزرار</b>\n\n"
            f"عدد الأزرار: <b>{count}</b>"
        )
        buttons = [
            btn("1️⃣ زر واحد في كل صف",    "pc_layout",      {"l": 1}, owner=owner, color="p"),
            btn("2️⃣ زران في كل صف",        "pc_layout",      {"l": 2}, owner=owner, color="p"),
            btn("➕ أضف المزيد من الأزرار", "pc_more_buttons", {},       owner=owner),
            btn("🔙 رجوع",                 "pc_back",         {"s": "await_buttons"}, owner=owner),
            btn("❌ إلغاء",                 "pc_cancel",        {},       owner=owner, color="d"),
        ]
        layout = [1, 1, 1, 2]

    elif step == "preview":
        return _render_preview(uid, cid, call, extra, mid)

    else:
        return

    markup = build_keyboard(buttons, layout, uid)
    _edit_or_send_text(cid, mid, text, markup, uid)


def _render_preview(uid, cid, call, extra, mid):
    """
    Real preview: shows the post exactly as it will appear.
    Uses edit_message_media for photo/video posts, edit_message_text for text-only.
    Control buttons are appended below.
    """
    from utils.html_sanitizer import safe_send_message, sanitize_html_tags
    
    owner       = (uid, cid)
    post_text   = extra.get("text", "")
    photo       = extra.get("photo")
    media_type  = extra.get("media_type", "photo")  # Default to photo for backward compatibility
    buttons_raw = extra.get("buttons_raw", [])
    cols        = extra.get("layout", 1)
    target      = extra.get("target", cid)

    # Sanitize user-generated post text
    safe_post_text = sanitize_html_tags(post_text)

    # Build the post's own markup (URL/callback buttons)
    post_markup = build_colored_buttons(buttons_raw, cols)

    # Control panel buttons
    ctrl = [
        btn("🚀 نشر الآن",      "pc_publish",      {}, owner=owner, color="su"),
        btn("✏️ تعديل النص",    "pc_edit_text",    {}, owner=owner, color="p"),
        btn("🖼 تغيير الوسائط", "pc_edit_image",   {}, owner=owner, color="p"),
        btn("🔘 تعديل الأزرار", "pc_edit_buttons", {}, owner=owner, color="p"),
        btn("🔙 رجوع",          "pc_back",          {"s": "await_has_buttons"}, owner=owner),
        btn("❌ إلغاء",         "pc_cancel",        {}, owner=owner, color="d"),
    ]
    ctrl_markup = build_keyboard(ctrl, [1, 2, 2, 2], uid)

    # ── header shown above the preview ──
    media_label = "📷 صورة" if media_type == "photo" else "🎥 فيديو" if media_type == "video" else "📄 نص فقط"
    header = (
        f"👁 <b>معاينة المنشور</b>\n{get_lines()}\n"
        f"📍 الهدف: <code>{target}</code>  │  "
        f"{media_label if photo else '📄 نص فقط'}  │  "
        f"🔘 {len(buttons_raw)} أزرار\n"
        f"{get_lines()}"
    )

    if photo and mid:
        # Replace panel with the actual media + post markup, then send controls
        try:
            if media_type == "video":
                from telebot.types import InputMediaVideo
                media = InputMediaVideo(media=photo, caption=safe_post_text, parse_mode="HTML")
            else:  # photo or default
                media = InputMediaPhoto(media=photo, caption=safe_post_text, parse_mode="HTML")
            bot.edit_message_media(media, cid, mid, reply_markup=post_markup)
            # Send a separate control panel message
            ctrl_msg = safe_send_message(cid, header, parse_mode="HTML", reply_markup=ctrl_markup)
            if ctrl_msg:
                StateManager.set_mid(uid, cid, ctrl_msg.message_id)
            return
        except Exception:
            pass

    # Text-only preview or fallback: edit panel with header + post text + controls
    combined = f"{header}\n\n{safe_post_text}"
    _edit_or_send_text(cid, mid, combined, ctrl_markup, uid)


# ══════════════════════════════════════════
# Input handlers
# ══════════════════════════════════════════

def handle_post_creator_input(message) -> bool:
    """Handles text input steps. Called from _handle_input_states in replies.py."""
    uid = message.from_user.id
    cid = message.chat.id

    if not StateManager.is_state(uid, cid, _STATE):
        return False
    if not is_any_dev(uid):
        return False

    state = StateManager.get(uid, cid)
    step  = state.get("step", "")
    extra = state.get("extra", {})

    _delete(cid, message.message_id)

    if step == "await_target":
        raw = (message.text or "").strip()
        if not raw.lstrip("-").isdigit():
            _toast(cid, "❌ أرسل معرّفاً رقمياً صحيحاً.")
            return True

        target_id = int(raw)

        # ── التحقق من وجود البوت في القناة/المجموعة وصلاحياته ──
        valid, err_msg = _validate_target(target_id)
        if not valid:
            mid = StateManager.get_mid(uid, cid)
            if mid:
                try:
                    bot.edit_message_text(
                        f"❌ <b>تعذّر النشر في هذه الوجهة</b>\n\n{err_msg}\n\n"
                        "أرسل معرّفاً آخر أو اضغط إلغاء:",
                        cid, mid, parse_mode="HTML",
                    )
                except Exception:
                    pass
            return True

        _set_extra(uid, cid, target=target_id)
        StateManager.update(uid, cid, {"step": "await_has_image"})
        _panel(uid, cid)
        return True

    if step == "await_image":
        # Check if message contains a photo or video
        if message.photo:
            # Handle photo input
            file_id = message.photo[-1].file_id  # highest resolution
            caption = (message.caption or "").strip()
            _delete(cid, message.message_id)
            _set_extra(uid, cid, photo=file_id, media_type="photo")
            if caption:
                # If photo has caption, use it as the text and skip text input step
                _set_extra(uid, cid, text=caption)
                StateManager.update(uid, cid, {"step": "await_has_buttons"})
            else:
                # No caption, proceed to text input step
                StateManager.update(uid, cid, {"step": "await_text"})
            _panel(uid, cid)
            return True
        elif message.video:
            # Handle video input
            file_id = message.video.file_id
            caption = (message.caption or "").strip()
            _delete(cid, message.message_id)
            _set_extra(uid, cid, photo=file_id, media_type="video")
            if caption:
                # If video has caption, use it as the text and skip text input step
                _set_extra(uid, cid, text=caption)
                StateManager.update(uid, cid, {"step": "await_has_buttons"})
            else:
                # No caption, proceed to text input step
                StateManager.update(uid, cid, {"step": "await_text"})
            _panel(uid, cid)
            return True
        else:
            # Show error only if it's not a photo or video
            _toast(cid, "❌ أرسل <b>صورة أو فيديو</b> وليس نصاً.")
            return True

    if step == "await_text":
        text = (message.text or "").strip()
        if not text:
            _toast(cid, "❌ النص لا يمكن أن يكون فارغاً.")
            return True
        _set_extra(uid, cid, text=text)
        StateManager.update(uid, cid, {"step": "await_has_buttons"})
        _panel(uid, cid)
        return True

    if step == "await_buttons":
        raw      = (message.text or "").strip()
        existing = extra.get("buttons_raw", [])
        remaining = _MAX_BTNS - len(existing)

        if remaining <= 0:
            _toast(cid, f"❌ وصلت للحد الأقصى ({_MAX_BTNS} أزرار).")
            return True

        new_btns, errors = _parse_buttons(raw, limit=remaining)
        if errors:
            _toast(cid, "\n".join(errors))
            return True
        if not new_btns:
            _toast(cid,
                   "❌ الصيغة غير صحيحة.\n"
                   "استخدم: <code>نص | رابط | رقم_اللون</code>")
            return True

        existing.extend(new_btns)
        _set_extra(uid, cid, buttons_raw=existing)
        StateManager.update(uid, cid, {"step": "await_layout"})
        _panel(uid, cid)
        return True

    return False



# ══════════════════════════════════════════
# Private helpers
# ══════════════════════════════════════════

def _set_extra(uid, cid, **kwargs):
    extra = StateManager.get_extra(uid, cid)
    extra.update(kwargs)
    StateManager.update(uid, cid, {"extra": extra})


def _parse_buttons(raw: str, limit: int = _MAX_BTNS):
    """
    Parse button lines. Returns (list_of_dicts, list_of_errors).
    Supports:
        label | https://url [| color]
        label | callback:action [| color]
    """
    result = []
    errors = []
    for i, line in enumerate(raw.splitlines()):
        line = line.strip()
        if not line:
            continue
        if "|" not in line:
            errors.append(f"❌ السطر {i+1}: يجب أن يحتوي على | بين النص والرابط.")
            continue
        parts = [p.strip() for p in line.split("|")]
        label = parts[0]
        dest  = parts[1] if len(parts) > 1 else ""
        color = _COLOR_MAP.get(parts[2], "primary") if len(parts) >= 3 else "default"

        if not label:
            errors.append(f"❌ السطر {i+1}: نص الزر فارغ.")
            continue
        if not dest:
            errors.append(f"❌ السطر {i+1}: الرابط أو الـ callback فارغ.")
            continue

        if dest.startswith("callback:"):
            result.append({"label": label, "cb": dest[9:], "style": color})
        elif dest.startswith("http://") or dest.startswith("https://"):
            result.append({"label": label, "url": dest, "style": color})
        else:
            errors.append(
                f"❌ السطر {i+1}: الرابط يجب أن يبدأ بـ https:// أو callback:\n"
                f"   <code>{dest[:60]}</code>"
            )
            continue

        if len(result) >= limit:
            break

    return result, errors


def _edit_or_send_text(cid, mid, text, markup, uid):
    """Edit existing panel or send new one with safe HTML handling."""
    from utils.html_sanitizer import safe_edit_message_text, safe_send_message
    
    if mid:
        if safe_edit_message_text(cid, mid, text, parse_mode="HTML", reply_markup=markup):
            return
    
    msg = safe_send_message(cid, text, parse_mode="HTML", reply_markup=markup)
    if msg:
        StateManager.set_mid(uid, cid, msg.message_id)


def _delete(cid, mid):
    try:
        bot.delete_message(cid, mid)
    except Exception:
        pass


def _toast(cid, text, ttl=4.0):
    """Self-destructing error message."""
    try:
        msg = bot.send_message(cid, text, parse_mode="HTML")
        threading.Timer(ttl, lambda: _delete(cid, msg.message_id)).start()
    except Exception:
        pass


def _validate_target(target_id: int) -> tuple[bool, str]:
    """
    يتحقق من أن البوت عضو في الوجهة ويملك صلاحية إرسال الرسائل.
    يرجع (True, "") عند النجاح، أو (False, رسالة_الخطأ).
    """
    try:
        bot_id = bot.get_me().id
        member = bot.get_chat_member(target_id, bot_id)
    except Exception as e:
        err = str(e).lower()
        if "chat not found" in err or "invalid" in err:
            return False, "❌ المجموعة/القناة غير موجودة أو المعرّف خاطئ."
        if "bot is not a member" in err or "kicked" in err:
            return False, "❌ البوت ليس عضواً في هذه المجموعة/القناة.\nأضف البوت أولاً ثم حاول مجدداً."
        if "member list is inaccessible" in err or "not enough rights" in err:
            # القناة لا تسمح بفحص الأعضاء — نفترض أن البوت مشرف إذا وصل للشات
            try:
                chat = bot.get_chat(target_id)
                if chat.type == "channel":
                    return True, ""   # سيتضح عند النشر الفعلي
            except Exception:
                pass
            return False, "❌ لا يمكن التحقق من الصلاحيات.\nتأكد أن البوت مشرف في القناة."
        return False, f"❌ تعذّر الوصول للوجهة.\nتأكد من المعرّف أو أن البوت موجود هناك."

    status = member.status
    if status == "kicked":
        return False, "❌ البوت محظور من هذه المجموعة/القناة."
    if status == "left":
        return False, "❌ البوت ليس عضواً في هذه المجموعة/القناة."

    # للقنوات: يجب أن يكون مشرفاً
    try:
        chat = bot.get_chat(target_id)
        if chat.type == "channel":
            if status != "administrator":
                return False, "❌ البوت يحتاج صلاحية المشرف في القناة لإرسال المنشورات."
            can_post = getattr(member, "can_post_messages", False)
            if not can_post:
                return False, "❌ البوت لا يملك صلاحية نشر الرسائل في هذه القناة.\nفعّل صلاحية 'نشر الرسائل' للبوت."
    except Exception:
        pass

    return True, ""
