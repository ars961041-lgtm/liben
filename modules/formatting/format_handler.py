"""
معالج التنسيق الذكي — التفاعل مع البوت (أزرار، معاينة، إرسال)
"""
from core.bot import bot
from utils.pagination import btn, send_ui, edit_ui, register_action, set_state, get_state, clear_state

from .format_parser import parse
from .format_constants import FORMAT_GUIDE

_B = "p"   # أزرق
_G = "su"  # أخضر
_R = "d"   # أحمر

# ══════════════════════════════════════════
# 🎯 نقطة الدخول — أمر "تنسيق"
# ══════════════════════════════════════════

def handle_format_command(message):
    """
    المستخدم يرد على رسالة بـ "تنسيق"
    يقرأ نص الرسالة الأصلية ويعرض معاينة.
    """
    if not message.text:
        return False

    text = message.text.strip().lower()
    if text not in ["تنسيق", "format"]:
        return False

    uid = message.from_user.id
    cid = message.chat.id

    # يجب أن يكون رداً على رسالة
    if not message.reply_to_message:
        bot.reply_to(
            message,
            "❌ <b>استخدام خاطئ</b>\n\n"
            "رد على الرسالة التي تريد تنسيقها بـ: <code>تنسيق</code>",
            parse_mode="HTML",
        )
        return True

    original = message.reply_to_message.text or message.reply_to_message.caption or ""
    if not original.strip():
        bot.reply_to(message, "❌ الرسالة المردود عليها لا تحتوي على نص.")
        return True

    _show_preview(message, uid, cid, original)
    return True


def _show_preview(message, uid: int, cid: int, raw_text: str):
    """يحلل النص ويعرض المعاينة مع الأزرار."""
    result = parse(raw_text)
    owner  = (uid, cid)

    # حفظ النص الأصلي في الحالة للسماح بالتعديل
    set_state(uid, cid, "fmt_preview", data={"raw": raw_text})

    # بناء نص المعاينة
    preview_header = "👁 <b>معاينة التنسيق:</b>\n━━━━━━━━━━━━━━━\n"
    preview_body   = result.html if result.html.strip() else "<i>(نص فارغ)</i>"

    # تحذيرات التصحيح التلقائي
    warn_text = ""
    if result.warnings:
        warn_text = "\n\n" + "\n".join(result.warnings)

    full_preview = preview_header + preview_body + warn_text

    buttons = [
        btn("✔️ إرسال",  "fmt_send",   {}, color=_G, owner=owner),
        btn("✏️ تعديل",  "fmt_edit",   {}, color=_B, owner=owner),
        btn("❌ إلغاء",  "fmt_cancel", {}, color=_R, owner=owner),
    ]

    try:
        send_ui(
            cid,
            text=full_preview,
            buttons=buttons,
            layout=[3],
            owner_id=uid,
            reply_to=message.message_id,
        )
    except Exception as e:
        # إذا كان HTML غير صالح — أرسل نصاً عادياً مع تحذير
        bot.reply_to(
            message,
            f"⚠️ <b>خطأ في التنسيق:</b>\n<code>{e}</code>\n\n"
            f"تحقق من صحة الوسوم وأعد المحاولة.",
            parse_mode="HTML",
        )
        clear_state(uid, cid)


# ══════════════════════════════════════════
# 🔘 أزرار المعاينة
# ══════════════════════════════════════════

@register_action("fmt_send")
def on_send(call, data):
    """إرسال النص المُنسَّق نهائياً."""
    uid = call.from_user.id
    cid = call.message.chat.id

    state = get_state(uid, cid)
    raw   = state.get("data", {}).get("raw", "")
    clear_state(uid, cid)

    if not raw:
        bot.answer_callback_query(call.id, "❌ انتهت صلاحية المعاينة.", show_alert=True)
        _delete_msg(cid, call.message.message_id)
        return

    result = parse(raw)

    # حذف رسالة المعاينة
    _delete_msg(cid, call.message.message_id)

    # إرسال النص المُنسَّق
    try:
        bot.send_message(cid, result.html, parse_mode="HTML")
        bot.answer_callback_query(call.id, "✅ تم الإرسال")
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خطأ: {e}", show_alert=True)


