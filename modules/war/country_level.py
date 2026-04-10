"""
نظام مستويات الدول — حساب ديناميكي + نظام الفئات الثلاث للهجوم
"""
import math
from database.db_queries.countries_queries import get_all_cities_of_country_by_country_id

# ══════════════════════════════════════════
# ⚙️ أوزان الإحصائيات
# ══════════════════════════════════════════

STAT_WEIGHTS = {
    "military_power":       3.0,
    "economy_score":        2.0,
    "health_level":         1.0,
    "education_level":      1.0,
    "infrastructure_level": 1.0,
}

# ══════════════════════════════════════════
# 🎯 نظام الفئات الثلاث
# ══════════════════════════════════════════

# عتبات الفئات بناءً على القوة العسكرية
TIER_THRESHOLDS = {
    "weak":   (0,     2000),   # 🟢 ضعيف
    "medium": (2000,  10000),  # 🟡 متوسط
    "strong": (10000, float("inf")),  # 🔴 قوي
}

TIER_LABELS = {
    "weak":   "🟢 ضعيف",
    "medium": "🟡 متوسط",
    "strong": "🔴 قوي",
}

# قواعد الهجوم المسموح بها
ALLOWED_ATTACKS = {
    ("weak",   "weak"):   True,
    ("weak",   "medium"): True,
    ("weak",   "strong"): False,   # ❌ ضعيف لا يهاجم قوي
    ("medium", "weak"):   True,
    ("medium", "medium"): True,
    ("medium", "strong"): True,
    ("strong", "weak"):   False,   # ❌ قوي لا يهاجم ضعيف
    ("strong", "medium"): True,    # ✅ مسموح لكن بعقوبة
    ("strong", "strong"): True,
}

# عقوبة الهجوم غير المتكافئ (قوي → متوسط)
ATTACK_PENALTIES = {
    ("strong", "medium"): 0.8,   # 20% تقليل في الضرر
}


def get_attack_penalty(attacker_tier: str, defender_tier: str) -> float:
    """يرجع معامل الضرر (1.0 = كامل، 0.8 = 20% عقوبة)"""
    return ATTACK_PENALTIES.get((attacker_tier, defender_tier), 1.0)


# ══════════════════════════════════════════
# 🏆 مضاعفات المكافآت الذكية
# ══════════════════════════════════════════

REWARD_MULTIPLIERS = {
    ("weak",   "strong"):  1.5,   # 🔥 مخاطرة عالية = مكافأة عالية
    ("weak",   "medium"):  1.2,
    ("medium", "strong"):  1.2,
    ("medium", "weak"):    0.9,
    ("strong", "medium"):  0.8,
    ("strong", "strong"):  1.0,
    ("weak",   "weak"):    1.0,
    ("medium", "medium"):  1.0,
}


def get_reward_multiplier(attacker_tier: str, defender_tier: str) -> float:
    """يرجع مضاعف المكافأة بناءً على فئتي المهاجم والمدافع"""
    return REWARD_MULTIPLIERS.get((attacker_tier, defender_tier), 1.0)


def get_country_tier(country_id: int) -> str:
    """يرجع فئة الدولة: weak / medium / strong"""
    try:
        from modules.war.power_calculator import get_country_power
        power = get_country_power(country_id)
    except Exception:
        power = 0.0

    if power < TIER_THRESHOLDS["weak"][1]:
        return "weak"
    elif power < TIER_THRESHOLDS["medium"][1]:
        return "medium"
    return "strong"


def get_tier_label(country_id: int) -> str:
    """يرجع نص الفئة مع الإيموجي"""
    return TIER_LABELS.get(get_country_tier(country_id), "🟡 متوسط")

# ══════════════════════════════════════════
# 📊 حساب المستوى
# ══════════════════════════════════════════

def get_country_score(country_id: int) -> float:
    """
    يحسب النقاط الإجمالية للدولة من مجموع إحصائيات مدنها.
    يشمل مكافأة التحالف.
    """
    from database.db_queries.assets_queries import calculate_city_effects, get_city_military_power

    cities = get_all_cities_of_country_by_country_id(country_id)
    if not cities:
        return 0.0

    total = 0.0
    for city in cities:
        cid = city["id"] if isinstance(city, dict) else city[0]
        fx = calculate_city_effects(cid)
        military = get_city_military_power(cid)
        total += (
            military                      * STAT_WEIGHTS["military_power"] +
            fx.get("economy", 0)          * STAT_WEIGHTS["economy_score"] +
            fx.get("health", 0)           * STAT_WEIGHTS["health_level"] +
            fx.get("education", 0)        * STAT_WEIGHTS["education_level"] +
            fx.get("infrastructure", 0)   * STAT_WEIGHTS["infrastructure_level"]
        )

    # مكافأة التحالف
    try:
        from database.db_queries.alliances_queries import get_alliance_by_country, get_alliance_effect
        alliance = get_alliance_by_country(country_id)
        if alliance:
            aid = alliance["id"]
            bonus = (
                get_alliance_effect(aid, "attack_bonus") +
                get_alliance_effect(aid, "defense_bonus") +
                get_alliance_effect(aid, "hp_bonus")
            )
            total *= (1 + bonus * 0.5)
    except Exception:
        pass

    # مكافأة القوة العسكرية
    try:
        from modules.war.power_calculator import get_country_power
        power = get_country_power(country_id)
        total += power * 0.1
    except Exception:
        pass

    return max(0.0, total)


