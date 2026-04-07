"""
نظام التوازن والعمق — خسائر المدن، حماية الخسارة، تعب الجيش،
مزايا الدفاع، الاستخبارات المضادة، حماية المبتدئين، سجل الحروب
"""
import time
import random

from database.connection import get_db_conn
from database.db_queries.countries_queries import get_all_cities_of_country_by_country_id
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

# ══════════════════════════════════════════
# ⚙️ ثوابت التوازن
# ══════════════════════════════════════════

MAX_LOSS_PCT          = 0.60   # حد أقصى للخسارة 60%
WEAK_DEFENDER_THRESH  = 0.20   # إذا كان المدافع < 20% من المهاجم → حماية إضافية
WEAK_DEFENDER_CAP     = 0.40   # حد الخسارة للمدافع الضعيف 40%
DEFENDER_BONUS        = 0.15   # +15% قوة دفاع للمدافع
TERRAIN_BONUS_MIN     = 0.05   # 5% حد أدنى لمكافأة التضاريس
TERRAIN_BONUS_MAX     = 0.10   # 10% حد أقصى لمكافأة التضاريس
FATIGUE_PER_BATTLE    = 0.08   # 8% تعب لكل معركة
FATIGUE_MAX           = 0.40   # 40% حد أقصى للتعب
FATIGUE_RECOVERY_RATE = 0.02   # 2% تعافٍ لكل ساعة
BEGINNER_LEVEL_THRESH = 3      # مستوى المدينة الذي يمنع الهجوم
CITY_DAMAGE_CHANCE    = 0.60   # 60% احتمال تضرر مبنى بعد المعركة
REPAIR_COST_RATIO     = 0.50   # تكلفة الإصلاح = 50% من السعر الأصلي
REPAIR_TIME_BASE      = 3600   # ثانية وقت الإصلاح الأساسي


# ══════════════════════════════════════════
# 🛡️ 1. حماية الخسارة القصوى
# ══════════════════════════════════════════

def clamp_loss_pct(raw_loss_pct: float, attacker_power: float,
                   defender_power: float, is_defender: bool) -> float:
    """
    يُقيّد نسبة الخسارة بحد أقصى 60%.
    إذا كان المدافع ضعيفاً جداً → حماية إضافية (40%).
    """
    cap = MAX_LOSS_PCT

    if is_defender and attacker_power > 0:
        ratio = defender_power / attacker_power
        if ratio < WEAK_DEFENDER_THRESH:
            cap = WEAK_DEFENDER_CAP

    return max(0.0, min(raw_loss_pct, cap))


# ══════════════════════════════════════════
# 🏰 2. مزايا الدفاع
# ══════════════════════════════════════════

def apply_defender_advantage(def_power: float) -> float:
    """
    يُضيف مكافأة الدفاع (+15%) ومكافأة التضاريس العشوائية (5–10%).
    """
    terrain_bonus = random.uniform(TERRAIN_BONUS_MIN, TERRAIN_BONUS_MAX)
    total_bonus   = DEFENDER_BONUS + terrain_bonus
    return max(0.0, def_power * (1 + total_bonus))


# ══════════════════════════════════════════
# 😴 3. تعب الجيش
# ══════════════════════════════════════════

def get_fatigue(country_id: int) -> float:
    """يرجع مستوى التعب الحالي (0.0 – 0.40)"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT fatigue_level, last_battle_at FROM army_fatigue WHERE country_id = ?
    """, (country_id,))
    row = cursor.fetchone()
    if not row:
        return 0.0

    fatigue, last_battle = row[0], row[1]
    # تعافٍ تلقائي بمرور الوقت
    hours_passed = (int(time.time()) - last_battle) / 3600
    recovered    = hours_passed * FATIGUE_RECOVERY_RATE
    current      = max(0.0, fatigue - recovered)
    return round(current, 4)


