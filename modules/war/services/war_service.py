# war_service.py

from database.db_queries.war_queries import (
    add_battle_loss,
    apply_troop_losses,
    apply_equipment_losses,
    get_city_equipment,
    get_city_troops,
    record_city_battle,
    update_city_resources,
)
from modules.war.war_report import format_battle_report
from modules.war.war_simulator import simulate_battle

from database.db_queries.countries_queries import (
    get_city_by_id,
    get_all_cities_of_country_by_country_id
)


# ─────────────────────────────
# ⚔️ تنفيذ هجوم كامل
# ─────────────────────────────
def execute_attack(attacker_city_id, defender_city_id,
                   attacker_name="المهاجم",
                   defender_name="المدافع",
                   attacker_cards=None,
                   defender_cards=None):

    # 1️⃣ جلب المدينة المهاجمة
    attacker_city = get_city_by_id(attacker_city_id)
    if not attacker_city:
        return "❌ مدينة الهجوم غير موجودة!"

    country_id = attacker_city["country_id"]

    # 2️⃣ جلب كل مدن الدولة
    attacker_cities = get_all_cities_of_country_by_country_id(country_id)
    if not attacker_cities:
        return "❌ لا توجد مدن في الدولة!"

    # 3️⃣ جمع القوات والمعدات
    total_attacker_troops = {}
    total_attacker_eq = {}

    for city in attacker_cities:
        troops = get_city_troops(city["id"])
        eq = get_city_equipment(city["id"])

        for t in troops:
            total_attacker_troops[t["troop_type_id"]] = \
                total_attacker_troops.get(t["troop_type_id"], 0) + t["quantity"]

        for e in eq:
            total_attacker_eq[e["equipment_type_id"]] = \
                total_attacker_eq.get(e["equipment_type_id"], 0) + e["quantity"]

    # 4️⃣ جلب قوات المدافع
    defender_troops = get_city_troops(defender_city_id)
    defender_eq = get_city_equipment(defender_city_id)

    if not defender_troops:
        return "❌ الهدف لا يملك جيش!"

    # 5️⃣ تشغيل المحاكاة
    result = simulate_battle(
        total_attacker_troops,
        defender_troops,
        total_attacker_eq,
        defender_eq,
        attacker_cards,
        defender_cards
    )

    # 6️⃣ تحديد الفائز
    winner = result["winner"]

    if winner == "attacker":
        winner_id = attacker_city_id
        loot = 100
    elif winner == "defender":
        winner_id = defender_city_id
        loot = 50
    else:
        winner_id = None
        loot = 0

    # 7️⃣ تسجيل المعركة
    battle_id = record_city_battle(
        attacker_city_id=attacker_city_id,
        defender_city_id=defender_city_id,
        attacker_power=result["attacker_power"]["attack"],
        defender_power=result["defender_power"]["attack"],
        winner=winner,
        loot=loot
    )

    # 8️⃣ تسجيل الخسائر (المهاجم)
    for city in attacker_cities:
        for loss in result["attacker_losses"]:
            add_battle_loss(
                battle_id,
                city["id"],
                "troop",
                troop_type_id=loss.get("troop_type_id"),
                lost_quantity=loss["lost"]
            )

        apply_troop_losses(city["id"], result["attacker_losses"])
        apply_equipment_losses(city["id"], result["attacker_losses"])

    # 9️⃣ تسجيل الخسائر (المدافع)
    for loss in result["defender_losses"]:
        add_battle_loss(
            battle_id,
            defender_city_id,
            "troop",
            troop_type_id=loss.get("troop_type_id"),
            lost_quantity=loss["lost"]
        )

    apply_troop_losses(defender_city_id, result["defender_losses"])
    apply_equipment_losses(defender_city_id, result["defender_losses"])

    # 🔟 توزيع الغنائم
    if winner_id:
        update_city_resources(winner_id, loot)

    # 11️⃣ التقرير
    report = format_battle_report(
        attacker_name,
        defender_name,
        {
            "winner": winner,
            "attacker_remaining_hp": result["attacker_power"]["hp"],
            "defender_remaining_hp": result["defender_power"]["hp"],
            "attacker_losses": result["attacker_losses"],
            "defender_losses": result["defender_losses"]
        }
    )
    return report