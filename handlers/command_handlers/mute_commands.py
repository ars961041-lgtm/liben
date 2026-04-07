"""
أوامر الكتم العالمي النصية السريعة — للمطورين فقط.
"""
from core.bot import bot


def handle_global_mute_cmd(message):
    """
    كتم عالمي — يدعم:
    1. رد على رسالة: "كتم عالمي [سبب اختياري]"
    2. نص مباشر:   "كتم عالمي [ID] [سبب اختياري]"
    """
    from core.admin import global_mute
    uid, reason = _parse_mute_target(message, prefix="كتم عالمي")
    if not uid:
        bot.reply_to(message,
                     "❌ الصيغة:\n"
                     "• رد على رسالة: <code>كتم عالمي [السبب]</code>\n"
                     "• أو: <code>كتم عالمي [ID] [السبب]</code>",
                     parse_mode="HTML")
        return
    global_mute(uid, message.from_user.id, reason)
    bot.reply_to(message,
                 f"🔇 تم الكتم العالمي للمستخدم <code>{uid}</code>"
                 + (f"\n📝 السبب: {reason}" if reason else ""),
                 parse_mode="HTML")


def handle_global_unmute_cmd(message):
    """
    رفع كتم عالمي — يدعم:
    1. رد على رسالة: "رفع كتم عالمي [سبب اختياري للتحقق]"
    2. نص مباشر:   "رفع كتم عالمي [ID] [سبب اختياري للتحقق]"
    إذا أُعطي سبب، يتحقق من تطابقه مع سبب الكتم المسجل قبل الرفع.
    """
    from core.admin import global_unmute
    uid, reason = _parse_mute_target(message, prefix="رفع كتم عالمي")
    if not uid:
        bot.reply_to(message,
                     "❌ الصيغة:\n"
                     "• رد على رسالة: <code>رفع كتم عالمي</code>\n"
                     "• أو: <code>رفع كتم عالمي [ID]</code>\n"
                     "• مع تحقق السبب: <code>رفع كتم عالمي [ID] [السبب]</code>",
                     parse_mode="HTML")
        return

    ok, detail = global_unmute(uid, reason)
    if ok:
        msg = f"✅ تم رفع الكتم العالمي عن <code>{uid}</code>"
        if detail:
            msg += f"\n📝 السبب المسجل كان: {detail}"
        msg += "\nℹ️ الكتم في المجموعات الأخرى (إن وجد) لم يتأثر."
    elif detail == "not_found":
        msg = f"❌ المستخدم <code>{uid}</code> غير مكتوم عالمياً"
    elif detail.startswith("reason_mismatch:"):
        stored = detail.split(":", 1)[1]
        msg = (
            f"❌ السبب غير متطابق!\n"
            f"السبب المسجل: <b>{stored or 'بدون سبب'}</b>\n"
            f"السبب المُدخل: <b>{reason}</b>\n\n"
            f"لرفع الكتم بدون تحقق السبب: <code>رفع كتم عالمي {uid}</code>"
        )
    else:
        msg = f"❌ حدث خطأ أثناء رفع الكتم عن <code>{uid}</code>"
    bot.reply_to(message, msg, parse_mode="HTML")


def _parse_mute_target(message, prefix: str) -> tuple[int | None, str]:
    """يستخرج (user_id, reason) من رسالة كتم."""
    if message.reply_to_message and message.reply_to_message.from_user:
        uid    = message.reply_to_message.from_user.id
        text   = message.text.strip()
        reason = text[len(prefix):].strip() if text.lower().startswith(prefix) else ""
        return uid, reason

    text  = message.text.strip()
    after = text[len(prefix):].strip() if text.lower().startswith(prefix) else text
    parts = after.split(maxsplit=1)
    if not parts:
        return None, ""
    uid_str = parts[0]
    reason  = parts[1] if len(parts) > 1 else ""
    if not uid_str.isdigit():
        return None, ""
    return int(uid_str), reason
