"""
handlers/analytics_handler.py

Commands that surface analytics from history/log tables.

Commands (text-based, work in groups and private):
  إحصائيات الأصول       — top purchased assets this month
  أكثر ترقية            — top upgraded assets this month
  أكبر منفقين           — top spenders on city assets
  إحصائيات التحويلات    — bank transfer volume summary + top senders
  إحصائيات المعارك      — battle summary + top winning countries
  أكثر هجوما           — most active attacking countries
  إحصائيات التجسس       — top spy countries by success rate
  إحصائيات الاستكشاف    — top exploring countries
  أكبر منفقين حرب       — top war spenders

All commands default to the current month.
Append "الأسبوع" to get weekly stats, or "كل الوقت" for all-time.
"""
from core.bot import bot
from utils.helpers import get_lines
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME
from database.db_queries.analytics_queries import (
    get_top_purchased_assets, get_top_upgraded_assets, get_top_spenders_on_assets,
    get_top_senders, get_top_receivers, get_transfer_volume_summary,
    get_top_winners, get_most_active_attackers, get_battle_summary,
    get_top_spy_countries, get_top_explorers, get_top_war_spenders,
    _month_start, _week_start,
)

_COMMANDS = {
    "إحصائيات الأصول",
    "أكثر ترقية",
    "أكبر منفقين",
    "إحصائيات التحويلات",
    "إحصائيات المعارك",
    "أكثر هجوما",
    "إحصائيات التجسس",
    "إحصائيات الاستكشاف",
    "أكبر منفقين حرب",
}


def _resolve_period(text: str) -> tuple[int, str]:
    """Returns (since_unix, label) based on trailing keyword."""
    if "الأسبوع" in text:
        return _week_start(), "هذا الأسبوع"
    if "كل الوقت" in text:
        return 0, "كل الوقت"
    return _month_start(), "هذا الشهر"


def analytics_commands(message) -> bool:
    text = (message.text or "").strip()

    # Find which command matches (commands are multi-word, check by prefix)
    matched_cmd = None
    for cmd in _COMMANDS:
        if text == cmd or text.startswith(cmd + " "):
            matched_cmd = cmd
            break

    if not matched_cmd:
        return False

    since, period_label = _resolve_period(text)
    reply = _dispatch(matched_cmd, since, period_label)
    if reply:
        bot.reply_to(message, reply, parse_mode="HTML")
    return True


def _dispatch(cmd: str, since: int, period: str) -> str:
    if cmd == "إحصائيات الأصول":
        return _fmt_top_purchased(since, period)
    if cmd == "أكثر ترقية":
        return _fmt_top_upgraded(since, period)
    if cmd == "أكبر منفقين":
        return _fmt_top_asset_spenders(since, period)
    if cmd == "إحصائيات التحويلات":
        return _fmt_transfers(since, period)
    if cmd == "إحصائيات المعارك":
        return _fmt_battles(since, period)
    if cmd == "أكثر هجوما":
        return _fmt_attackers(since, period)
    if cmd == "إحصائيات التجسس":
        return _fmt_spy(since, period)
    if cmd == "إحصائيات الاستكشاف":
        return _fmt_exploration(since, period)
    if cmd == "أكبر منفقين حرب":
        return _fmt_war_spenders(since, period)
    return ""


# ── Formatters ────────────────────────────────────────────────────

def _fmt_top_purchased(since: int, period: str) -> str:
    rows = get_top_purchased_assets(10, since)
    if not rows:
        return f"📦 لا توجد مشتريات {period}."
    lines = [f"📦 <b>أكثر الأصول شراءً — {period}</b>\n{get_lines()}\n"]
    for i, r in enumerate(rows, 1):
        lines.append(
            f"{i}. {r['emoji']} {r['name_ar']} — "
            f"{r['total_bought']:,} وحدة | "
            f"{r['total_spent']:,.0f} {CURRENCY_ARABIC_NAME}"
        )
    return "\n".join(lines)


def _fmt_top_upgraded(since: int, period: str) -> str:
    rows = get_top_upgraded_assets(10, since)
    if not rows:
        return f"⬆️ لا توجد ترقيات {period}."
    lines = [f"⬆️ <b>أكثر الأصول ترقيةً — {period}</b>\n{get_lines()}\n"]
    for i, r in enumerate(rows, 1):
        lines.append(
            f"{i}. {r['emoji']} {r['name_ar']} — "
            f"{r['total_upgrades']:,} ترقية | "
            f"{r['total_spent']:,.0f} {CURRENCY_ARABIC_NAME}"
        )
    return "\n".join(lines)


