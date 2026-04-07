"""
أوامر التقدم والإنجازات والنفوذ والمواسم والأحداث العالمية.
متاحة في المجموعات والخاص.
"""
from core.bot import bot
from utils.helpers import get_lines
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME


def show_achievements(message):
    user_id = message.from_user.id
    try:
        from modules.progression.achievements import get_user_achievements
        achievements = get_user_achievements(user_id)
        if not achievements:
            bot.reply_to(message,
                         "🏅 لم تحصل على أي إنجازات بعد!\nاستمر في اللعب لكسب الإنجازات.",
                         parse_mode="HTML")
            return
        text = f"🏅 <b>إنجازاتك ({len(achievements)})</b>\n{get_lines()}\n\n"
        for a in achievements[:15]:
            import time as _t
            ts = _t.strftime("%Y-%m-%d", _t.localtime(a["unlocked_at"]))
            text += f"{a['emoji']} <b>{a['name_ar']}</b> — {ts}\n"
        from modules.progression.seasons import get_latest_title
        title = get_latest_title(user_id)
        if title:
            text += f"\n🏆 <b>لقبك الموسمي:</b> {title}"
        bot.reply_to(message, text, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")


def show_progress(message):
    user_id = message.from_user.id
    try:
        from modules.progression.achievements import get_achievement_progress
        progress = get_achievement_progress(user_id)
        if not progress:
            bot.reply_to(message, "✅ أنجزت كل الإنجازات المتاحة!", parse_mode="HTML")
            return
        text = f"📈 <b>تقدمك نحو الإنجازات القادمة</b>\n{get_lines()}\n\n"
        for p in progress:
            text += (
                f"{p['emoji']} <b>{p['name_ar']}</b>\n"
                f"  [{p['bar']}] {p['progress']}%\n"
                f"  {p['current']}/{p['target']} — {p['description_ar']}\n\n"
            )
        bot.reply_to(message, text, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")


def show_influence(message):
    user_id = message.from_user.id
    try:
        from database.db_queries.countries_queries import get_country_by_owner
        from modules.progression.influence import get_influence_display
        country = get_country_by_owner(user_id)
        if not country:
            bot.reply_to(message, "❌ لا تملك دولة!")
            return
        text = get_influence_display(dict(country)["id"])
        bot.reply_to(message, text, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")


def show_global_event(message):
    try:
        from modules.progression.global_events import get_events_page
        bot.reply_to(message, get_events_page(), parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")


def show_season(message):
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


def collect_city_income(message):
    """جمع دخل المدن يدوياً — كولداون 6 ساعات"""
    user_id = message.from_user.id
    try:
        from database.db_queries.countries_queries import get_country_by_owner
        from modules.economy.economy_service import (
            collect_income_for_country, can_collect_income, get_income_summary
        )
        country = get_country_by_owner(user_id)
        if not country:
            bot.reply_to(message, "❌ ليس لديك دولة. أنشئ دولة أولاً.")
            return
        country_id = dict(country)["id"]
        can, remaining = can_collect_income(country_id)
        if not can:
            summary = get_income_summary(country_id)
            h, m = remaining // 3600, (remaining % 3600) // 60
            bot.reply_to(message,
                f"⏳ يمكنك جمع الدخل بعد <b>{h}س {m}د</b>\n\n"
                f"💰 الدخل المتوقع: {summary['income']:.0f} {CURRENCY_ARABIC_NAME}\n"
                f"🔧 الصيانة: {summary['maintenance']:.0f} {CURRENCY_ARABIC_NAME}\n"
                f"📊 الصافي: {summary['net']:+.0f} {CURRENCY_ARABIC_NAME}",
                parse_mode="HTML")
            return
        result = collect_income_for_country(country_id, user_id)
        bot.reply_to(message, result["message"], parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")
