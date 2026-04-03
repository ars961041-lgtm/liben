"""
الذكاء الداخلي — اقتراحات خفيفة بناءً على حالة المستخدم
لا حسابات ثقيلة، لا API خارجية
"""
from core.personality import suggestion_prefix


# ══════════════════════════════════════════
# 💡 محرك الاقتراحات
# ══════════════════════════════════════════

def get_suggestions(user_id: int) -> list[str]:
    """
    يرجع قائمة اقتراحات مخصصة للمستخدم بناءً على حالته الحالية.
    خفيف جداً — يستخدم فقط بيانات موجودة في الذاكرة والـ DB.
    """
    suggestions = []

    try:
        suggestions += _check_economy(user_id)
        suggestions += _check_military(user_id)
        suggestions += _check_alliance(user_id)
        suggestions += _check_battle(user_id)
        suggestions += _check_tickets(user_id)
    except Exception as e:
        print(f"[Intelligence] error: {e}")

    return suggestions[:3]  # أقصى 3 اقتراحات


def get_suggestion_text(user_id: int) -> str:
    """يرجع نص الاقتراحات جاهزاً للإرسال، أو سلسلة فارغة"""
    suggestions = get_suggestions(user_id)
    if not suggestions:
        return ""
    prefix = suggestion_prefix()
    lines = "\n".join(f"  • {s}" for s in suggestions)
    return f"\n\n{prefix}\n{lines}"


# ══════════════════════════════════════════
# 🔍 فحوصات الحالة
# ══════════════════════════════════════════

def _check_economy(user_id: int) -> list[str]:
    """يفحص الحالة الاقتصادية"""
    tips = []
    try:
        from database.db_queries.bank_queries import get_user_balance
        balance = get_user_balance(user_id)
        if balance is not None:
            if balance < 100:
                tips.append("💸 رصيدك منخفض — جرّب: <code>راتب</code> أو <code>مهمة</code>")
            elif balance > 5000:
                tips.append("💰 رصيدك ممتاز — فكّر في الاستثمار: <code>استثمار</code>")
    except Exception:
        pass
    return tips


def _check_military(user_id: int) -> list[str]:
    """يفحص الحالة العسكرية"""
    tips = []
    try:
        from database.db_queries.countries_queries import get_country_by_owner
        from modules.war.power_calculator import get_country_power
        country = get_country_by_owner(user_id)
        if not country:
            tips.append("🌍 لا تملك دولة — أنشئها: <code>إنشاء دولة [الاسم]</code>")
            return tips
        country = dict(country)
        power = get_country_power(country["id"])
        if power == 0:
            tips.append("⚔️ جيشك فارغ — اشترِ جنوداً من متجر الحرب")
        elif power < 500:
            tips.append("🪖 قوتك العسكرية ضعيفة — عزّز جيشك قبل الهجوم")

        # فحص التعافي
        from modules.war.war_economy import is_country_in_recovery
        in_rec, rem = is_country_in_recovery(country["id"])
        if in_rec:
            tips.append(f"🔄 دولتك في تعافٍ — متبقي {rem // 60} دقيقة")
    except Exception:
        pass
    return tips


def _check_alliance(user_id: int) -> list[str]:
    """يفحص حالة التحالف"""
    tips = []
    try:
        from database.db_queries.alliances_queries import get_alliance_by_user
        alliance = get_alliance_by_user(user_id)
        if not alliance:
            tips.append("🏰 لست في تحالف — انضم أو أنشئ: <code>تحالفي</code>")
    except Exception:
        pass
    return tips


def _check_battle(user_id: int) -> list[str]:
    """يفحص المعارك النشطة"""
    tips = []
    try:
        from database.db_queries.countries_queries import get_country_by_owner
        from database.db_queries.advanced_war_queries import get_active_battles_for_country
        country = get_country_by_owner(user_id)
        if country:
            country = dict(country)
            active = get_active_battles_for_country(country["id"])
            if active:
                b = active[0]
                status_ar = "في الطريق" if b["status"] == "traveling" else "في القتال"
                tips.append(f"⚔️ لديك معركة نشطة ({status_ar}) — <code>حرب</code>")
    except Exception:
        pass
    return tips


def _check_tickets(user_id: int) -> list[str]:
    """يفحص التذاكر المفتوحة"""
    tips = []
    try:
        from modules.tickets.ticket_db import get_open_ticket_for_user
        ticket = get_open_ticket_for_user(user_id)
        if ticket:
            tips.append(f"🎫 لديك تذكرة مفتوحة #{ticket['id']} — يمكنك متابعتها")
    except Exception:
        pass
    return tips


# ══════════════════════════════════════════
# 🎯 اقتراح بناءً على آخر أمر
# ══════════════════════════════════════════

_COMMAND_FOLLOWUPS: dict[str, str] = {
    "حرب":          "💡 بعد المعركة: تحقق من مصابيك — <code>مستشفى</code>",
    "عرش الحرب":    "💡 بعد المعركة: تحقق من مصابيك — <code>مستشفى</code>",
    "دولتي":        "💡 عزّز اقتصادك بشراء مباني — <code>متجر</code>",
    "مدينتي":       "💡 طوّر مدينتك — <code>ترقية</code>",
    "تحالفي":       "💡 اشترِ ترقيات للتحالف لتقوية الجميع",
    "إبلاغ المطور": "💡 يمكنك متابعة تذكرتك بإرسال رسالة جديدة",
    "راتب":         "💡 استثمر راتبك — <code>استثمار</code>",
}


def get_followup_tip(last_command: str) -> str:
    """يرجع اقتراحاً بناءً على آخر أمر"""
    return _COMMAND_FOLLOWUPS.get(last_command, "")
