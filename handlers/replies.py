from core.bot import bot

from handlers.chat_responses.chat_handler import chat_responses
from handlers.general.general_handler import show_developer
from handlers.group_admin.admin_commands import custom_title, pin_message, delete_message
from handlers.group_admin.admin_commands import set_group_bio, set_group_name
from handlers.group_admin.developer import DEV_COMMANDS
from handlers.group_admin.developer.dev_panel import handle_dev_input
from handlers.group_admin.permissions import is_developer
from handlers.group_admin.restrictions import (
    ban_user, get_target_user,
    handle_muted_users, mute_user, restricted_user, unban_user,
    unmute_user, unrestricted_user
)
from handlers.misc.time_date import today_date, today_time
from handlers.games.games_handler import games_command
from handlers.tops.tops_handler import top_commands
from handlers.users import add_user_if_not_exists, send_user_profile, send_welcome, track_group_members
from modules.bank.commands.bank_commands import bank_commands
from modules.country.country_commands import country_commands
from modules.country.city_commands import city_commands
from modules.country.daily_tasks_commands import daily_tasks_commands
from modules.war.handlers.advanced_war_handler import handle_war_text_commands
from modules.alliances.alliance_commands import alliance_commands
from modules.tickets.ticket_callbacks import handle_ticket_commands, handle_ticket_media
from core import memory, intelligence
from core.admin import is_muted_anywhere, is_any_dev
from handlers.group_admin.developer.admin_panel import handle_admin_input, open_admin_panel
from handlers.group_admin.developer.dev_guide import open_dev_guide
from handlers.group_admin.developer.dev_store import open_dev_store, handle_dev_store_input

# =========================
# ⏹️ أوامر ثابتة
# =========================
commands = {
    "كتم": mute_user,
    "رفع الكتم": unmute_user,
    "حظر": ban_user,
    "رفع الحظر": unban_user,
    "تقييد": restricted_user,
    "رفع التقييد": unrestricted_user,
}