def add_fatigue(country_id: int):
    """يُضيف تعباً بعد كل معركة"""
    current = get_fatigue(country_id)
    new_val = min(FATIGUE_MAX, current + FATIGUE_PER_BATTLE)
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO army_fatigue (country_id, fatigue_level, last_battle_at)
        VALUES (?, ?, ?)
        ON CONFLICT(country_id) DO UPDATE SET fatigue_level = ?, last_battle_at = ?
    """, (country_id, new_val, int(time.time()), new_val, int(time.time())))
    conn.commit()


def apply_fatigue_to_power(power: float, country_id: int) -> float:
    """يُطبّق تأثير التعب على القوة: power × (1 - fatigue%)"""
    fatigue = get_fatigue(country_id)
    return max(0.0, power * (1 - fatigue))


def get_fatigue_display(country_id: int) -> str:
    """نص عرض التعب للواجهة"""
    f = get_fatigue(country_id)
    pct = int(f * 100)
    if pct == 0:
        return "✅ لا يوجد تعب"
    elif pct < 20:
        return f"😐 تعب خفيف: {pct}%"
    elif pct < 35:
        return f"😓 تعب متوسط: {pct}%"
    else:
        return f"😩 تعب شديد: {pct}% — قوتك منخفضة!"


# ══════════════════════════════════════════
# 🏚️ 4. تضرر مباني المدينة
# ══════════════════════════════════════════

def damage_defender_assets(defender_country_id: int, damage_count: int = None):
    """
    يُتلف عشوائياً 1–3 مباني في مدن المدافع.
    يُقلّل المستوى بمقدار 1 أو يُعطّل المبنى مؤقتاً.
    يرجع قائمة المباني المتضررة.
    """
    cities = get_all_cities_of_country_by_country_id(defender_country_id)
    if not cities:
        return []

    conn = get_db_conn()
    cursor = conn.cursor()
    damaged = []

    count = damage_count or random.randint(1, 3)

    for _ in range(count):
        if not cities:
            break
        city = random.choice(cities)
        city_id = city["id"] if isinstance(city, dict) else city[0]

        # جلب مبانٍ قابلة للتضرر
        cursor.execute("""
            SELECT id, building_type, level FROM buildings
            WHERE city_id = ? AND level > 1
            ORDER BY RANDOM() LIMIT 1
        """, (city_id,))
        building = cursor.fetchone()

        if building:
            bid, btype, blevel = building[0], building[1], building[2]
            if random.random() < 0.5:
                # تقليل المستوى
                new_level = max(1, blevel - 1)
                cursor.execute("UPDATE buildings SET level = ? WHERE id = ?", (new_level, bid))
                damaged.append({"type": "level_down", "building": btype, "city_id": city_id})
            else:
                # تعطيل مؤقت (30 دقيقة)
                disabled_until = int(time.time()) + 1800
                try:
                    cursor.execute("""
                        UPDATE city_assets SET disabled_until = ?
                        WHERE city_id = ? AND asset_type = ?
                    """, (disabled_until, city_id, btype))
                except Exception:
                    pass
                damaged.append({"type": "disabled", "building": btype, "city_id": city_id,
                                 "until": disabled_until})

    conn.commit()
    return damaged


def is_asset_disabled(city_id: int, asset_type: str) -> bool:
    """يتحقق إذا كان المبنى معطلاً"""
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    try:
        cursor.execute("""
            SELECT disabled_until FROM city_assets
            WHERE city_id = ? AND asset_type = ? AND disabled_until > ?
        """, (city_id, asset_type, now))
        return cursor.fetchone() is not None
    except Exception:
        return False


# ══════════════════════════════════════════
# 🔧 5. طابور الإصلاح المكلف
# ══════════════════════════════════════════

def queue_repair(city_id: int, equipment_type_id: int, quantity: int,
                 base_cost: float) -> dict:
    """
    يُضيف معدة لطابور الإصلاح.
    التكلفة = 50% من السعر الأصلي × الكمية.
    الوقت = BASE_REPAIR_TIME ثانية.
    """
    repair_cost      = round(quantity * base_cost * REPAIR_COST_RATIO, 2)
    repair_ready_at  = int(time.time()) + REPAIR_TIME_BASE

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO repair_queue
        (city_id, equipment_type_id, quantity, repair_cost, repair_ready_at)
        VALUES (?, ?, ?, ?, ?)
    """, (city_id, equipment_type_id, quantity, repair_cost, repair_ready_at))
    conn.commit()
    return {"id": cursor.lastrowid, "cost": repair_cost, "ready_at": repair_ready_at}


