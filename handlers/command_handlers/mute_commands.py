"""
أوامر الكتم العالمي النصية السريعة — للمطورين فقط.
"""
from core.bot import bot


def handle_global_mute_cmd(message):
    """
    كتم عالمي — يدعم:
    1. رد على رسالة: "كتم عالمي [سبب اختياري]"
    2. @username:    "كتم عالمي @user [سبب]"
    3. نص مباشر:    "كتم عالمي [ID] [سبب اختياري]"
    """
    from core.admin import global_mute
    from handlers.group_admin.restrictions import resolve_user
    from handlers.group_admin.permissions import can_delete_messages

    uid, name, err = resolve_user(message)
    if uid is None:
        bot.reply_to(message,
                     err or (
                         "❌ الصيغة:\n"
                         "• رد على رسالة: <code>كتم عالمي [السبب]</code>\n"
                         "• أو: <code>كتم عالمي @username [السبب]</code>\n"
                         "• أو: <code>كتم عالمي [ID] [السبب]</code>"
                     ),
                     parse_mode="HTML")
        return

    # استخراج السبب من نهاية النص
    text   = (message.text or "").strip()
    parts  = text.split(maxsplit=2)
    reason = parts[2] if len(parts) >= 3 else ""

    global_mute(uid, message.from_user.id, reason)

    # حذف صامت إذا كان للبوت صلاحية
    if can_delete_messages(message.chat.id):
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception:
            pass

    bot.reply_to(message,
                 f"🔇 تم الكتم العالمي للمستخدم <code>{uid}</code>"
                 + (f" ({name})" if name and name != str(uid) else "")
                 + (f"\n📝 السبب: {reason}" if reason else ""),
                 parse_mode="HTML")


def handle_global_unmute_cmd(message):
    """
    رفع كتم عالمي — يدعم رد / @username / ID.
    السبب غير مطلوب ولا يُتحقق منه.
    """
    from core.admin import global_unmute
    from handlers.group_admin.restrictions import resolve_user

    uid, name, err = resolve_user(message)
    if uid is None:
        bot.reply_to(message,
                     err or (
                         "❌ الصيغة:\n"
                         "• رد على رسالة: <code>رفع كتم عالمي</code>\n"
                         "• أو: <code>رفع كتم عالمي @username</code>\n"
                         "• أو: <code>رفع كتم عالمي [ID]</code>"
                     ),
                     parse_mode="HTML")
        return

    ok, detail = global_unmute(uid)
    if ok:
        msg = f"✅ تم رفع الكتم العالمي عن <code>{uid}</code>"
        if name and name != str(uid):
            msg += f" ({name})"
        msg += "\nℹ️ الكتم في المجموعات الأخرى (إن وجد) لم يتأثر."
    elif detail == "not_found":
        msg = f"❌ المستخدم <code>{uid}</code> غير مكتوم عالمياً"
    else:
        msg = f"❌ حدث خطأ أثناء رفع الكتم عن <code>{uid}</code>"

    bot.reply_to(message, msg, parse_mode="HTML")