def receive_responses(message):
    """
    هذه الدالة الأساسية لمعالجة كل الرسائل الواردة
    """
    add_user_if_not_exists(message)
    track_group_members(message)

    # تجاهل الرسائل المكتمة (النظام القديم)
    if handle_muted_users(message):
        return

    # ─── فحص الكتم العالمي والمجموعة (النظام الجديد) ───
    chat_id_check = message.chat.id if message.chat.type != "private" else None
    if is_muted_anywhere(message.from_user.id, chat_id_check):
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception:
            pass
        return

    # ─── تتبع الذاكرة ───
    user_id = message.from_user.id
    memory.set_last_interaction(user_id, message.chat.type)

    # ─── معالجة الوسائط (صور، ملفات، إلخ) للتذاكر ───
    # if not message.text:
    #     handle_ticket_media(message)
    #     return

    text = message.text.strip()
    if not text:
        return

    normalized_text = text.lower()

    # ── Developer input intercept (must be first) ──────────────
    if handle_dev_input(message):
        return

    # ─── لوحة إدارة البوت (ثوابت، مطورون، كتم) ───
    if handle_admin_input(message):
        return

    # ─── متجر المطورين ───
    if handle_dev_store_input(message):
        return

    # ─── تسجيل الأمر في الذاكرة ───
    memory.set_last_command(user_id, text)

    # ─── نظام التذاكر (يجب أن يكون قبل باقي الأوامر) ───
    if handle_ticket_commands(message):
        return

    # ─── حالة انتظار رسالة التذكرة ───
    from utils.pagination.router import get_state
    if get_state(message.from_user.id, message.chat.id).get("state") == "awaiting_ticket_msg":
        from modules.tickets.ticket_handler import handle_ticket_message_input
        handle_ticket_message_input(message)
        return

    # =========================
    # أوامر عامة
    # =========================
    if normalized_text == "/start":
        send_welcome(message)
    
    if normalized_text == "المطور":
        show_developer(message)

    # -------------------------
    # 🏦 أوامر البنك
    # -------------------------
    elif bank_commands(message):
        return

    # -------------------------
    # 🎮 الألعاب
    # -------------------------
    elif games_command(message):
        return

    # -------------------------
    # 🏆 أوامر التوبات
    # -------------------------
    elif top_commands(message):  # ← سيتم التعامل مع كل التوبات الجديدة هنا
        return

    # -------------------------
    # 🌍 أوامر الدولة
    # -------------------------
    elif country_commands(message):
        return

    elif city_commands(message):
        return

    elif daily_tasks_commands(message):
        return

    # -------------------------
    # 🏰 أوامر التحالفات
    # -------------------------
    elif alliance_commands(message):
        return

    # -------------------------
    # 🗓 الوقت والتاريخ
    # -------------------------
    elif normalized_text in ["اليوم"]:
        today_date(message)

    elif normalized_text in ["كم الساعة", "كم الساعه", "الساعة كم", "الساعه كم", "الوقت"]:
        today_time(message)

    # -------------------------
    # ⚔️ نظام الحرب
    # -------------------------
    elif handle_war_text_commands(message):
        return

    # -------------------------
    # 🛠 لوحة إدارة البوت
    # -------------------------
    elif normalized_text in ["لوحة الإدارة", "لوحة الادارة", "ثوابت البوت", "/admin"]:
        open_admin_panel(message)
        return

    # ─── دليل المطور ───
    elif normalized_text in ["شرح المطور", "دليل المطور"]:
        open_dev_guide(message)
        return

    # ─── متجر المطورين ───
    elif normalized_text in ["متجر المطورين", "متجر المطور", "dev store"] and is_any_dev(message.from_user.id):
        open_dev_store(message)
        return

    # ─── إنجازاتي ───
    elif normalized_text in ["إنجازاتي", "انجازاتي", "الإنجازات"]:
        _show_achievements(message)
        return

    # ─── تقدمي ───
    elif normalized_text in ["تقدمي", "تقدم"]:
        _show_progress(message)
        return

    # ─── النفوذ ───
    elif normalized_text in ["نفوذي", "تأثيري"]:
        _show_influence(message)
        return

    # ─── الأحداث العالمية ───
    elif normalized_text in ["الأحداث", "حدث", "الاحداث"]:
        _show_global_event(message)
        return

    # ─── الموسم ───
    elif normalized_text in ["الموسم", "موسم"]:
        _show_season(message)
        return

    # ─── تحديث جروب البوت ───
    elif normalized_text in ["تحديث جروب البوت", "تعيين جروب البوت"] and is_any_dev(message.from_user.id):
        from core.admin import set_const
        group_id = str(message.chat.id)
        set_const("dev_group_id", group_id)
        # تحديث ticket handler
        try:
            import modules.tickets.ticket_handler as _th
            _th.DEV_GROUP_ID = int(group_id)
        except Exception:
            pass
        bot.reply_to(message, f"✅ تم تعيين هذه المجموعة كجروب البوت الرئيسي\nID: <code>{group_id}</code>",
                     parse_mode="HTML")
        return

    # ─── أوامر الكتم العالمي النصية ───
    elif normalized_text.startswith("كتم عالمي ") and is_any_dev(message.from_user.id):
        _handle_global_mute_cmd(message)
        return

    elif normalized_text.startswith("رفع كتم عالمي ") and is_any_dev(message.from_user.id):
        _handle_global_unmute_cmd(message)
        return
    # -------------------------
    # 👨‍💻 أوامر المطور
    # -------------------------
    elif normalized_text in DEV_COMMANDS:
        if is_developer(message):
            cmd_info = DEV_COMMANDS[normalized_text]
            func = cmd_info["func"]
            needs_user = cmd_info.get("needs_user", False)

            if needs_user:
                user_id, _ = get_target_user(message)
                if not user_id:
                    bot.reply_to(message, "حدد المستخدم بالرد أو الايدي أو اليوزر")
                    return
                func(message, user_id)
            else:
                func(message)
            return
        else:
            return

    # -------------------------
    # 📌 أوامر المجموعة
    # -------------------------
    elif normalized_text == "مسح":
        delete_message(message)

    elif normalized_text == "تثبيت":
        pin_message(message)

    elif normalized_text == "لقبي":
        custom_title(message)

    elif normalized_text == 'تعيين اسم المجموعة':
        set_group_name(message)

    elif normalized_text == 'تعيين بايو المجموعة':
        set_group_bio(message)

    # -------------------------
    # 🧾 أوامر الملف الشخصي
    # -------------------------
    elif text in ["عني", "ايدي", "معلوماتي"] or text.startswith("ايدي"):
        send_user_profile(message)  

    elif normalized_text in ["عنه", "معلوماته"]:
        send_user_profile(message)
    # -------------------------
    # البحث عن أوامر محددة
    # -------------------------
    else:
        for command_name, func in commands.items():
            if normalized_text.startswith(command_name):
                user_id, _ = get_target_user(message)
                if not user_id:
                    bot.reply_to(message, "حدد المستخدم بالرد أو الايدي أو اليوزر")
                    return
                func(message)
                return

    # -------------------------
    # 💬 الردود التلقائية
    # -------------------------
    # ─── متابعة المستخدم لتذكرة مفتوحة (في الخاص) ───
    if message.chat.type == "private":
        from modules.tickets.ticket_handler import handle_user_followup
        if handle_user_followup(message):
            return

    chat_responses(message)


