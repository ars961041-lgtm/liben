from core.bot import bot
from database.db_queries.cities_queries import city_exists, create_city, get_user_city
from database.db_queries.countries_queries import (
    attach_user_to_country, create_invite, get_pending_invite,
    get_user_country, has_pending_invite, update_invite_status
)
from utils.pagination.buttons import btn
from utils.pagination.ui import edit_ui, send_ui
from utils.pagination.router import register_action
from utils.helpers import get_lines


def handle_join_command(message):
    from_user = message.from_user.id

    if not message.reply_to_message:
        bot.reply_to(message, "❌ لازم ترد على الشخص")
        return

    to_user    = message.reply_to_message.from_user.id
    to_name    = message.reply_to_message.from_user.first_name or str(to_user)

    country = get_user_country(from_user)
    if not country:
        bot.reply_to(message, "❌ لازم يكون عندك دولة أولاً")
        return

    if get_user_city(to_user):
        bot.reply_to(message, "❌ هذا الشخص عنده مدينة بالفعل")
        return

    if has_pending_invite(to_user):
        bot.reply_to(message, "❌ هذا الشخص عنده دعوة معلقة بالفعل")
        return

    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ اكتب اسم المدينة\nمثال: <code>ضم [اسم المدينة]</code>",
                     parse_mode="HTML")
        return

    if len(parts[1:]) > 3:
        bot.reply_to(message, "❌ اسم المدينة طويل جداً (3 كلمات كحد أقصى)")
        return

    city_name = " ".join(parts[1:]).strip()

    if len(city_name) < 2:
        bot.reply_to(message, "❌ الاسم قصير جداً")
        return

    if city_exists(city_name):
        bot.reply_to(message, "❌ المدينة موجودة مسبقاً، اختر اسماً آخر")
        return

    invite_id = create_invite(from_user, to_user, country["id"], city_name)

    owner = (to_user, message.chat.id)
    text = (
        f"📩 <b>دعوة انضمام لدولة</b>\n"
        f"{get_lines()}\n"
        f"🏳️ الدولة: <b>{country['name']}</b>\n"
        f"🏙 المدينة المقترحة: <b>{city_name}</b>\n"
        f"👤 من: <b>{message.from_user.first_name}</b>\n\n"
        f"هل تريد الانضمام؟"
    )

    buttons = [
        btn("✅ قبول", "accept_invite", owner=owner, color="su"),
        btn("❌ رفض",  "reject_invite", owner=owner, color="d")
    ]

    # ─── محاولة إرسال الدعوة للمستخدم ───
    sent = False
    try:
        send_ui(to_user, text=text, buttons=buttons, layout=[2], owner_id=to_user)
        sent = True
    except Exception as e:
        err_str = str(e)
        if "403" in err_str or "Forbidden" in err_str or "bot was blocked" in err_str.lower():
            # المستخدم حجب البوت أو لم يبدأ محادثة
            update_invite_status(invite_id, "rejected")
            bot.reply_to(
                message,
                f"❌ لا يمكن إرسال الدعوة لـ <b>{to_name}</b>\n"
                f"يجب أن يبدأ المستخدم محادثة مع البوت أولاً.",
                parse_mode="HTML"
            )
        else:
            bot.reply_to(message, f"❌ خطأ أثناء إرسال الدعوة: {e}")
        return

    if sent:
        bot.reply_to(
            message,
            f"✅ تم إرسال دعوة الانضمام لـ <b>{to_name}</b>\n"
            f"🏙 المدينة: <b>{city_name}</b>",
            parse_mode="HTML"
        )


@register_action("accept_invite")
def accept_invite(call, data):
    user_id = call.from_user.id
    owner   = (user_id, call.message.chat.id)

    invite = get_pending_invite(user_id)
    if not invite:
        bot.answer_callback_query(call.id, "❌ لا توجد دعوة معلقة", show_alert=True)
        return

    # تحقق أن المدينة لم تُنشأ بعد
    if city_exists(invite["city_name"]):
        update_invite_status(invite["id"], "rejected")
        bot.answer_callback_query(call.id, "❌ اسم المدينة محجوز بالفعل، تواصل مع صاحب الدولة",
                                  show_alert=True)
        return

    city_id = create_city(invite["city_name"], user_id, invite["country_id"])
    attach_user_to_country(user_id, city_id, invite["country_id"])
    update_invite_status(invite["id"], "accepted")

    # إشعار صاحب الدولة
    try:
        from database.db_queries.countries_queries import get_user_country
        country_owner_country = get_user_country(invite["from_user_id"])
        bot.send_message(
            invite["from_user_id"],
            f"✅ <b>{call.from_user.first_name}</b> قبل الدعوة وانضم لدولتك!\n"
            f"🏙 المدينة: <b>{invite['city_name']}</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass

    bot.answer_callback_query(call.id)
    edit_ui(
        call,
        text=(
            f"✅ <b>تم الانضمام بنجاح!</b>\n"
            f"🏙 مدينتك: <b>{invite['city_name']}</b>\n\n"
            f"اكتب <code>دولتي</code> لعرض دولتك."
        ),
        buttons=[btn("🌍 عرض الدولة", "country_back",
                     {"cid": invite["country_id"]}, color="su",
                     owner=owner)],
        layout=[1]
    )


@register_action("reject_invite")
def reject_invite(call, data):
    user_id = call.from_user.id

    invite = get_pending_invite(user_id)
    if not invite:
        bot.answer_callback_query(call.id, "❌ لا توجد دعوة", show_alert=True)
        return

    update_invite_status(invite["id"], "rejected")

    # إشعار صاحب الدولة
    try:
        bot.send_message(
            invite["from_user_id"],
            f"❌ <b>{call.from_user.first_name}</b> رفض دعوة الانضمام لمدينة <b>{invite['city_name']}</b>.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(
            "❌ تم رفض الدعوة.",
            call.message.chat.id,
            call.message.message_id
        )
    except Exception:
        pass
