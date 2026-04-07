"""
نظام النفوذ والتأثير — تدرج لوغاريتمي مع حد أقصى ناعم
"""
import math
from database.connection import get_db_conn
from utils.helpers import get_lines


def _c(name, default):
    try:
        from core.admin import get_const_int, get_const_float
        if isinstance(default, float):
            return get_const_float(name, default)
        return get_const_int(name, int(default))
    except Exception:
        return default


# ══════════════════════════════════════════
# 📐 الصيغة اللوغاريتمية
# ══════════════════════════════════════════

def _log_bonus(points: int, rate: float, hard_cap: float) -> float:
    """
    تدرج لوغاريتمي مع حد أقصى ناعم:
      bonus = rate × log2(points/100 + 1)
    يصل لـ 50% من hard_cap عند 100 نقطة، 75% عند 300، 90% عند 700.
    """
    if points <= 0:
        return 0.0
    raw = rate * math.log2(points / 100 + 1)
    # تناقص العوائد: كل مضاعفة تُضيف نصف ما أضافته السابقة
    return min(hard_cap, raw)


# ══════════════════════════════════════════
# 📊 إدارة النفوذ
# ══════════════════════════════════════════

def ensure_influence(country_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO country_influence
        (country_id, influence_points, income_bonus_pct, war_advantage_pct)
        VALUES (?, 0, 0, 0)
    """, (country_id,))
    conn.commit()


def get_influence(country_id: int) -> dict:
    ensure_influence(country_id)
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM country_influence WHERE country_id = ?", (country_id,))
    row = cursor.fetchone()
    return dict(row) if row else {"influence_points": 0, "income_bonus_pct": 0, "war_advantage_pct": 0}


def add_influence(country_id: int, points: int, reason: str = ""):
    """يُضيف نقاط نفوذ ويُحدّث المكافآت"""
    ensure_influence(country_id)

    # ─── تطبيق حدث العصر الذهبي / أسبوع التحالفات ───
    try:
        from modules.progression.global_events import get_event_effect
        xp_bonus = get_event_effect("xp_bonus")
        if xp_bonus > 0:
            points = round(points * (1 + xp_bonus))
        # alliance_xp_bonus يُطبق فقط على مكاسب التحالف
        if reason and "alliance" in reason:
            alliance_bonus = get_event_effect("alliance_xp_bonus")
            if alliance_bonus > 0:
                points = round(points * (1 + alliance_bonus))
    except Exception:
        pass

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE country_influence
        SET influence_points = influence_points + ?,
            last_updated = strftime('%s','now')
        WHERE country_id = ?
    """, (points, country_id))
    conn.commit()
    _recalc_bonuses(country_id)

    try:
        cursor.execute("SELECT owner_id FROM countries WHERE id = ?", (country_id,))
        row = cursor.fetchone()
        if row:
            from modules.progression.achievements import trigger_achievement_check
            trigger_achievement_check(row[0], "influence_gained")
    except Exception:
        pass


def _recalc_bonuses(country_id: int):
    """
    يُعيد حساب مكافآت النفوذ بصيغة لوغاريتمية.
    الحدود القصوى: دخل 40%، حرب 20%
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT influence_points FROM country_influence WHERE country_id = ?",
                   (country_id,))
    row = cursor.fetchone()
    if not row:
        return

    points = max(0, row[0])

    # معدلات من الثوابت
    income_rate = _c("influence_income_rate", 0.08)   # معدل الدخل اللوغاريتمي
    war_rate    = _c("influence_war_rate",    0.05)    # معدل الحرب اللوغاريتمي
    income_cap  = _c("influence_income_cap",  0.40)    # حد أقصى 40%
    war_cap     = _c("influence_war_cap",     0.20)    # حد أقصى 20%

    income_bonus = _log_bonus(points, income_rate, income_cap)
    war_bonus    = _log_bonus(points, war_rate,    war_cap)

    cursor.execute("""
        UPDATE country_influence
        SET income_bonus_pct = ?, war_advantage_pct = ?
        WHERE country_id = ?
    """, (round(income_bonus, 4), round(war_bonus, 4), country_id))
    conn.commit()


def get_income_bonus(country_id: int) -> float:
    inf = get_influence(country_id)
    return max(0.0, inf.get("income_bonus_pct", 0))


def get_war_advantage(country_id: int) -> float:
    inf = get_influence(country_id)
    return max(0.0, inf.get("war_advantage_pct", 0))


def on_battle_won(winner_country_id: int, loser_country_id: int):
    win_pts = _c("influence_per_win", 10)
    add_influence(winner_country_id, win_pts, "battle_win")
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE country_influence
        SET influence_points = MAX(0, influence_points - 3)
        WHERE country_id = ?
    """, (loser_country_id,))
    conn.commit()
    _recalc_bonuses(loser_country_id)


def on_defense_won(defender_country_id: int):
    def_pts = _c("influence_per_defense", 5)
    add_influence(defender_country_id, def_pts, "defense_win")


# ══════════════════════════════════════════
# 📈 تقدم النفوذ (للعرض)
# ══════════════════════════════════════════

def get_influence_progress(country_id: int) -> dict:
    """
    يرجع تفاصيل التقدم نحو المستوى التالي من المكافآت.
    """
    inf    = get_influence(country_id)
    points = inf["influence_points"]

    income_rate = _c("influence_income_rate", 0.08)
    war_rate    = _c("influence_war_rate",    0.05)
    income_cap  = _c("influence_income_cap",  0.40)
    war_cap     = _c("influence_war_cap",     0.20)

    current_income = _log_bonus(points, income_rate, income_cap)
    current_war    = _log_bonus(points, war_rate,    war_cap)

    # حساب النقاط اللازمة للمستوى التالي (+1% دخل)
    next_income_target = current_income + 0.01
    if next_income_target >= income_cap:
        pts_for_next = None  # وصل للحد الأقصى
    else:
        # عكس الصيغة: points = 100 × (2^(target/rate) - 1)
        try:
            pts_for_next = max(0, int(100 * (2 ** (next_income_target / income_rate) - 1)) - points)
        except Exception:
            pts_for_next = None

    return {
        "points":         points,
        "income_bonus":   round(current_income * 100, 1),
        "war_advantage":  round(current_war * 100, 1),
        "income_cap":     round(income_cap * 100, 1),
        "war_cap":        round(war_cap * 100, 1),
        "pts_for_next":   pts_for_next,
        "at_income_cap":  current_income >= income_cap * 0.99,
    }


def get_influence_display(country_id: int) -> str:
    """نص عرض النفوذ مع شريط التقدم"""
    p = get_influence_progress(country_id)

    bar_len  = 10
    inc_fill = min(bar_len, int((p["income_bonus"] / p["income_cap"]) * bar_len))
    bar      = "█" * inc_fill + "░" * (bar_len - inc_fill)

    next_txt = (
        f"📍 نقاط للمستوى التالي: {p['pts_for_next']}"
        if p["pts_for_next"] is not None
        else "✅ وصلت للحد الأقصى!"
    )

    return (
        f"🌍 <b>النفوذ والتأثير</b>\n"
        f"{get_lines()}\n"
        f"⭐ نقاط النفوذ: {p['points']}\n\n"
        f"💰 مكافأة الدخل: +{p['income_bonus']}% / {p['income_cap']}%\n"
        f"  [{bar}]\n"
        f"⚔️ ميزة الحرب: +{p['war_advantage']}% / {p['war_cap']}%\n\n"
        f"{next_txt}"
    )