def get_repair_queue(country_id: int) -> list:
    """يرجع طابور الإصلاح لدولة"""
    cities = get_all_cities_of_country_by_country_id(country_id)
    if not cities:
        return []
    conn = get_db_conn()
    cursor = conn.cursor()
    result = []
    for city in cities:
        cid = city["id"] if isinstance(city, dict) else city[0]
        cursor.execute("""
            SELECT rq.*, et.name_ar, et.emoji
            FROM repair_queue rq
            JOIN equipment_types et ON rq.equipment_type_id = et.id
            WHERE rq.city_id = ? AND rq.status = 'pending'
            ORDER BY rq.repair_ready_at ASC
        """, (cid,))
        result.extend([dict(r) for r in cursor.fetchall()])
    return result


def complete_ready_repairs(country_id: int) -> int:
    """يُكمل الإصلاحات الجاهزة ويُعيد المعدات للخدمة"""
    cities = get_all_cities_of_country_by_country_id(country_id)
    if not cities:
        return 0
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    total = 0

    for city in cities:
        cid = city["id"] if isinstance(city, dict) else city[0]
        cursor.execute("""
            SELECT id, equipment_type_id, quantity FROM repair_queue
            WHERE city_id = ? AND status = 'pending' AND repair_ready_at <= ?
        """, (cid, now))
        ready = cursor.fetchall()
        for row in ready:
            rid, eid, qty = row[0], row[1], row[2]
            cursor.execute("""
                INSERT INTO city_equipment (city_id, equipment_type_id, quantity)
                VALUES (?, ?, ?)
                ON CONFLICT(city_id, equipment_type_id) DO UPDATE SET quantity = quantity + ?
            """, (cid, eid, qty, qty))
            cursor.execute("UPDATE repair_queue SET status = 'done' WHERE id = ?", (rid,))
            total += qty

    conn.commit()
    return total


def pay_and_start_repair(user_id: int, country_id: int) -> tuple:
    """
    يدفع تكلفة الإصلاح ويبدأ الطابور.
    يرجع (True, msg) أو (False, msg)
    """
    queue = get_repair_queue(country_id)
    if not queue:
        return False, "❌ لا توجد معدات في طابور الإصلاح."

    total_cost = sum(r["repair_cost"] for r in queue)
    from database.db_queries.bank_queries import get_user_balance, deduct_user_balance
    balance = get_user_balance(user_id)
    if balance < total_cost:
        return False, f"❌ تحتاج {total_cost:.0f} {CURRENCY_ARABIC_NAME} للإصلاح (رصيدك: {balance:.0f})"

    deduct_user_balance(user_id, total_cost)
    return True, f"🔧 بدأ الإصلاح! {len(queue)} نوع معدات | تكلفة: {total_cost:.0f} {CURRENCY_ARABIC_NAME}"


# ══════════════════════════════════════════
# 🕵️ 6. الاستخبارات المضادة
# ══════════════════════════════════════════

def counter_intelligence_check(attacker_cid: int, target_cid: int) -> dict:
    """
    يتحقق من احتمال اكتشاف الجاسوس.
    يرجع dict: {detected, spy_killed, fake_intel}
    """
    from database.db_queries.advanced_war_queries import get_spy_units, ensure_spy_units
    ensure_spy_units(attacker_cid)
    ensure_spy_units(target_cid)

    atk_spy = get_spy_units(attacker_cid)
    def_spy = get_spy_units(target_cid)

    spy_lvl    = atk_spy["spy_level"]
    counter_lvl = def_spy["counter_intel"] + def_spy["defense_level"]

    # احتمال الاكتشاف يرتفع مع قوة الاستخبارات المضادة
    detect_chance = max(0.0, min(0.8, (counter_lvl - spy_lvl) * 0.15))

    # ─── تطبيق حدث مكافحة التجسس ───
    try:
        from modules.progression.global_events import get_event_effect
        ci_bonus = get_event_effect("counter_intel_bonus")
        if ci_bonus > 0:
            detect_chance = min(0.9, detect_chance + ci_bonus)
    except Exception:
        pass

    roll = random.random()

    if roll < detect_chance:
        # تم اكتشاف الجاسوس
        spy_killed  = random.random() < 0.5
        fake_intel  = not spy_killed  # إذا لم يُقتل → معلومات مزيفة
        return {"detected": True, "spy_killed": spy_killed, "fake_intel": fake_intel}

    return {"detected": False, "spy_killed": False, "fake_intel": False}


