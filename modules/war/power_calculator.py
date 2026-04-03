"""
حساب القوة المركزي — يُستخدم في كل مكان
get_country_power(country_id) هي الدالة الوحيدة المعتمدة
"""
from database.db_queries.war_queries import get_city_troops, get_city_equipment
from database.db_queries.countries_queries import get_all_cities_of_country_by_country_id


# ══════════════════════════════════════════
# 🔧 جمع قوات الدولة
# ══════════════════════════════════════════

def aggregate_country_forces(country_id):
    """
    يجمع كل قوات ومعدات جميع مدن الدولة.
    يرجع (troops_list, equipment_list)
    """
    cities = get_all_cities_of_country_by_country_id(country_id)
    if not cities:
        return [], []

    all_troops = {}
    all_eq = {}

    for city in cities:
        cid = city["id"] if isinstance(city, dict) else city[0]

        for t in get_city_troops(cid):
            t = dict(t)
            tid = t["troop_type_id"]
            if tid not in all_troops:
                all_troops[tid] = t.copy()
            else:
                all_troops[tid]["quantity"] = (
                    all_troops[tid].get("quantity", 0) + t.get("quantity", 0)
                )

        for e in get_city_equipment(cid):
            e = dict(e)
            eid = e["equipment_type_id"]
            if eid not in all_eq:
                all_eq[eid] = e.copy()
            else:
                all_eq[eid]["quantity"] = (
                    all_eq[eid].get("quantity", 0) + e.get("quantity", 0)
                )

    return list(all_troops.values()), list(all_eq.values())


# ══════════════════════════════════════════
# 💪 حساب القوة الخام
# ══════════════════════════════════════════

def calc_raw_power(troops, equipment):
    """
    الصيغة:
      troops_power  = Σ quantity × (attack×1.0 + defense×0.5 + hp×0.1)
      equip_bonus   = Σ quantity × (attack_bonus + defense_bonus×0.5)
    """
    troops_power = sum(
        t.get("quantity", 0) * (
            t.get("attack", 0) * 1.0
            + t.get("defense", 0) * 0.5
            + t.get("hp", 0) * 0.1
        )
        for t in troops
    )
    equip_bonus = sum(
        e.get("quantity", 0) * (
            e.get("attack_bonus", 0)
            + e.get("defense_bonus", 0) * 0.5
        )
        for e in equipment
    )
    return max(0.0, troops_power + equip_bonus)


# ══════════════════════════════════════════
# 🏰 تأثير ترقيات التحالف
# ══════════════════════════════════════════

def _get_alliance_multiplier(country_id):
    """يرجع مضاعف قوة التحالف للدولة (1.0 إذا لم تكن في تحالف)"""
    try:
        from database.db_queries.alliances_queries import (
            get_alliance_by_country, get_alliance_effect
        )
        alliance = get_alliance_by_country(country_id)
        if not alliance:
            return 1.0
        aid = alliance["id"]
        atk_bonus = get_alliance_effect(aid, "attack_bonus")
        def_bonus = get_alliance_effect(aid, "defense_bonus")
        hp_bonus  = get_alliance_effect(aid, "hp_bonus")
        return max(1.0, 1.0 + atk_bonus + def_bonus * 0.5 + hp_bonus * 0.3)
    except Exception:
        return 1.0


# ══════════════════════════════════════════
# 🎯 الدالة الرئيسية — استخدم هذه فقط
# ══════════════════════════════════════════

def get_country_power(country_id):
    """
    يحسب القوة الكاملة للدولة:
      total_power = raw_power × alliance_multiplier × (1 - maintenance_penalty)
    لا تعود أبداً بقيمة سالبة.
    """
    troops, equipment = aggregate_country_forces(country_id)
    raw = calc_raw_power(troops, equipment)
    multiplier = _get_alliance_multiplier(country_id)
    power = max(0.0, raw * multiplier)

    # ─── تطبيق عقوبة الصيانة ───
    try:
        from modules.war.maintenance_service import get_maintenance_penalty
        penalty = get_maintenance_penalty(country_id)
        power = max(0.0, power * (1 - penalty))
    except Exception:
        pass

    return power


def get_country_power_breakdown(country_id):
    """
    يرجع تفصيلاً كاملاً للقوة (للعرض في الواجهة)
    """
    troops, equipment = aggregate_country_forces(country_id)
    raw = calc_raw_power(troops, equipment)
    multiplier = _get_alliance_multiplier(country_id)
    total = max(0.0, raw * multiplier)

    troop_count = sum(t.get("quantity", 0) for t in troops)
    equip_count = sum(e.get("quantity", 0) for e in equipment)

    return {
        "total": total,
        "raw": raw,
        "alliance_multiplier": multiplier,
        "troop_count": troop_count,
        "equipment_count": equip_count,
        "troops": troops,
        "equipment": equipment,
    }
