"""
نظام قوانين المجموعات — v2

أوامر:
  القوانين / قوانين الجروب
    - بدون رد  → عرض القوانين (أو رسالة إرشادية إذا لم تُضبط)
    - مع رد    → حفظ نص الرد كقوانين (مشرف فقط)

أزرار المشرف:
  🗑️ مسح  │  📌 تثبيت (ذكي)  │  🔔 تفعيل/إيقاف الإرسال  │  ℹ️ تفاصيل  │  ❌ إخفاء

أزرار الجميع:
  ❌ إخفاء

Auto-send throttle: max 1 send per chat per 10 seconds to prevent spam on bulk joins.
"""
import time
import threading

from core.bot import bot
from utils.keyboards import ui_btn, build_keyboard
from utils.helpers import get_lines
from handlers.group_admin.permissions import is_admin
from modules.rules.rules_db import (
    get_rules, set_rules, delete_rules, set_auto_send,
)

_MAX_LEN = 4096

# Throttle: (chat_id) → last_send_timestamp
_auto_send_throttle: dict[int, float] = {}
_throttle_lock = threading.Lock()
_THROTTLE_SEC  = 10   # min seconds between auto-sends per chat


# ══════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════

def handle_rules_command(message) -> bool:
    text = (message.text or "").strip()
    if text not in ("القوانين", "قوانين الجروب"):
        return False
    if message.chat.type not in ("group", "supergroup"):
        return False

    cid = message.chat.id
    uid = message.from_user.id

    # ── admin replied to a message → save as rules ──
    if message.reply_to_message and is_admin(message):
        raw = (message.reply_to_message.text or "").strip()
        if not raw:
            bot.reply_to(message, "❌ الرسالة المردود عليها لا تحتوي على نص.")
            return True
        if len(raw) > _MAX_LEN:
            bot.reply_to(message,
                         f"❌ القوانين طويلة جدًا ({len(raw)} حرف).\n"
                         f"الحد الأقصى: {_MAX_LEN} حرف.")
            return True
        set_rules(cid, raw, uid)
        bot.reply_to(message, "✅ تم حفظ قوانين المجموعة بنجاح.")
        return True

    # ── show rules ──
    _show_rules(cid, uid, reply_to=message.message_id)
    return True


# ══════════════════════════════════════════
# Show rules
# ══════════════════════════════════════════

def _show_rules(chat_id: int, user_id: int, reply_to: int = None):
    row = get_rules(chat_id)
    if not row:
        _show_no_rules(chat_id, user_id, reply_to)
        return

    text   = f"📜 <b>قوانين المجموعة</b>\n{get_lines()}\n\n{row['rules']}"
    markup = _build_markup(chat_id, user_id, row)
    kwargs = {"parse_mode": "HTML", "reply_markup": markup}
    if reply_to:
        kwargs["reply_to_message_id"] = reply_to
    bot.send_message(chat_id, text, **kwargs)


def _show_no_rules(chat_id: int, user_id: int, reply_to: int = None):
    """Friendly message explaining how to set rules — shown to admins only."""
    try:
        member = bot.get_chat_member(chat_id, user_id)
        is_adm = member.status in ("administrator", "creator")
    except Exception:
        is_adm = False

    if is_adm:
        text = (
            "📜 <b>لا توجد قوانين لهذا القروب بعد</b>\n\n"
            "لإضافة القوانين:\n"
            "1️⃣ اكتب القوانين في رسالة\n"
            "2️⃣ رد عليها بـ <code>القوانين</code>\n\n"
            "✅ سيتم حفظها فوراً وعرضها للأعضاء."
        )
    else:
        text = "📜 لا توجد قوانين لهذا القروب حتى الآن."

    kwargs = {"parse_mode": "HTML"}
    if reply_to:
        kwargs["reply_to_message_id"] = reply_to
    bot.send_message(chat_id, text, **kwargs)


def _build_markup(chat_id: int, user_id: int, row: dict):
    auto_on      = bool(row.get("auto_send", 0))
    toggle_label = "🔕 إيقاف الإرسال للجدد" if auto_on else "🔔 تفعيل الإرسال للجدد"

    try:
        member        = bot.get_chat_member(chat_id, user_id)
        viewer_is_adm = member.status in ("administrator", "creator")
    except Exception:
        viewer_is_adm = False

    if viewer_is_adm:
        buttons = [
            ui_btn("🗑️ مسح القوانين", action="rules_delete", style="danger"),
            ui_btn("📌 تثبيت",         action="rules_pin",    style="primary"),
            ui_btn(toggle_label,        action="rules_toggle", style="success"),
            ui_btn("ℹ️ تفاصيل",        action="rules_info",   style="primary"),
            ui_btn("❌ إخفاء",          action="rules_hide",   style="danger"),
        ]
        layout = [2, 2, 1]
    else:
        buttons = [ui_btn("❌ إخفاء", action="rules_hide", style="danger")]
        layout  = [1]

    return build_keyboard(buttons, layout)


# ══════════════════════════════════════════
# Callback registration
# ══════════════════════════════════════════