@register_action("fmt_edit")
def on_edit(call, data):
    """إلغاء المعاينة والسماح بإعادة الإرسال."""
    uid = call.from_user.id
    cid = call.message.chat.id
    clear_state(uid, cid)
    _delete_msg(cid, call.message.message_id)
    bot.answer_callback_query(call.id)
    bot.send_message(
        cid,
        "✏️ <b>وضع التعديل</b>\n\n"
        "رد على الرسالة مجدداً بـ <code>تنسيق</code> بعد تعديل النص.",
        parse_mode="HTML",
    )


@register_action("fmt_cancel")
def on_cancel(call, data):
    """إلغاء وحذف المعاينة."""
    uid = call.from_user.id
    cid = call.message.chat.id
    clear_state(uid, cid)
    _delete_msg(cid, call.message.message_id)
    bot.answer_callback_query(call.id, "تم الإلغاء")


# ══════════════════════════════════════════
# 📚 دليل التنسيق — أمر "شرح تنسيق"
# ══════════════════════════════════════════

def handle_format_guide(message):
    """يعرض دليل التنسيق التفاعلي."""
    if not message.text:
        return False

    text = message.text.strip().lower()
    if text not in ["شرح تنسيق", "دليل تنسيق", "format guide", "تنسيق دليل"]:
        return False

    uid   = message.from_user.id
    cid   = message.chat.id
    owner = (uid, cid)

    buttons = [
        btn(f"{v['emoji']} {k_label(k)}", "fmt_guide_section",
            {"sec": k}, color=_B, owner=owner)
        for k, v in FORMAT_GUIDE.items()
    ]
    buttons.append(btn("❌ إغلاق", "fmt_guide_close", {}, color=_R, owner=owner))

    layout = _grid(len(buttons) - 1, 2) + [1]

    send_ui(
        cid,
        text=(
            "📚 <b>دليل التنسيق الذكي</b>\n"
            "━━━━━━━━━━━━━━━\n\n"
            "اختر نوع التنسيق لعرض شرحه:"
        ),
        buttons=buttons,
        layout=layout,
        owner_id=uid,
        reply_to=message.message_id,
    )
    return True


def k_label(key: str) -> str:
    return FORMAT_GUIDE[key]["label"]


@register_action("fmt_guide_section")
def on_guide_section(call, data):
    """يعرض شرح قسم معين من الدليل."""
    uid = call.from_user.id
    cid = call.message.chat.id
    sec = data.get("sec", "bold")
    owner = (uid, cid)

    info = FORMAT_GUIDE.get(sec)
    if not info:
        bot.answer_callback_query(call.id, "❌ قسم غير موجود", show_alert=True)
        return

    text = (
        f"{info['title']}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📝 <b>الشرح:</b>\n{info['desc']}\n\n"
        f"🔤 <b>الاستخدام:</b>\n<code>{info['usage']}</code>\n\n"
        f"✨ <b>النتيجة:</b>\n{info['example']}"
    )

    back_btn = btn("🔙 رجوع للدليل", "fmt_guide_back", {}, color=_R, owner=owner)
    close_btn = btn("❌ إغلاق", "fmt_guide_close", {}, color=_R, owner=owner)

    edit_ui(call, text=text, buttons=[back_btn, close_btn], layout=[2])


@register_action("fmt_guide_back")
def on_guide_back(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)

    buttons = [
        btn(f"{v['emoji']} {k_label(k)}", "fmt_guide_section",
            {"sec": k}, color=_B, owner=owner)
        for k, v in FORMAT_GUIDE.items()
    ]
    buttons.append(btn("❌ إغلاق", "fmt_guide_close", {}, color=_R, owner=owner))
    layout = _grid(len(buttons) - 1, 2) + [1]

    edit_ui(
        call,
        text=(
            "📚 <b>دليل التنسيق الذكي</b>\n"
            "━━━━━━━━━━━━━━━\n\n"
            "اختر نوع التنسيق لعرض شرحه:"
        ),
        buttons=buttons,
        layout=layout,
    )


@register_action("fmt_guide_close")
def on_guide_close(call, data):
    bot.answer_callback_query(call.id)
    _delete_msg(call.message.chat.id, call.message.message_id)


# ══════════════════════════════════════════
# 🔧 مساعدات
# ══════════════════════════════════════════

def _delete_msg(chat_id: int, msg_id: int):
    try:
        bot.delete_message(chat_id, msg_id)
    except Exception:
        pass


def _grid(n: int, cols: int = 2) -> list:
    layout, rem = [], n
    while rem > 0:
        layout.append(min(cols, rem))
        rem -= cols
    return layout or [1]
