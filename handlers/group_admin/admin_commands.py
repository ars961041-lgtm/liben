from core.bot import bot
from database.reset_db import reset_database
from database.update_db import update_database
from handlers.group_admin.permissions import (
    is_admin, is_developer,
    sender_can_delete, sender_can_pin,
    can_delete_messages, can_pin_messages,
)


def _reply(message, text):
    bot.reply_to(message, text, parse_mode="HTML", disable_web_page_preview=True)


# ── Group info ────────────────────────────────────────────────────────────────

def set_group_name(message):
    if not is_admin(message):
        _reply(message, "❌ أنت لست مشرفاً في هذه المجموعة.")
        return
    if not message.reply_to_message or not message.reply_to_message.text:
        _reply(message, "❌ يرجى الرد على النص الذي تريد تعيينه اسماً للمجموعة.")
        return
    try:
        bot.set_chat_title(message.chat.id, message.reply_to_message.text)
        _reply(message, "✅ تم تغيير اسم المجموعة.")
    except Exception as e:
        _reply(message, f"❌ فشل تغيير الاسم: {e}")


def set_group_bio(message):
    if not is_admin(message):
        _reply(message, "❌ أنت لست مشرفاً في هذه المجموعة.")
        return
    if not message.reply_to_message or not message.reply_to_message.text:
        _reply(message, "❌ يرجى الرد على النص الذي تريد تعيينه وصفاً للمجموعة.")
        return
    try:
        bot.set_chat_description(message.chat.id, message.reply_to_message.text)
        _reply(message, "✅ تم تغيير وصف المجموعة.")
    except Exception as e:
        _reply(message, f"❌ فشل تغيير الوصف: {e}")


def custom_title(message):
    if not is_admin(message):
        _reply(message, "❌ أنت لست مشرفاً في هذه المجموعة.")
        return
    try:
        member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if member.custom_title:
            _reply(message, f"🏷 لقبك: <b>{member.custom_title}</b>")
        else:
            _reply(message, "ℹ️ ليس لديك لقب مخصص.")
    except Exception as e:
        _reply(message, f"❌ خطأ: {e}")


# ── Delete message ────────────────────────────────────────────────────────────

def delete_message(message):
    ok, err = sender_can_delete(message)
    if not ok:
        _reply(message, err)
        return

    if not can_delete_messages(message.chat.id):
        _reply(message, (
            "⛔ البوت لا يملك صلاحية <b>حذف الرسائل</b>.\n"
            "Bot lacks the <b>Delete Messages</b> permission."
        ))
        return

    if not message.reply_to_message:
        _reply(message, "❌ يجب الرد على الرسالة المراد حذفها.")
        return

    try:
        bot.delete_message(message.chat.id, message.reply_to_message.message_id)
    except Exception as e:
        _reply(message, f"❌ فشل الحذف: {e}")


# ── Pin message ───────────────────────────────────────────────────────────────

def pin_message(message):
    ok, err = sender_can_pin(message)
    if not ok:
        _reply(message, err)
        return

    if not can_pin_messages(message.chat.id):
        _reply(message, (
            "⛔ البوت لا يملك صلاحية <b>تثبيت الرسائل</b>.\n"
            "Bot lacks the <b>Pin Messages</b> permission."
        ))
        return

    if not message.reply_to_message:
        _reply(message, "❌ يجب الرد على الرسالة المراد تثبيتها.")
        return

    try:
        bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
        _reply(message, "📌 تم تثبيت الرسالة.")
    except Exception as e:
        _reply(message, f"❌ فشل التثبيت: {e}")


# ── DB management (developer only) ───────────────────────────────────────────

def reset_db(message):
    if not is_developer(message):
        return
    ok, msg = reset_database()
    _reply(message, msg if msg else ("✅ تم إعادة إنشاء قاعدة البيانات." if ok else "❌ فشلت إعادة الإنشاء."))


def update_db(message):
    if not is_developer(message):
        return
    try:
        update_database()
        _reply(message, "✅ تم تحديث قاعدة البيانات بنجاح.")
    except Exception as e:
        _reply(message, f"❌ خطأ أثناء التحديث: {e}")
