# war_simulator.py

import random
from .war_helpers import calculate_total_power, apply_cards_to_power, determine_winner


# ─────────────────────────────
# 🚀 الصواريخ
# ─────────────────────────────
def missile_phase(attacker_eq, defender_eq):
    missiles = sum(e["quantity"] for e in attacker_eq if e["special_effect"] == "missile")
    anti = sum(e["quantity"] for e in defender_eq if e["special_effect"] == "anti_missile")

    blocked = min(missiles, anti)
    effective = missiles - blocked

    damage = effective * random.uniform(5, 10)

    return {
        "launched": missiles,
        "blocked": blocked,
        "hit": effective,
        "damage": damage
    }


# ─────────────────────────────
# ⚔️ جولة قتال
# ─────────────────────────────
def simulate_round(attacker, defender):
    atk_damage = max(0, attacker["attack"] - defender["defense"] * 0.5)
    def_damage = max(0, defender["attack"] - attacker["defense"] * 0.5)

    atk_damage *= random.uniform(0.8, 1.2)
    def_damage *= random.uniform(0.8, 1.2)

    defender["hp"] -= atk_damage
    attacker["hp"] -= def_damage

    return attacker, defender


# ─────────────────────────────
# 💥 حساب الخسائر
# ─────────────────────────────
def calculate_losses(troops, remaining_ratio):
    losses = []

    for t in troops:
        lost = int(t["quantity"] * (1 - remaining_ratio) * random.uniform(0.4, 0.8))
        if lost > 0:
            losses.append({
                "troop_type_id": t["troop_type_id"],
                "lost": lost
            })

    return losses


# ─────────────────────────────
# 🧨 محاكاة معركة كاملة
# ─────────────────────────────
def simulate_battle(attacker_troops, defender_troops,
                    attacker_eq, defender_eq,
                    attacker_cards=None, defender_cards=None):

    # حساب القوة
    power_a = calculate_total_power(attacker_troops, attacker_eq)
    power_d = calculate_total_power(defender_troops, defender_eq)

    # تطبيق البطاقات
    power_a = apply_cards_to_power(power_a, attacker_cards)
    power_d = apply_cards_to_power(power_d, defender_cards)

    # مرحلة الصواريخ
    missile_result = missile_phase(attacker_eq, defender_eq)
    power_d["hp"] -= missile_result["damage"]

    # جولات
    rounds = 3
    for _ in range(rounds):
        power_a, power_d = simulate_round(power_a, power_d)

        if power_a["hp"] <= 0 or power_d["hp"] <= 0:
            break

    # الفائز
    winner = determine_winner(power_a, power_d)

    # نسب البقاء
    total_hp = max(1, power_a["hp"] + power_d["hp"])

    ratio_a = max(0, power_a["hp"]) / total_hp
    ratio_d = max(0, power_d["hp"]) / total_hp

    # الخسائر
    losses_a = calculate_losses(attacker_troops, ratio_a)
    losses_d = calculate_losses(defender_troops, ratio_d)

    return {
        "winner": winner,
        "attacker_power": power_a,
        "defender_power": power_d,
        "missiles": missile_result,
        "attacker_losses": losses_a,
        "defender_losses": losses_d
    }