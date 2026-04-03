# war_helpers.py

# ─────────────────────────────
# ⚡ حساب القوة
# ─────────────────────────────
def calculate_total_power(troops, equipment):
    attack = 0
    defense = 0
    hp = 0

    for t in troops:
        attack += t["quantity"] * t["attack"]
        defense += t["quantity"] * t["defense"]
        hp += t["quantity"] * t["hp"]

    for e in equipment:
        attack += e["quantity"] * (e["attack_bonus"] or 0)
        defense += e["quantity"] * (e["defense_bonus"] or 0)

    return {
        "attack": attack,
        "defense": defense,
        "hp": hp
    }


# ─────────────────────────────
# 🧪 تطبيق البطاقات
# ─────────────────────────────
def apply_cards_to_power(power, cards):
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
# 🎯 تحديد الفائز
# ─────────────────────────────
def determine_winner(attacker_power, defender_power):
    if attacker_power["hp"] > defender_power["hp"]:
        return "attacker"
    elif defender_power["hp"] > attacker_power["hp"]:
        return "defender"
    return "draw"