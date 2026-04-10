"""
ذكر مؤقت — يسمح للمستخدم بإنشاء ذكر شخصي مؤقت بدون قاعدة بيانات.

التدفق:
  ذكر → اطلب النص → اطلب العدد → أرسل الرسالة مع زر التسبيح
  كل ضغطة تنقص العداد → عند الوصول لصفر: كرر / احذف
"""
from core.bot import bot
from utils.pagination import btn, send_ui, edit_ui, register_action, set_state, get_state, clear_state

# ── تخزين مؤقت في الذاكرة: (user_id, chat_id) → {text, total, remaining} ──
_SESSIONS: dict[tuple, dict] = {}


# ══════════════════════════════════════════
# نقطة الدخول
# ══════════════════════════════════════════

def handle_custom_zikr_command(message) -> bool:
    if (message.text or "").strip() != "ذكر":
        return False
    uid = message.from_user.id
    cid = message.chat.id
    set_state(uid, cid, "czikr_awaiting_text", data={"_mid": None})
    bot.reply_to(message, "📿 أرسل نص الذكر:")
    return True


# ══════════════════════════════════════════
# معالج الإدخال النصي
# ══════════════════════════════════════════

def handle_custom_zikr_input(message) -> bool:
    uid   = message.from_user.id
    cid   = message.chat.id
    state = get_state(uid, cid)
    if not state:
        return False

    s = state.get("state", "")

    if s == "czikr_awaiting_text":
        text = (message.text or "").strip()
        if not text:
            bot.reply_to(message, "❌ أرسل نصاً صحيحاً.")
            return True
        clear_state(uid, cid)
        set_state(uid, cid, "czikr_awaiting_count",
                  data={"text": text})
        bot.reply_to(message, "🔢 كم مرة تريد التسبيح؟ (أرسل رقماً)")
        return True

    if s == "czikr_awaiting_count":
        raw   = (message.text or "").strip()
        sdata = state.get("data", {})
        ztext = sdata.get("text", "")

        notice = ""
        if not raw.isdigit():
            total  = 100
            notice = f"⚠️ إدخال غير رقمي — سيتم استخدام العدد الافتراضي: <b>100</b>"
        else:
            total = int(raw)
            if total <= 0:
                total  = 100
                notice = f"⚠️ العدد غير صالح — سيتم استخدام العدد الافتراضي: <b>100</b>"
            elif total > 1000:
                total  = 1000
                notice = f"⚠️ الحد الأقصى هو <b>1000</b> — تم تقليص العدد تلقائياً."

        clear_state(uid, cid)

        if notice:
            bot.reply_to(message, notice, parse_mode="HTML")

        _SESSIONS[(uid, cid)] = {"text": ztext, "total": total, "remaining": total}
        _send_zikr_msg(cid, uid, ztext, total, total,
                       reply_to=message.message_id)
        return True

    return False


# ══════════════════════════════════════════
# إرسال / تحديث رسالة الذكر
# ══════════════════════════════════════════

def _send_zikr_msg(cid, uid, text, total, remaining,
                   reply_to=None, call=None):
    owner   = (uid, cid)
    caption = f"📿 <b>{text}</b>\n\n🔁 المتبقي: <b>{remaining}</b> / {total}"
    buttons = [
        btn(f"✅  ({remaining})", "czikr_tap",
            {"r": remaining, "t": total}, owner=owner, color="su"),
    ]
    layout = [1]

    if call:
        edit_ui(call, text=caption, buttons=buttons, layout=layout)
    else:
        send_ui(cid, text=caption, buttons=buttons, layout=layout,
                owner_id=uid, reply_to=reply_to)


# ══════════════════════════════════════════
# معالجات الأزرار
# ══════════════════════════════════════════

@register_action("czikr_tap")
def on_tap(call, data):
    uid       = call.from_user.id
    cid       = call.message.chat.id
    remaining = int(data["r"]) - 1
    total     = int(data["t"])

    session = _SESSIONS.get((uid, cid))
    if not session:
        bot.answer_callback_query(call.id, "❌ انتهت الجلسة.", show_alert=True)
        return

    ztext = session["text"]

    if remaining > 0:
        session["remaining"] = remaining
        bot.answer_callback_query(call.id)
        _send_zikr_msg(cid, uid, ztext, total, remaining, call=call)
    else:
        # وصل للصفر — اسأل: كرر أم احذف؟
        session["remaining"] = 0
        bot.answer_callback_query(call.id, "🎉 أتممت الذكر!", show_alert=False)
        owner   = (uid, cid)
        caption = f"📿 <b>{ztext}</b>\n\n✅ <b>أتممت {total} مرة!</b>\n\nماذا تريد؟"
        buttons = [
            btn("🔁 كرر", "czikr_repeat", {"t": total}, owner=owner, color="su"),
            btn("🗑 احذف", "czikr_delete", {},           owner=owner, color="d"),
        ]
        edit_ui(call, text=caption, buttons=buttons, layout=[2])


@register_action("czikr_repeat")
def on_repeat(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    total = int(data["t"])

    session = _SESSIONS.get((uid, cid))
    if not session:
        bot.answer_callback_query(call.id, "❌ انتهت الجلسة.", show_alert=True)
        return

    session["remaining"] = total
    bot.answer_callback_query(call.id)
    _send_zikr_msg(cid, uid, session["text"], total, total, call=call)


@register_action("czikr_delete")
def on_delete(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    _SESSIONS.pop((uid, cid), None)
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(cid, call.message.message_id)
    except Exception:
        pass