def register_rules_callbacks():
    """Register all rules callback handlers. Call once at startup."""

    @bot.callback_query_handler(func=lambda c: _action(c) == "rules_delete")
    def cb_delete(call):
        if not _admin_check(call):
            return
        cid = call.message.chat.id
        delete_rules(cid)
        bot.answer_callback_query(call.id, "✅ تم مسح القوانين.", show_alert=True)
        _safe_delete(cid, call.message.message_id)

    @bot.callback_query_handler(func=lambda c: _action(c) == "rules_pin")
    def cb_pin(call):
        if not _admin_check(call):
            return
        cid = call.message.chat.id
        mid = call.message.message_id
        # Unpin previous pinned message first (smart pin)
        try:
            chat = bot.get_chat(cid)
            if getattr(chat, "pinned_message", None):
                bot.unpin_chat_message(cid, chat.pinned_message.message_id)
        except Exception:
            pass
        try:
            bot.pin_chat_message(cid, mid, disable_notification=True)
            bot.answer_callback_query(call.id, "📌 تم تثبيت القوانين.")
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ فشل التثبيت: {e}", show_alert=True)

    @bot.callback_query_handler(func=lambda c: _action(c) == "rules_toggle")
    def cb_toggle(call):
        if not _admin_check(call):
            return
        cid = call.message.chat.id
        row = get_rules(cid)
        if not row:
            bot.answer_callback_query(call.id, "❌ لا توجد قوانين.", show_alert=True)
            return
        new_val = 0 if row["auto_send"] else 1
        set_auto_send(cid, new_val)
        label = "✅ تم تفعيل الإرسال للأعضاء الجدد" if new_val else "❌ تم إيقاف الإرسال للأعضاء الجدد"
        bot.answer_callback_query(call.id, label, show_alert=True)
        row["auto_send"] = new_val
        try:
            bot.edit_message_reply_markup(
                cid, call.message.message_id,
                reply_markup=_build_markup(cid, call.from_user.id, row),
            )
        except Exception:
            pass

    @bot.callback_query_handler(func=lambda c: _action(c) == "rules_info")
    def cb_info(call):
        if not _admin_check(call):
            return
        cid = call.message.chat.id
        row = get_rules(cid)
        if not row:
            bot.answer_callback_query(call.id, "❌ لا توجد قوانين.", show_alert=True)
            return

        try:
            updater = bot.get_chat(row["updated_by"])
            name    = updater.first_name or str(row["updated_by"])
        except Exception:
            name = str(row["updated_by"])

        updated_at = str(row.get("updated_at") or "")
        # Format: "2025-04-07 14:30:00" → "2025/04/07" + "14:30"
        date_part = updated_at[:10].replace("-", "/") if len(updated_at) >= 10 else "—"
        time_part = updated_at[11:16]                 if len(updated_at) >= 16 else "—"

        bot.answer_callback_query(call.id)
        bot.send_message(
            cid,
            f"ℹ️ <b>تفاصيل القوانين</b>\n{get_lines()}\n\n"
            f"👤 تم الإنشاء بواسطة: "
            f"<a href='tg://user?id={row['updated_by']}'>{name}</a>\n"
            f"📅 التاريخ: <b>{date_part}</b>\n"
            f"🕒 الوقت: <b>{time_part}</b>\n"
            f"🔔 الإرسال للجدد: {'✅ مفعّل' if row['auto_send'] else '❌ موقوف'}",
            parse_mode="HTML",
            reply_to_message_id=call.message.message_id,
        )

    @bot.callback_query_handler(func=lambda c: _action(c) == "rules_hide")
    def cb_hide(call):
        bot.answer_callback_query(call.id)
        _safe_delete(call.message.chat.id, call.message.message_id)


# ══════════════════════════════════════════
# Auto-send to new members (throttled)
# ══════════════════════════════════════════

def send_rules_to_new_member(chat_id: int, user_id: int):
    """
    Called from welcome.py when a new member joins.
    Throttled to max 1 send per chat per _THROTTLE_SEC seconds.
    """
    row = get_rules(chat_id)
    if not row or not row.get("auto_send"):
        return

    now = time.time()
    with _throttle_lock:
        last = _auto_send_throttle.get(chat_id, 0)
        if now - last < _THROTTLE_SEC:
            return
        _auto_send_throttle[chat_id] = now

    text = (
        f"📜 <b>قوانين المجموعة</b>\n{get_lines()}\n\n"
        f"{row['rules']}\n\n"
        "<i>يرجى الالتزام بالقوانين أعلاه.</i>"
    )
    markup = build_keyboard(
        [ui_btn("❌ إخفاء", action="rules_hide", style="danger")], [1]
    )
    try:
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)
    except Exception as e:
        print(f"[rules] auto_send error: {e}")


# ══════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════

def _action(call) -> str:
    """Extract action string from callback_data (JSON or plain)."""
    import json
    data = call.data or ""
    try:
        return json.loads(data).get("a", "")
    except Exception:
        return data


def _admin_check(call) -> bool:
    uid = call.from_user.id
    cid = call.message.chat.id
    try:
        if bot.get_chat_member(cid, uid).status in ("administrator", "creator"):
            return True
    except Exception:
        pass
    bot.answer_callback_query(call.id, "❌ هذا الزر للمشرفين فقط.", show_alert=True)
    return False


def _safe_delete(chat_id: int, message_id: int):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass
