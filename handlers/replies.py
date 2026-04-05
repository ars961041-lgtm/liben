from core.bot import bot
from core.state_manager import StateManager
from utils.logger import log_event
from utils.helpers import send_result, get_lines

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
from handlers.games.entertainment_games import entertainment_games_command
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
from core.admin import is_muted_anywhere, is_any_dev, is_globally_muted, is_group_muted
from handlers.group_admin.developer.admin_panel import handle_admin_input, open_admin_panel
from handlers.group_admin.developer.dev_guide import open_dev_guide
from handlers.group_admin.developer.dev_store import open_dev_store, handle_dev_store_input
from modules.formatting.format_handler import handle_format_command, handle_format_guide
from modules.text_tools.replace_handler import handle_replace_command
from modules.content_hub.hub_handler import (
    handle_content_command, handle_add_content_command, handle_hub_input
)
from modules.quran.quran_handler import (
    handle_quran_commands, handle_dev_quran_input
)
from handlers.group_admin.developer.dev_control_panel import handle_developer_input
from handlers.group_admin.promote import handle_promote_command, handle_promote_input
from handlers.group_admin.promote.promote_handler import handle_edit_command

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


def _in_private(message):
    # ══════════════════════════════════════════
    # 7. أوامر عامة
    # ══════════════════════════════════════════
    if message == "/start":
        send_welcome(message)
        return

    if message == "المطور":
        show_developer(message)
        return

def is_group(message):
    # ══════════════════════════════════════════
    # 1b. حماية الخاص — الأوامر الجماعية فقط في المجموعات
    # ══════════════════════════════════════════

    return message.chat.type in ("group", "supergroup")


