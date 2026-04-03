# db_queries/daily_tasks_queries.py
import sqlite3, json, time, random
from database.connection import get_db_conn

# ══════════════════════════════════════
# توليد المهام اليومية لمدينة معينة
# ══════════════════════════════════════
def generate_daily_tasks_for_city(user_id, city_id):
    conn = get_db_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # حذف المهام السابقة للمدينة لليوم
    cursor.execute("DELETE FROM daily_tasks WHERE user_id=? AND city_id=?", (user_id, city_id))
    conn.commit()

    # استدعاء جميع المهام من pool
    cursor.execute("SELECT * FROM daily_tasks_pool")
    pool = [dict(row) for row in cursor.fetchall()]

    if len(pool) < 7:
        return "لا توجد مهام كافية في قاعدة المهام اليومية."

    # اختيار 7 مهام عشوائية
    chosen_tasks = random.sample(pool, 7)

    for task in chosen_tasks:
        task_data = {
            "id": task.get("id"),
            "type": task.get("type"),
            "description": task.get("description"),
            "asset_id": task.get("asset_id"),
            "troop_type_id": task.get("troop_type_id"),
            "equipment_type_id": task.get("equipment_type_id"),
            "required_level": task.get("required_level"),
            "required_quantity": task.get("required_quantity")
        }
        cursor.execute("""
            INSERT OR IGNORE INTO daily_tasks (user_id, city_id, task_data, assigned_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, city_id, json.dumps(task_data), int(time.time())))

    conn.commit()
    return "تم توليد 7 مهام يومية جديدة بنجاح! 🌟"

# ══════════════════════════════════════
# تحديث حالة المهام اليومية تلقائيًا
# ══════════════════════════════════════
def update_daily_tasks_status(user_id, city_id):
    conn = get_db_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, task_data FROM daily_tasks WHERE user_id=? AND city_id=?", (user_id, city_id))
    tasks = cursor.fetchall()

    for task in tasks:
        task_info = json.loads(task["task_data"])
        completed = 0

        if task_info["type"] == "upgrade_asset":
            cursor.execute("SELECT level FROM city_assets WHERE city_id=? AND asset_id=?", (city_id, task_info["asset_id"]))
            asset = cursor.fetchone()
            if asset and asset["level"] >= task_info.get("required_level", 2):
                completed = 1

        elif task_info["type"] == "upgrade_city_level":
            cursor.execute("SELECT level FROM cities WHERE id=?", (city_id,))
            city = cursor.fetchone()
            if city and city["level"] >= task_info.get("required_level", 2):
                completed = 1

        elif task_info["type"] == "buy_troops":
            cursor.execute("SELECT quantity FROM city_troops WHERE city_id=? AND troop_type_id=?", (city_id, task_info["troop_type_id"]))
            row = cursor.fetchone()
            if row and row["quantity"] >= task_info.get("required_quantity", 5):
                completed = 1

        elif task_info["type"] == "buy_equipment":
            cursor.execute("SELECT quantity FROM city_equipment WHERE city_id=? AND equipment_type_id=?", (city_id, task_info["equipment_type_id"]))
            row = cursor.fetchone()
            if row and row["quantity"] >= task_info.get("required_quantity", 3):
                completed = 1

        cursor.execute("UPDATE daily_tasks SET completed=? WHERE id=?", (completed, task["id"]))

    conn.commit()

# ══════════════════════════════════════
# عرض المهام اليومية للمستخدم
# ══════════════════════════════════════
def show_daily_tasks(user_id, city_id):
    conn = get_db_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # إذا لم توجد مهام اليوم، توليدها
    cursor.execute("SELECT COUNT(*) FROM daily_tasks WHERE user_id=? AND city_id=?", (user_id, city_id))
    count = cursor.fetchone()[0]
    if count == 0:
        generate_daily_tasks_for_city(user_id, city_id)

    # تحديث حالة المهام قبل العرض
    update_daily_tasks_status(user_id, city_id)
    cursor.execute("SELECT * FROM daily_tasks WHERE user_id=? AND city_id=?", (user_id, city_id))
    tasks = cursor.fetchall()

    if not tasks:
        return "لا توجد مهام جديدة اليوم."

    output = "📝 مهامك اليومية:\n"
    for idx, task in enumerate(tasks, 1):
        task_info = json.loads(task["task_data"])
        status = "✅" if task["completed"] else "❌"  # sqlite3.Row indexed by column name
        output += f"{idx}. {task_info['description']} [{status}]\n"
    return output

# ══════════════════════════════════════
# جمع مكافآت المهام اليومية المكتملة
# ══════════════════════════════════════
def collect_daily_task_rewards(user_id, city_id):
    conn = get_db_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # تحديث حالة المهام أولًا
    update_daily_tasks_status(user_id, city_id)

    # إجمالي المهام
    cursor.execute("""
        SELECT COUNT(*) FROM daily_tasks
        WHERE user_id=? AND city_id=?
    """, (user_id, city_id))
    total_tasks = cursor.fetchone()[0]

    # المهام المكتملة
    cursor.execute("""
        SELECT COUNT(*) FROM daily_tasks
        WHERE user_id=? AND city_id=? AND completed=1
    """, (user_id, city_id))
    completed_tasks = cursor.fetchone()[0]

    # ❌ إذا لم يكمل كل المهام
    if completed_tasks < total_tasks:
        remaining = total_tasks - completed_tasks
        return f"❌ لم تكمل المهام بعد!\nباقي لك {remaining} مهمة.\nاكتب '<code>مهامي</code>' لمعرفة التفاصيل."

    # ✅ إذا مكتملة ولكن تم أخذ الجائزة
    cursor.execute("""
        SELECT COUNT(*) FROM daily_tasks
        WHERE user_id=? AND city_id=? AND reward_collected=1
    """, (user_id, city_id))
    collected = cursor.fetchone()[0]

    if collected == total_tasks:
        return "🎁 لقد استلمت مكافأة اليوم بالفعل!"

    # 🎉 إعطاء المكافأة (مرة واحدة فقط)
    rewards = []

    # مكافأة عامة (أفضل من مكافآت متفرقة)
    money = random.randint(200, 500)
    rewards.append(f"💰 +{money} ذهب")

    # مثال: إضافة جنود
    cursor.execute("""
        INSERT INTO city_troops (city_id, troop_type_id, quantity)
        VALUES (?,?,?)
        ON CONFLICT(city_id, troop_type_id) DO UPDATE SET
        quantity=quantity+excluded.quantity
    """, (city_id, 4, 3))  # قوات خاصة

    rewards.append("🔥 +3 قوات خاصة")

    # مثال: معدات
    cursor.execute("""
        INSERT INTO city_equipment (city_id, equipment_type_id, quantity)
        VALUES (?,?,?)
        ON CONFLICT(city_id, equipment_type_id) DO UPDATE SET
        quantity=quantity+excluded.quantity
    """, (city_id, 6, 2))  # دبابة

    rewards.append("🛡 +2 دبابة")

    # تعليم كل المهام كمستلمة
    cursor.execute("""
        UPDATE daily_tasks
        SET reward_collected=1
        WHERE user_id=? AND city_id=?
    """, (user_id, city_id))

    conn.commit()

    return "🎉 تم إكمال جميع المهام!\n\n" + "\n".join(rewards)

# ───── جلب مدينة المستخدم ─────
def get_user_city(user_id):
    """إرجاع أول مدينة يمتلكها المستخدم كقاموس"""
    conn = get_db_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM cities WHERE owner_id=? LIMIT 1", (user_id,))
    city = cursor.fetchone()
    if city:
        return dict(city)  # تحويل row إلى dict
    return None