def _fmt_top_asset_spenders(since: int, period: str) -> str:
    rows = get_top_spenders_on_assets(10, since)
    if not rows:
        return f"💰 لا توجد بيانات إنفاق {period}."
    lines = [f"💰 <b>أكبر المنفقين على الأصول — {period}</b>\n{get_lines()}\n"]
    for i, r in enumerate(rows, 1):
        lines.append(
            f"{i}. {r['name']} — {r['total_spent']:,.0f} {CURRENCY_ARABIC_NAME}"
        )
    return "\n".join(lines)


def _fmt_transfers(since: int, period: str) -> str:
    summary = get_transfer_volume_summary(since)
    senders = get_top_senders(5, since)
    lines = [
        f"💸 <b>إحصائيات التحويلات — {period}</b>\n{get_lines()}\n",
        f"📊 إجمالي التحويلات: {summary['total_count']:,}",
        f"💵 الحجم الكلي: {summary['total_volume']:,.0f} {CURRENCY_ARABIC_NAME}",
        f"💳 الرسوم المحصّلة: {summary['total_fees']:,.0f} {CURRENCY_ARABIC_NAME}",
        f"\n🏆 <b>أكثر المرسلين:</b>",
    ]
    for i, r in enumerate(senders, 1):
        lines.append(
            f"{i}. {r['name']} — {r['total_sent']:,.0f} {CURRENCY_ARABIC_NAME} "
            f"({r['transfer_count']} تحويل)"
        )
    return "\n".join(lines)


def _fmt_battles(since: int, period: str) -> str:
    summary = get_battle_summary(since)
    winners = get_top_winners(5, since)
    avg_min = round(summary["avg_duration_sec"] / 60, 1)
    lines = [
        f"⚔️ <b>إحصائيات المعارك — {period}</b>\n{get_lines()}\n",
        f"🗡 إجمالي المعارك: {summary['total_battles']:,}",
        f"💰 إجمالي الغنائم: {summary['total_loot']:,.0f} {CURRENCY_ARABIC_NAME}",
        f"⏱ متوسط مدة المعركة: {avg_min} دقيقة",
        f"\n🏆 <b>أكثر الدول انتصاراً:</b>",
    ]
    for i, r in enumerate(winners, 1):
        lines.append(
            f"{i}. {r['country_name']} — {r['wins']} انتصار | "
            f"{r['total_loot']:,.0f} {CURRENCY_ARABIC_NAME} غنائم"
        )
    return "\n".join(lines)


def _fmt_attackers(since: int, period: str) -> str:
    rows = get_most_active_attackers(10, since)
    if not rows:
        return f"⚔️ لا توجد معارك {period}."
    lines = [f"🗡 <b>أكثر الدول هجوماً — {period}</b>\n{get_lines()}\n"]
    for i, r in enumerate(rows, 1):
        lines.append(
            f"{i}. {r['country_name']} — {r['attacks']} هجوم | "
            f"نسبة الفوز: {r['win_rate']}%"
        )
    return "\n".join(lines)


def _fmt_spy(since: int, period: str) -> str:
    rows = get_top_spy_countries(10, since)
    if not rows:
        return f"🕵️ لا توجد عمليات تجسس {period}."
    lines = [f"🕵️ <b>إحصائيات التجسس — {period}</b>\n{get_lines()}\n"]
    for i, r in enumerate(rows, 1):
        lines.append(
            f"{i}. {r['country_name']} — {r['successes']} نجاح / {r['total_ops']} عملية "
            f"({r['success_rate']}%)"
        )
    return "\n".join(lines)


def _fmt_exploration(since: int, period: str) -> str:
    rows = get_top_explorers(10, since)
    if not rows:
        return f"🗺️ لا توجد مهام استكشاف {period}."
    lines = [f"🗺️ <b>إحصائيات الاستكشاف — {period}</b>\n{get_lines()}\n"]
    for i, r in enumerate(rows, 1):
        lines.append(
            f"{i}. {r['country_name']} — {r['total_missions']} مهمة | "
            f"{r['discoveries']} اكتشاف | "
            f"{r['total_cost']:,.0f} {CURRENCY_ARABIC_NAME}"
        )
    return "\n".join(lines)


def _fmt_war_spenders(since: int, period: str) -> str:
    rows = get_top_war_spenders(10, since)
    if not rows:
        return f"💰 لا توجد بيانات إنفاق حربي {period}."
    lines = [f"💰 <b>أكبر المنفقين على الحرب — {period}</b>\n{get_lines()}\n"]
    for i, r in enumerate(rows, 1):
        lines.append(
            f"{i}. {r['name']} — {r['total_spent']:,.0f} {CURRENCY_ARABIC_NAME} "
            f"({r['action_count']} عملية)"
        )
    return "\n".join(lines)