def _dispatch(message):
    """المعالج الداخلي — يُلفّه receive_responses بحدود الخطأ."""
    add_user_if_not_exists(message)
    track_group_members(message)

    uid = message.from_user.id
    cid = message.chat.id

    # ══════════════════════════════════════════
    # 0. كشف انتهاء الجلسة (TTL)
    # ══════════════════════════════════════════
    from utils.pagination.router import get_state as _gs
    _flow_state = _gs(uid, cid)
    _sm_state   = StateManager.get(uid, cid)
    # إذا كانت هناك جلسة pagination منتهية ولا توجد حالة نشطة في StateManager
    if _flow_state.get("state") and not _sm_state:
        send_result(
            chat_id=cid,
            text="⚠️ انتهت العملية بسبب عدم التفاعل",
        )
        return

    # ══════════════════════════════════════════
    # 1. فحص الكتم — أولوية قصوى
    # ══════════════════════════════════════════
    if is_globally_muted(uid):
        try:
            bot.delete_message(cid, message.message_id)
        except Exception:
            pass
        return

    if message.chat.type != "private" and is_group_muted(uid, cid):
        try:
            bot.delete_message(cid, message.message_id)
        except Exception:
            pass
        return

    if handle_muted_users(message):
        return


    # ══════════════════════════════════════════
    # 2. تتبع الذاكرة
    # ══════════════════════════════════════════
    memory.set_last_interaction(uid, message.chat.type)

    if not message.text:
        return

    text            = message.text.strip()
    normalized_text = text.lower()

    if not text:
        return

    # ══════════════════════════════════════════
    # 3. معالجات الإدخال النصي (حالات الانتظار)
    # ══════════════════════════════════════════
    if handle_dev_input(message):          return
    if handle_admin_input(message):        return
    if handle_dev_store_input(message):    return
    if handle_developer_input(message):    return
    if handle_dev_quran_input(message):    return
    if handle_hub_input(message):          return
    if handle_promote_input(message):      return

    # ══════════════════════════════════════════
    # 4. تسجيل الأمر في الذاكرة
    # ══════════════════════════════════════════
    memory.set_last_command(uid, text)

    # ══════════════════════════════════════════
    # 5. نظام التذاكر
    # ══════════════════════════════════════════
    if handle_ticket_commands(message):
        return

    from utils.pagination.router import get_state as _gs
    if _gs(uid, cid).get("state") == "awaiting_ticket_msg":
        from modules.tickets.ticket_handler import handle_ticket_message_input
        handle_ticket_message_input(message)
        return

    # ══════════════════════════════════════════
    # 6. أوامر المطور
    # ══════════════════════════════════════════
    if is_any_dev(uid):
        if normalized_text.startswith("كتم عالمي "):
            _handle_global_mute_cmd(message)
            return
        if normalized_text.startswith("رفع كتم عالمي "):
            _handle_global_unmute_cmd(message)
            return
        if normalized_text in ["تحديث جروب البوت", "تعيين جروب البوت"]:
            _set_dev_group(message)
            return
        if normalized_text in ["متجر المطورين", "متجر المطور", "dev store"]:
            open_dev_store(message)
            return
        if normalized_text in ["لوحة المطور", "dev panel"]:
            from handlers.group_admin.developer.dev_control_panel import open_developer_panel
            open_developer_panel(message)
            return
        if text.startswith("اضف "):
            if handle_add_content_command(message):
                return


    # ── ترقية / تعديل مشرف ──
    if normalized_text in ["/promote", "رفع مشرف"]:
        handle_promote_command(message)
        return
    if normalized_text in ["/edit_admin", "تعديل مشرف"]:
        handle_edit_command(message)
        return

    # ══════════════════════════════════════════
    # 8. البنك
    # ══════════════════════════════════════════
    if bank_commands(message):
        return

    # ══════════════════════════════════════════
    # 9. الألعاب
    # ══════════════════════════════════════════
    if games_command(message):
        return
    if entertainment_games_command(message):
        return

    # ══════════════════════════════════════════
    # 10. التوبات
    # ══════════════════════════════════════════
    if top_commands(message):
        return

    # ══════════════════════════════════════════
    # 11. الدولة والمدن
    # ══════════════════════════════════════════
    if country_commands(message):   return
    if city_commands(message):      return
    if daily_tasks_commands(message): return

    # ══════════════════════════════════════════
    # 12. التحالفات
    # ══════════════════════════════════════════
    if alliance_commands(message):
        return

    # ══════════════════════════════════════════
    # 13. الحرب
    # ══════════════════════════════════════════
    if handle_war_text_commands(message):
        return

    # ══════════════════════════════════════════
    # 14. القرآن
    # ══════════════════════════════════════════
    if handle_quran_commands(message):
        return

    # ══════════════════════════════════════════
    # 15. مركز المحتوى
    # ══════════════════════════════════════════
    if handle_content_command(message):
        return

    # ══════════════════════════════════════════
    # 16. التنسيق والاستبدال
    # ══════════════════════════════════════════
    if normalized_text == "تنسيق":
        handle_format_command(message)
        return
    if normalized_text in ["شرح تنسيق", "دليل التنسيق"]:
        handle_format_guide(message)
        return
    if text.startswith("تعديل "):
        handle_replace_command(message)
        return

    # ══════════════════════════════════════════
    # 17. الوقت والتاريخ
    # ══════════════════════════════════════════
    if normalized_text == "اليوم":
        today_date(message)
        return
    if normalized_text in ["كم الساعة", "كم الساعه", "الساعة كم", "الساعه كم", "الوقت"]:
        today_time(message)
        return

    # ══════════════════════════════════════════
    # 18. لوحة الإدارة ودليل المطور
    # ══════════════════════════════════════════
    if normalized_text in ["لوحة الإدارة", "لوحة الادارة", "ثوابت البوت", "/admin"]:
        open_admin_panel(message)
        return
    if normalized_text in ["شرح المطور", "دليل المطور"]:
        open_dev_guide(message)
        return

    # ══════════════════════════════════════════
    # 19. الإنجازات والتقدم والنفوذ والمواسم
    # ══════════════════════════════════════════
    if normalized_text in ["إنجازاتي", "انجازاتي", "الإنجازات"]:
        _show_achievements(message)
        return
    if normalized_text in ["تقدمي", "تقدم"]:
        _show_progress(message)
        return
    if normalized_text in ["نفوذي", "تأثيري"]:
        _show_influence(message)
        return
    if normalized_text in ["الأحداث", "حدث", "الاحداث"]:
        _show_global_event(message)
        return
    if normalized_text in ["الموسم", "موسم"]:
        _show_season(message)
        return

    # ══════════════════════════════════════════
    # 20. أوامر المطور (DEV_COMMANDS)
    # ══════════════════════════════════════════
    if normalized_text in DEV_COMMANDS:
        if is_developer(message):
            cmd_info   = DEV_COMMANDS[normalized_text]
            func       = cmd_info["func"]
            needs_user = cmd_info.get("needs_user", False)
            if needs_user:
                target_uid, _ = get_target_user(message)
                if not target_uid:
                    bot.reply_to(message, "حدد المستخدم بالرد أو الايدي أو اليوزر")
                    return
                func(message, target_uid)
            else:
                func(message)
        return

    # ══════════════════════════════════════════
    # 21. أوامر المجموعة
    # ══════════════════════════════════════════
    if normalized_text == "مسح":
        delete_message(message)
        return
    if normalized_text == "تثبيت":
        pin_message(message)
        return
    if normalized_text == "لقبي":
        custom_title(message)
        return
    if normalized_text == "تعيين اسم المجموعة":
        set_group_name(message)
        return
    if normalized_text == "تعيين بايو المجموعة":
        set_group_bio(message)
        return

    # ══════════════════════════════════════════
    # 22. الملف الشخصي
    # ══════════════════════════════════════════
    if text in ["عني", "ايدي", "معلوماتي"] or text.startswith("ايدي"):
        send_user_profile(message)
        return
    if normalized_text in ["عنه", "معلوماته"]:
        send_user_profile(message)
        return

    # ══════════════════════════════════════════
    # 23. أوامر الكتم/الحظر (prefix-based)
    # ══════════════════════════════════════════
    for command_name, func in commands.items():
        if normalized_text.startswith(command_name):
            target_uid, _ = get_target_user(message)
            if not target_uid:
                bot.reply_to(message, "حدد المستخدم بالرد أو الايدي أو اليوزر")
                return
            func(message)
            return

    # ══════════════════════════════════════════
    # 24. متابعة التذاكر المفتوحة (الخاص فقط)
    # ══════════════════════════════════════════
    if message.chat.type == "private":
        from modules.tickets.ticket_handler import handle_user_followup
        if handle_user_followup(message):
            return

    # ══════════════════════════════════════════
    # 25. الردود التلقائية
    # ══════════════════════════════════════════
    chat_responses(message)


def receive_responses(message):
    """
    نقطة الدخول الرئيسية — حدود الخطأ الإلزامية.
    أي استثناء يُنظّف الحالة ويُبلّغ المستخدم فوراً.
    """
    uid = message.from_user.id
    cid = message.chat.id
    state = StateManager.get(uid, cid)

    try:
        _in_private(message)
        if is_group(message):
            _dispatch(message)
        
    except Exception as e:
        StateManager.clear(uid, cid)
        log_event("flow_error", user=uid, chat=cid, error=str(e), state=state)
        send_result(
            chat_id=cid,
            text="❌ حدث خطأ أثناء التنفيذ، تم إلغاء العملية",
        )


def _set_dev_group(message):
    from core.admin import set_const
    group_id = str(message.chat.id)
    set_const("dev_group_id", group_id)
    try:
        import modules.tickets.ticket_handler as _th
        _th.DEV_GROUP_ID = int(group_id)
    except Exception:
        pass
    bot.reply_to(message,
                 f"✅ تم تعيين هذه المجموعة كجروب البوت الرئيسي\nID: <code>{group_id}</code>",
                 parse_mode="HTML")


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
        text = f"🏅 <b>إنجازاتك ({len(achievements)})</b>\n{get_lines()}\n\n"
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
        text = "📈 <b>تقدمك نحو الإنجازات القادمة</b>\n{get_lines()}\n\n"
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
            f"{get_lines()}\n"
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
