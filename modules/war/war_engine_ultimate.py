"""
⚠️ DEPRECATED — هذا الملف مهجور ولا يُستخدم في النظام الحالي.
استخدم بدلاً منه: modules/war/live_battle_engine.py
يمكن حذف هذا الملف بأمان.
"""
import random

from database.connection import get_db_conn

# ─────────────────────────────
# 🧠 حساب القوة التفصيلية
# ─────────────────────────────
def get_city_army(city_id):
    conn = get_db_conn()
    cursor = conn.cursor()

    # الجنود
    cursor.execute("""
        SELECT ct.troop_type_id, ct.quantity,
               tt.attack, tt.defense, tt.hp, tt.speed
        FROM city_troops ct
        JOIN troop_types tt ON ct.troop_type_id = tt.id
        WHERE ct.city_id = ?
    """, (city_id,))
    troops = cursor.fetchall()

    # المعدات
    cursor.execute("""
        SELECT ce.equipment_type_id, ce.quantity,
               et.attack_bonus, et.defense_bonus, et.special_effect
        FROM city_equipment ce
        JOIN equipment_types et ON ce.equipment_type_id = et.id
        WHERE ce.city_id = ?
    """, (city_id,))
    equipment = cursor.fetchall()

    return troops, equipment


# ─────────────────────────────
# ⚡ حساب القوة الإجمالية
# ─────────────────────────────
def calculate_power(troops, equipment):
    attack = 0
    defense = 0
    hp = 0

    for t in troops:
        qty = t["quantity"]
        attack += qty * t["attack"]
        defense += qty * t["defense"]
        hp += qty * t["hp"]

    for e in equipment:
        attack += e["quantity"] * (e["attack_bonus"] or 0)
        defense += e["quantity"] * (e["defense_bonus"] or 0)

    return {"attack": attack, "defense": defense, "hp": hp}


# ─────────────────────────────
# 🃏 تطبيق البطاقات
# ─────────────────────────────
def apply_cards(power, cards):
    if not cards:
        return power

    for c in cards:
        if c["type"] == "attack":
            power["attack"] *= (1 + c["value"])
        elif c["type"] == "defense":
            power["defense"] *= (1 + c["value"])
        elif c["type"] == "hp":
            power["hp"] *= (1 + c["value"])

    return power


# ─────────────────────────────
# 🚀 تأثير الصواريخ والدفاع الجوي
# ─────────────────────────────
def missile_phase(attacker_eq, defender_eq):
    missiles = sum(e["quantity"] for e in attacker_eq if e["special_effect"] == "missile")
    anti = sum(e["quantity"] for e in defender_eq if e["special_effect"] == "anti_missile")

    blocked = min(missiles, anti)
    effective = missiles - blocked

    damage = effective * random.uniform(5, 10)
    return damage


# ─────────────────────────────
# ⚔️ جولات القتال
# ─────────────────────────────
def simulate_round(attacker, defender):
    # الهجوم مقابل الدفاع
    atk_damage = max(0, attacker["attack"] - defender["defense"] * 0.5)
    def_damage = max(0, defender["attack"] - attacker["defense"] * 0.5)

    # عشوائية بسيطة
    atk_damage *= random.uniform(0.8, 1.2)
    def_damage *= random.uniform(0.8, 1.2)

    defender["hp"] -= atk_damage
    attacker["hp"] -= def_damage

    return attacker, defender


# ─────────────────────────────
# 💥 حساب الخسائر الواقعية
# ─────────────────────────────
def calculate_losses(troops, remaining_hp_ratio):
    losses = []

    for t in troops:
        lost = int(t["quantity"] * (1 - remaining_hp_ratio) * random.uniform(0.4, 0.8))
        if lost > 0:
            losses.append({
                "troop_type_id": t["troop_type_id"],
                "lost": lost
            })

    return losses


# ─────────────────────────────
# 🧨 المعركة الكاملة
# ─────────────────────────────
def run_battle(attacker_city_id, defender_city_id, attacker_cards=None, defender_cards=None):
    troops_a, equip_a = get_city_army(attacker_city_id)
    troops_d, equip_d = get_city_army(defender_city_id)

    power_a = calculate_power(troops_a, equip_a)
    power_d = calculate_power(troops_d, equip_d)

    # تطبيق البطاقات
    power_a = apply_cards(power_a, attacker_cards)
    power_d = apply_cards(power_d, defender_cards)

    # مرحلة الصواريخ
    missile_damage = missile_phase(equip_a, equip_d)
    power_d["hp"] -= missile_damage

    # جولات القتال
    rounds = 3
    for _ in range(rounds):
        power_a, power_d = simulate_round(power_a, power_d)
        if power_a["hp"] <= 0 or power_d["hp"] <= 0:
            break
        # تحديد الفائز
    if power_a["hp"] > power_d["hp"]:
        winner = attacker_city_id
    else:
        winner = defender_city_id

    # حساب نسبة البقاء
    ratio_a = max(0, power_a["hp"]) / max(1, (power_a["hp"] + power_d["hp"]))
    ratio_d = max(0, power_d["hp"]) / max(1, (power_a["hp"] + power_d["hp"]))

    losses_a = calculate_losses(troops_a, ratio_a)
    losses_d = calculate_losses(troops_d, ratio_d)

    return {
        "winner": winner,
        "attacker_remaining_hp": power_a["hp"],
        "defender_remaining_hp": power_d["hp"],
        "attacker_losses": losses_a,
        "defender_losses": losses_d
    }