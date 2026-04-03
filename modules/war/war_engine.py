"""
⚠️ DEPRECATED — هذا الملف مهجور ولا يُستخدم في النظام الحالي.
استخدم بدلاً منه: modules/war/live_battle_engine.py
يمكن حذف هذا الملف بأمان.
"""
from datetime import datetime

from database.connection import get_db_conn

# ─── حساب قوة المدينة
def calculate_city_power(city_id):
    conn = get_db_conn()
    cursor = conn.cursor()

    # قوة الجنود
    cursor.execute("""
        SELECT SUM(ct.quantity * tt.attack) as attack_power,
               SUM(ct.quantity * tt.defense) as defense_power
        FROM city_troops ct
        JOIN troop_types tt ON ct.troop_type_id = tt.id
        WHERE ct.city_id = ?
    """, (city_id,))
    troops_power = cursor.fetchone()
    attack = troops_power[0] or 0
    defense = troops_power[1] or 0

    # قوة المعدات
    cursor.execute("""
        SELECT SUM(ce.quantity * et.attack_bonus) as attack_bonus,
               SUM(ce.quantity * et.defense_bonus) as defense_bonus
        FROM city_equipment ce
        JOIN equipment_types et ON ce.equipment_type_id = et.id
        WHERE ce.city_id = ?
    """, (city_id,))
    equip_power = cursor.fetchone()
    attack += equip_power[0] or 0
    defense += equip_power[1] or 0

    return {"attack": attack, "defense": defense}

# ─── تنفيذ المعركة
def execute_battle(attacker_city_id, defender_city_id, battle_type='normal', cards=[]):
    conn = get_db_conn()
    cursor = conn.cursor()

    attacker_power = calculate_city_power(attacker_city_id)
    defender_power = calculate_city_power(defender_city_id)

    # تطبيق تأثير البطاقات
    for card in cards:
        if card['type'] == 'boost_attack':
            attacker_power['attack'] += card['value']
        elif card['type'] == 'boost_defense':
            defender_power['defense'] += card['value']

    # حساب النتيجة
    attacker_score = attacker_power['attack'] - defender_power['defense']
    defender_score = defender_power['attack'] - attacker_power['defense']

    if attacker_score > defender_score:
        winner = attacker_city_id
    else:
        winner = defender_city_id

    # تسجيل المعركة
    cursor.execute("""
        INSERT INTO battles (attacker_city_id, defender_city_id, attacker_power, defender_power, winner, created_at)
        VALUES (?,?,?,?,?,?)
    """, (
        attacker_city_id, defender_city_id,
        attacker_score, defender_score,
        winner, int(datetime.now().timestamp())
    ))
    battle_id = cursor.lastrowid

    # تحديث الخسائر لكل جانب
    # مبدئي: خسائر عشوائية بسيطة (قابل للتطوير)
    cursor.execute("SELECT id, quantity FROM city_troops WHERE city_id=?", (attacker_city_id,))
    for troop_id, qty in cursor.fetchall():
        lost = max(1, int(qty * 0.1))
        cursor.execute("""
            INSERT INTO battle_losses (battle_id, city_id, loss_type, troop_type_id, lost_quantity)
            VALUES (?,?,?,?,?)
        """, (battle_id, attacker_city_id, 'troop', troop_id, lost))

    cursor.execute("SELECT id, quantity FROM city_troops WHERE city_id=?", (defender_city_id,))
    for troop_id, qty in cursor.fetchall():
        lost = max(1, int(qty * 0.1))
        cursor.execute("""
            INSERT INTO battle_losses (battle_id, city_id, loss_type, troop_type_id, lost_quantity)
            VALUES (?,?,?,?,?)
        """, (battle_id, defender_city_id, 'troop', troop_id, lost))

    conn.commit()
    return {"battle_id": battle_id, "winner": winner, "attacker_power": attacker_score, "defender_power": defender_score}