def score_to_level(score: float) -> int:
    """
    يحوّل النقاط إلى مستوى (1–20+).
    صيغة: level = 1 + floor(log2(score/50 + 1))
    """
    if score <= 0:
        return 1
    return max(1, 1 + int(math.log2(score / 50 + 1)))


def get_country_level(country_id: int) -> int:
    """الدالة الرئيسية — يرجع مستوى الدولة"""
    return score_to_level(get_country_score(country_id))


def get_level_info(country_id: int) -> dict:
    """يرجع معلومات المستوى الكاملة"""
    score = get_country_score(country_id)
    level = score_to_level(score)
    next_score = 50 * (2 ** level - 1)
    progress = min(100, int((score / max(1, next_score)) * 100))
    return {
        "level":      level,
        "score":      round(score, 1),
        "next_score": round(next_score, 1),
        "progress":   progress,
        "label":      _level_label(level),
    }


def _level_label(level: int) -> str:
    labels = {
        1: "🌱 مبتدئ", 2: "🌿 ناشئ", 3: "⚔️ محارب",
        4: "🛡 مدافع", 5: "🏹 قناص", 6: "🐎 فارس",
        7: "🏰 قائد", 8: "👑 ملك", 9: "🌟 إمبراطور",
        10: "🔥 أسطورة",
    }
    if level >= 10:
        return f"🔥 أسطورة (مستوى {level})"
    return labels.get(level, f"مستوى {level}")


# ══════════════════════════════════════════
# 🛡️ فحص الهجوم — نظام الفئات الثلاث
# ══════════════════════════════════════════

def check_attack_level(attacker_id: int, defender_id: int) -> tuple:
    """
    يتحقق من إمكانية الهجوم بناءً على الفئات الثلاث.
    يرجع (True, None) إذا مسموح، أو (False, رسالة_خطأ)
    يرجع (True, تحذير) إذا مسموح مع عقوبة
    """
    atk_tier = get_country_tier(attacker_id)
    def_tier = get_country_tier(defender_id)

    allowed = ALLOWED_ATTACKS.get((atk_tier, def_tier), True)
    if not allowed:
        atk_label = TIER_LABELS[atk_tier]
        def_label = TIER_LABELS[def_tier]
        if atk_tier == "strong" and def_tier == "weak":
            return False, (
                f"🛡️ <b>هجوم غير عادل!</b>\n\n"
                f"فئتك: {atk_label}\n"
                f"فئة الهدف: {def_label}\n\n"
                f"لا يمكن لدولة قوية مهاجمة دولة ضعيفة."
            )
        return False, (
            f"🛡️ <b>هجوم غير مسموح!</b>\n\n"
            f"فئتك: {atk_label} | فئة الهدف: {def_label}\n\n"
            f"القواعد:\n"
            f"🟢 ضعيف ↔ 🟡 متوسط ✔\n"
            f"🟡 متوسط ↔ 🔴 قوي ✔\n"
            f"🟢 ضعيف → 🔴 قوي ❌"
        )

    # تحذير عقوبة strong → medium
    penalty = ATTACK_PENALTIES.get((atk_tier, def_tier))
    if penalty:
        return True, f"⚠️ هجوم بفعالية مخفضة {int((1-penalty)*100)}% (قوي → متوسط)"
    return True, None


# ══════════════════════════════════════════
# 🏆 توب الدول بالمستوى
# ══════════════════════════════════════════

def get_top_countries_by_level(limit: int = 20) -> list:
    """يرجع أقوى الدول مرتبة بالمستوى"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, owner_id FROM countries")
    countries = cursor.fetchall()

    result = []
    for c in countries:
        cid, name, owner = c[0], c[1], c[2]
        info = get_level_info(cid)
        result.append({
            "id":      cid,
            "name":    name,
            "owner_id": owner,
            "level":   info["level"],
            "score":   info["score"],
            "label":   info["label"],
        })

    result.sort(key=lambda x: x["score"], reverse=True)
    return result[:limit]
