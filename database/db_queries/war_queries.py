from ..connection import get_db_conn

# ─────────────────────────────
# 🪖 جلب جنود المدينة
# ─────────────────────────────
def get_city_troops(city_id):
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ct.troop_type_id, ct.quantity,
               tt.attack, tt.defense, tt.hp, tt.speed, tt.name_ar, tt.emoji
        FROM city_troops ct
        JOIN troop_types tt ON ct.troop_type_id = tt.id
        WHERE ct.city_id = ?
    """, (city_id,))

    return cursor.fetchall()


# ─────────────────────────────
# 🛡️ جلب معدات المدينة
# ─────────────────────────────
def get_city_equipment(city_id):
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ce.equipment_type_id, ce.quantity,
               et.attack_bonus, et.defense_bonus, et.special_effect,
               et.name_ar, et.emoji
        FROM city_equipment ce
        JOIN equipment_types et ON ce.equipment_type_id = et.id
        WHERE ce.city_id = ?
    """, (city_id,))

    return cursor.fetchall()


# ─────────────────────────────
# ➕ تحديث عدد الجنود (بعد الخسائر)
# ─────────────────────────────
def update_troop_quantity(city_id, troop_type_id, new_quantity):
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE city_troops
        SET quantity = ?
        WHERE city_id = ? AND troop_type_id = ?
    """, (new_quantity, city_id, troop_type_id))

    conn.commit()


# ─────────────────────────────
# ➕ تحديث عدد المعدات
# ─────────────────────────────
def update_equipment_quantity(city_id, equipment_type_id, new_quantity):
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE city_equipment
        SET quantity = ?
        WHERE city_id = ? AND equipment_type_id = ?
    """, (new_quantity, city_id, equipment_type_id))

    conn.commit()


# ─────────────────────────────
# ⚔️ تسجيل المعركة
# ─────────────────────────────
def record_city_battle(attacker_city_id, defender_city_id,
                       attacker_power, defender_power,
                       winner, loot=0):
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO battles
        (attacker_city_id, defender_city_id, attacker_power, defender_power, winner, loot)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (attacker_city_id, defender_city_id, attacker_power, defender_power, winner, loot))

    conn.commit()
    return cursor.lastrowid


# ─────────────────────────────
# 💥 تسجيل الخسائر
# ─────────────────────────────
def add_battle_loss(battle_id, city_id,
                    loss_type,
                    troop_type_id=None,
                    equipment_type_id=None,
                    lost_quantity=0):
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO battle_losses
        (battle_id, city_id, loss_type, troop_type_id, equipment_type_id, lost_quantity)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (battle_id, city_id, loss_type, troop_type_id, equipment_type_id, lost_quantity))

    conn.commit()


# ─────────────────────────────
# 🔄 تطبيق الخسائر على الجنود
# ─────────────────────────────
def apply_troop_losses(city_id, losses):
    """
    losses = [{"troop_type_id": 1, "lost": 50}, ...]
    """
    conn = get_db_conn()
    cursor = conn.cursor()

    for loss in losses:
        cursor.execute("""
            SELECT quantity FROM city_troops
            WHERE city_id = ? AND troop_type_id = ?
        """, (city_id, loss["troop_type_id"]))

        row = cursor.fetchone()
        if not row:
            continue

        new_qty = max(0, row["quantity"] - loss["lost"])

        cursor.execute("""
            UPDATE city_troops
            SET quantity = ?
            WHERE city_id = ? AND troop_type_id = ?
        """, (new_qty, city_id, loss["troop_type_id"]))

    conn.commit()
    