def generate_fake_intel(target_cid: int) -> str:
    """يولّد معلومات مزيفة متقنة"""
    from modules.war.power_calculator import get_country_power
    real = get_country_power(target_cid)
    # تضخيم أو تقليص عشوائي
    fake = real * random.uniform(0.3, 2.5)
    return (
        f"💀 <b>معلومات مزيفة (تحذير شديد!)</b>\n"
        f"القوة المُبلَّغة: {fake:.0f}\n"
        f"⚠️ قد تكون هذه المعلومات مُضلِّلة!"
    )


# ══════════════════════════════════════════
# 🛡️ 7. حماية المبتدئين
# ══════════════════════════════════════════

def is_beginner_protected(defender_country_id: int) -> bool:
    """
    يتحقق إذا كانت الدولة محمية (كل مدنها مستوى < 3).
    """
    cities = get_all_cities_of_country_by_country_id(defender_country_id)
    if not cities:
        return False

    conn = get_db_conn()
    cursor = conn.cursor()
    for city in cities:
        cid = city["id"] if isinstance(city, dict) else city[0]
        cursor.execute("SELECT level FROM cities WHERE id = ?", (cid,))
        row = cursor.fetchone()
        if row and row[0] >= BEGINNER_LEVEL_THRESH:
            return False  # مدينة واحدة على الأقل متقدمة → لا حماية

    return True  # كل المدن مستوى < 3 → محمية


# ══════════════════════════════════════════
# 📜 8. سجل الحروب
# ══════════════════════════════════════════

def record_battle_history(battle_id: int, attacker_cid: int, defender_cid: int,
                           winner_cid, atk_loss_pct: float, def_loss_pct: float,
                           loot: float, battle_type: str, duration: int):
    """يُسجّل المعركة في سجل الحروب"""
    conn = get_db_conn()
    cursor = conn.cursor()

    def _cname(cid):
        if not cid:
            return "—"
        cursor.execute("SELECT name FROM countries WHERE id = ?", (cid,))
        r = cursor.fetchone()
        return r[0] if r else str(cid)

    cursor.execute("""
        INSERT INTO battle_history
        (battle_id, attacker_country_id, defender_country_id,
         attacker_name, defender_name, winner_country_id,
         attacker_losses_pct, defender_losses_pct, loot, battle_type, duration_seconds)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (battle_id, attacker_cid, defender_cid,
          _cname(attacker_cid), _cname(defender_cid), winner_cid,
          round(atk_loss_pct, 1), round(def_loss_pct, 1),
          round(loot, 2), battle_type, duration))
    conn.commit()


def get_battle_history(country_id: int, limit: int = 15) -> list:
    """يرجع سجل الحروب لدولة"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM battle_history
        WHERE attacker_country_id = ? OR defender_country_id = ?
        ORDER BY created_at DESC LIMIT ?
    """, (country_id, country_id, limit))
    return [dict(r) for r in cursor.fetchall()]


def get_global_war_log(limit: int = 20) -> list:
    """يرجع آخر المعارك على مستوى اللعبة"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM battle_history ORDER BY created_at DESC LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


def format_history_entry(entry: dict, viewer_country_id: int) -> str:
    """يُنسّق سطر واحد من سجل الحروب"""
    is_attacker = entry["attacker_country_id"] == viewer_country_id
    role        = "مهاجم" if is_attacker else "مدافع"
    won         = entry["winner_country_id"] == viewer_country_id
    icon        = "🏆" if won else ("💀" if entry["winner_country_id"] else "🤝")
    enemy       = entry["defender_name"] if is_attacker else entry["attacker_name"]
    my_loss     = entry["attacker_losses_pct"] if is_attacker else entry["defender_losses_pct"]
    type_ar     = {"normal": "عادي", "sudden": "مباغت", "fake": "وهمي",
                   "building_raid": "غارة"}.get(entry["battle_type"], entry["battle_type"])
    ts          = time.strftime("%m/%d %H:%M", time.localtime(entry["created_at"]))

    return (
        f"{icon} #{entry['battle_id']} | {role} ضد {enemy}\n"
        f"   {type_ar} | خسرت {my_loss:.0f}% | 💰 {entry['loot']:.0f} | {ts}"
    )