# ══════════════════════════════════════════
# 🔇 أوامر الكتم النصية السريعة
# ══════════════════════════════════════════

def _handle_global_mute_cmd(message):
    """كتم عالمي [ID] [السبب]"""
    from core.admin import global_mute
    parts = message.text.strip().split(maxsplit=2)
    if len(parts) < 2:
        bot.reply_to(message, "❌ الصيغة: كتم عالمي [ID] [السبب]")
        return
    uid_str = parts[1]
    reason  = parts[2] if len(parts) > 2 else ""
    if not uid_str.isdigit():
        bot.reply_to(message, "❌ ID غير صالح")
        return
    global_mute(int(uid_str), message.from_user.id, reason)
    bot.reply_to(message, f"🔇 تم الكتم العالمي للمستخدم <code>{uid_str}</code>",
                 parse_mode="HTML")


def _handle_global_unmute_cmd(message):
    """رفع كتم عالمي [ID]"""
    from core.admin import global_unmute
    parts = message.text.strip().split()
    if len(parts) < 3:
        bot.reply_to(message, "❌ الصيغة: رفع كتم عالمي [ID]")
        return
    uid_str = parts[2]
    if not uid_str.isdigit():
        bot.reply_to(message, "❌ ID غير صالح")
        return
    ok = global_unmute(int(uid_str))
    bot.reply_to(message, f"✅ تم رفع الكتم العالمي" if ok else "❌ المستخدم غير مكتوم عالمياً")


# ══════════════════════════════════════════
# 🏅 عرض الإنجازات
# ══════════════════════════════════════════