# ─────────────────────────────
# 🔄 تطبيق خسائر المعدات
# ─────────────────────────────
def apply_equipment_losses(city_id, losses):
    """
    losses = [{"equipment_type_id": 1, "lost": 10}, ...]
    """
    conn = get_db_conn()
    cursor = conn.cursor()

    for loss in losses:
        cursor.execute("""
            SELECT quantity FROM city_equipment
            WHERE city_id = ? AND equipment_type_id = ?
        """, (city_id, loss["equipment_type_id"]))

        row = cursor.fetchone()
        if not row:
            continue

        new_qty = max(0, row["quantity"] - loss["lost"])

        cursor.execute("""
            UPDATE city_equipment
            SET quantity = ?
            WHERE city_id = ? AND equipment_type_id = ?
        """, (new_qty, city_id, loss["equipment_type_id"]))

    conn.commit()


# ─────────────────────────────
# 💰 تحديث موارد المدينة (الغنائم)
# ─────────────────────────────
def update_city_resources(city_id, loot=0):
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE city_budget
        SET current_budget = current_budget + ?
        WHERE city_id = ?
    """, (loot, city_id))

    conn.commit()


# ─────────────────────────────
# 📊 تفاصيل معركة
# ─────────────────────────────
def get_battle_details(battle_id):
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM battles WHERE id = ?", (battle_id,))
    battle = cursor.fetchone()

    cursor.execute("""
        SELECT *
        FROM battle_losses
        WHERE battle_id = ?
    """, (battle_id,))
    losses = cursor.fetchall()

    return {
        "battle": battle,
        "losses": losses
    }

def get_all_troop_types():
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM troop_types")
    return cursor.fetchall()

def get_city_troop(city_id, troop_type_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT *
        FROM city_troops
        WHERE city_id = ? AND troop_type_id = ?
    """, (city_id, troop_type_id))
    return cursor.fetchone()

def add_city_troops(city_id, troop_type_id, quantity):
    conn = get_db_conn()
    cursor = conn.cursor()

    # هل القوات موجودة مسبقًا؟
    cursor.execute("""
        SELECT quantity FROM city_troops
        WHERE city_id = ? AND troop_type_id = ?
    """, (city_id, troop_type_id))
    row = cursor.fetchone()

    if row:
        new_qty = row["quantity"] + quantity
        cursor.execute("""
            UPDATE city_troops
            SET quantity = ?
            WHERE city_id = ? AND troop_type_id = ?
        """, (new_qty, city_id, troop_type_id))
    else:
        cursor.execute("""
            INSERT INTO city_troops (city_id, troop_type_id, quantity)
            VALUES (?, ?, ?)
        """, (city_id, troop_type_id, quantity))

    conn.commit()

# ─────────────────────────────
# 🃏 (اختياري) بطاقات المدينة
# ─────────────────────────────
def get_city_cards(city_id):
    """
    مثال بسيط (تعدل لاحقًا حسب نظامك)
    """
    return []


def get_troop_type_by_id(troop_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM troop_types WHERE id = ?", (troop_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


# ─────────────────────────────
# 🛡 جلب كل أنواع المعدات
# ─────────────────────────────
def get_all_equipment_types():
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM equipment_types ORDER BY base_cost")
    return cursor.fetchall()


def get_equipment_type_by_id(eq_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM equipment_types WHERE id = ?", (eq_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_city_equipment_item(city_id: int, eq_type_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM city_equipment
        WHERE city_id = ? AND equipment_type_id = ?
    """, (city_id, eq_type_id))
    return cursor.fetchone()


def add_city_equipment(city_id: int, eq_type_id: int, quantity: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT quantity FROM city_equipment
        WHERE city_id = ? AND equipment_type_id = ?
    """, (city_id, eq_type_id))
    row = cursor.fetchone()
    if row:
        cursor.execute("""
            UPDATE city_equipment SET quantity = quantity + ?
            WHERE city_id = ? AND equipment_type_id = ?
        """, (quantity, city_id, eq_type_id))
    else:
        cursor.execute("""
            INSERT INTO city_equipment (city_id, equipment_type_id, quantity)
            VALUES (?, ?, ?)
        """, (city_id, eq_type_id, quantity))
    conn.commit()