def _show_achievements(message):
    user_id = message.from_user.id
    try:
        from modules.progression.achievements import get_user_achievements
        achievements = get_user_achievements(user_id)
        if not achievements:
            bot.reply_to(message, "🏅 لم تحصل على أي إنجازات بعد!\nاستمر في اللعب لكسب الإنجازات.",
                         parse_mode="HTML")
            return
        text = f"🏅 <b>إنجازاتك ({len(achievements)})</b>\n━━━━━━━━━━━━━━━\n\n"
        for a in achievements[:15]:
            import time as _t
            ts = _t.strftime("%Y-%m-%d", _t.localtime(a["unlocked_at"]))
            text += f"{a['emoji']} <b>{a['name_ar']}</b> — {ts}\n"

        # إضافة لقب الموسم إذا وجد
        from modules.progression.seasons import get_latest_title
        title = get_latest_title(user_id)
        if title:
            text += f"\n🏆 <b>لقبك الموسمي:</b> {title}"

        bot.reply_to(message, text, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")


def _show_progress(message):
    """يعرض التقدم نحو الإنجازات القادمة"""
    user_id = message.from_user.id
    try:
        from modules.progression.achievements import get_achievement_progress
        progress = get_achievement_progress(user_id)
        if not progress:
            bot.reply_to(message, "✅ أنجزت كل الإنجازات المتاحة!", parse_mode="HTML")
            return
        text = "📈 <b>تقدمك نحو الإنجازات القادمة</b>\n━━━━━━━━━━━━━━━\n\n"
        for p in progress:
            text += (
                f"{p['emoji']} <b>{p['name_ar']}</b>\n"
                f"  [{p['bar']}] {p['progress']}%\n"
                f"  {p['current']}/{p['target']} — {p['description_ar']}\n\n"
            )
        bot.reply_to(message, text, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")


# ══════════════════════════════════════════
# 🌍 عرض النفوذ
# ══════════════════════════════════════════

def _show_influence(message):
    user_id = message.from_user.id
    try:
        from database.db_queries.countries_queries import get_country_by_owner
        from modules.progression.influence import get_influence_display
        country = get_country_by_owner(user_id)
        if not country:
            bot.reply_to(message, "❌ لا تملك دولة!")
            return
        country = dict(country)
        text = get_influence_display(country["id"])
        bot.reply_to(message, text, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")


def _show_global_event(message):
    """يعرض الحدث العالمي النشط"""
    try:
        from modules.progression.global_events import get_active_event, get_recent_events
        import time as _t
        event = get_active_event()
        if event:
            remaining = max(0, event["ends_at"] - int(_t.time()))
            hours = remaining // 3600
            mins  = (remaining % 3600) // 60
            text = (
                f"{event['emoji']} <b>حدث عالمي نشط!</b>\n\n"
                f"<b>{event['name_ar']}</b>\n"
                f"📝 {event['description_ar']}\n"
                f"⏱️ ينتهي خلال: {hours}س {mins}د"
            )
        else:
            recent = get_recent_events(3)
            text = "🌍 <b>لا يوجد حدث نشط حالياً</b>\n\n"
            if recent:
                text += "📋 <b>آخر الأحداث:</b>\n"
                for e in recent:
                    ts = _t.strftime("%m/%d", _t.localtime(e["started_at"]))
                    text += f"{e['emoji']} {e['name_ar']} — {ts}\n"
        bot.reply_to(message, text, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")


def _show_season(message):
    """يعرض حالة الموسم الحالي"""
    try:
        from modules.progression.seasons import get_season_status, get_season_leaderboard, get_active_season
        status = get_season_status()
        if not status["active"]:
            bot.reply_to(message, "🗓 لا يوجد موسم نشط حالياً.", parse_mode="HTML")
            return

        season = get_active_season()
        text = (
            f"🏆 <b>الموسم الحالي: {status['name']}</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"⏱️ ينتهي خلال: {status['days_left']} يوم {status['hours_left']} ساعة\n\n"
        )

        # توب المعارك
        lb = get_season_leaderboard(season["id"], "battles")
        if lb:
            text += "⚔️ <b>توب المعارك:</b>\n"
            medals = ["🥇", "🥈", "🥉"]
            for i, row in enumerate(lb[:3]):
                m = medals[i] if i < 3 else f"{i+1}."
                text += f"{m} {row.get('user_name','مجهول')} — {row['score']:.0f}\n"

        bot.reply_to(message, text, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")
