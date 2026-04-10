# database/db_queries/daily_tasks_queries.py
"""
Daily task system — generation, status checking, and reward collection.

Design principles:
  - One set of tasks per city per calendar day (Yemen TZ = UTC+3).
  - UNIQUE(city_id, date_key, task_pool_id) prevents any duplicate.
  - Pool is built once per day; expands automatically if exhausted.
  - Full reset (pool + tasks) happens at midnight Yemen time.
  - No full pool rebuild on every request — pool is cached in DB.

Task types and completion checks:
  upgrade_asset      — city_assets MAX(level) >= required_level
  buy_troops         — city_troops.quantity >= required_quantity
  buy_equipment      — city_equipment.quantity >= required_quantity
  upgrade_city_level — cities.level >= required_level
  accumulate_balance — user_accounts.balance >= required_quantity
  total_army_power   — computed power >= required_quantity
  reach_asset_count  — SUM(city_assets.quantity) for sector >= required_quantity
  collect_income     — income_collected counter in task_data >= required_quantity
"""
import sqlite3
import json
import time
import random
import threading
from datetime import datetime, timezone, timedelta

from database.connection import get_db_conn

# ── Constants ────────────────────────────────────────────────────
TASKS_PER_DAY   = 7
YEMEN_TZ        = timezone(timedelta(hours=3))   # Asia/Aden = UTC+3
_POOL_LOCK      = threading.Lock()               # guards pool expansion

_DIFF_LABEL = {1: "🟢 سهل", 2: "🟡 متوسط", 3: "🔴 صعب"}
_CAT_EMOJI  = {
    "development": "🏗",
    "military":    "⚔️",
    "economy":     "💰",
    "general":     "📋",
}


# ══════════════════════════════════════════════════════════════════
# Timezone helpers
# ══════════════════════════════════════════════════════════════════

def _today_yemen() -> str:
    """Returns today's date string YYYY-MM-DD in Yemen timezone."""
    return datetime.now(YEMEN_TZ).strftime("%Y-%m-%d")


def _seconds_until_midnight_yemen() -> float:
    """Seconds remaining until midnight in Yemen timezone."""
    now    = datetime.now(YEMEN_TZ)
    midnight = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return (midnight - now).total_seconds()


# ══════════════════════════════════════════════════════════════════
# Pool management
# ══════════════════════════════════════════════════════════════════

def _build_pool(conn, date_key: str):
    """
    Generates all task rows for today and inserts them into daily_tasks_pool.
    Reads asset/troop/equipment IDs from the DB — never hardcoded.
    Uses INSERT OR IGNORE so it is safe to call multiple times.
    """
    cursor = conn.cursor()

    cursor.execute("SELECT id, name_ar FROM assets ORDER BY id")
    assets = cursor.fetchall()
    cursor.execute("SELECT id, name_ar FROM troop_types ORDER BY id")
    troops = cursor.fetchall()
    cursor.execute("SELECT id, name_ar FROM equipment_types ORDER BY id")
    equipment = cursor.fetchall()

    if not assets or not troops or not equipment:
        return  # reference tables not seeded yet

    rows = []

    # 1. upgrade_asset — levels 2–8 per asset
    for a in assets:
        aid, name = a["id"], a["name_ar"]
        for lvl in range(2, 9):
            diff = 1 if lvl <= 3 else (2 if lvl <= 6 else 3)
            rows.append(("upgrade_asset",
                         f"رفع مستوى {name} إلى {lvl}",
                         aid, None, None, lvl, None,
                         150 * lvl * diff, None, diff, "development", date_key))

    # 2. buy_troops — 5 quantity tiers per troop type
    for qty, diff, gold in [(5,1,100),(10,1,180),(20,2,350),(35,2,550),(50,3,800)]:
        for t in troops:
            rows.append(("buy_troops",
                         f"شراء {qty} {t['name_ar']}",
                         None, t["id"], None, None, qty,
                         gold, None, diff, "military", date_key))

    # 3. buy_equipment — 5 quantity tiers per equipment type
    for qty, diff, gold in [(1,1,200),(2,1,350),(3,2,500),(5,2,750),(8,3,1100)]:
        for e in equipment:
            rows.append(("buy_equipment",
                         f"شراء {qty} {e['name_ar']}",
                         None, None, e["id"], None, qty,
                         gold, None, diff, "military", date_key))

    # 4. upgrade_city_level — levels 2–10
    for lvl in range(2, 11):
        diff = 1 if lvl <= 3 else (2 if lvl <= 6 else 3)
        rows.append(("upgrade_city_level",
                     f"رفع مستوى المدينة إلى {lvl}",
                     None, None, None, lvl, None,
                     300 * lvl * diff, None, diff, "development", date_key))

    # 5. accumulate_balance
    for target, diff, gold in [
        (500,1,100),(1000,1,180),(2500,1,350),(5000,2,600),
        (10000,2,1000),(25000,3,2000),(50000,3,3500),(100000,3,5000)
    ]:
        rows.append(("accumulate_balance",
                     f"اجمع رصيداً يبلغ {target:,} في البنك",
                     None, None, None, None, target,
                     gold, None, diff, "economy", date_key))

    # 6. total_army_power
    for target, diff, gold in [
        (500,1,200),(1000,1,350),(2500,2,600),
        (5000,2,1000),(10000,3,1800),(25000,3,3000)
    ]:
        rows.append(("total_army_power",
                     f"ابلغ قوة جيش إجمالية {target:,}",
                     None, None, None, None, target,
                     gold, None, diff, "military", date_key))

    # 7. reach_asset_count (required_level = sector_id)
    sectors = {1:"الصحة", 2:"التعليم", 3:"الاقتصاد", 4:"البنية التحتية"}
    for sid, label in sectors.items():
        for count, diff, gold in [(3,1,200),(5,1,350),(8,2,550),(12,2,800),(20,3,1400)]:
            rows.append(("reach_asset_count",
                         f"امتلك {count} وحدات من قطاع {label}",
                         None, None, None, sid, count,
                         gold, None, diff, "development", date_key))

    # 8. collect_income
    for times, diff, gold in [(1,1,150),(2,1,280),(3,2,420),(5,2,650)]:
        rows.append(("collect_income",
                     f"اجمع دخل مدينتك {times} {'مرة' if times==1 else 'مرات'}",
                     None, None, None, None, times,
                     gold, None, diff, "economy", date_key))

    cursor.executemany("""
        INSERT OR IGNORE INTO daily_tasks_pool
        (type, description, asset_id, troop_type_id, equipment_type_id,
         required_level, required_quantity, reward_gold, reward_troops,
         difficulty, category, pool_date)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    conn.commit()


def _get_pool_for_today(cursor) -> list[dict]:
    """Returns all pool rows for today. Expands pool if empty."""
    today = _today_yemen()
    cursor.execute(
        "SELECT * FROM daily_tasks_pool WHERE pool_date = ?", (today,)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    if not rows:
        # Pool was cleared or not yet built — rebuild under lock
        with _POOL_LOCK:
            cursor.execute(
                "SELECT COUNT(*) AS c FROM daily_tasks_pool WHERE pool_date = ?",
                (today,)
            )
            if cursor.fetchone()["c"] == 0:
                _build_pool(cursor.connection, today)
            cursor.execute(
                "SELECT * FROM daily_tasks_pool WHERE pool_date = ?", (today,)
            )
            rows = [dict(r) for r in cursor.fetchall()]
    return rows


def _expand_pool_if_needed(cursor, needed: int):
    """
    If fewer than `needed` unused pool rows remain for today,
    appends extra rows by varying quantities on existing task types.
    Called under _POOL_LOCK.
    """
    today = _today_yemen()
    cursor.execute(
        "SELECT COUNT(*) AS c FROM daily_tasks_pool WHERE pool_date = ?", (today,)
    )
    current = cursor.fetchone()["c"]
    if current >= needed:
        return

    # Generate extra rows with randomised quantities
    cursor.execute("SELECT id, name_ar FROM assets ORDER BY RANDOM() LIMIT 20")
    assets = cursor.fetchall()
    cursor.execute("SELECT id, name_ar FROM troop_types ORDER BY RANDOM() LIMIT 10")
    troops = cursor.fetchall()

    extra = []
    for a in assets:
        for lvl in random.sample(range(2, 11), min(3, 9)):
            diff = 1 if lvl <= 3 else (2 if lvl <= 6 else 3)
            desc = f"رفع مستوى {a['name_ar']} إلى {lvl} [+]"
            extra.append(("upgrade_asset", desc,
                          a["id"], None, None, lvl, None,
                          150 * lvl * diff, None, diff, "development", today))

    for t in troops:
        qty = random.choice([8, 12, 15, 25, 40, 60])
        diff = 1 if qty <= 10 else (2 if qty <= 30 else 3)
        desc = f"شراء {qty} {t['name_ar']} [+]"
        extra.append(("buy_troops", desc,
                      None, t["id"], None, None, qty,
                      100 * qty // 5, None, diff, "military", today))

    if extra:
        cursor.executemany("""
            INSERT OR IGNORE INTO daily_tasks_pool
            (type, description, asset_id, troop_type_id, equipment_type_id,
             required_level, required_quantity, reward_gold, reward_troops,
             difficulty, category, pool_date)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, extra)
        cursor.connection.commit()


# ══════════════════════════════════════════════════════════════════
# Daily reset — called at midnight Yemen time
# ══════════════════════════════════════════════════════════════════

def reset_daily_tasks():
    """
    Clears all tasks and pool rows from previous days.
    Called once at midnight Yemen time by the scheduler.
    Does NOT pre-generate tasks — they are generated lazily on first request.
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    today = _today_yemen()

    # Remove tasks from previous days
    cursor.execute("DELETE FROM daily_tasks WHERE date_key != ? AND date_key != ''", (today,))

    # Remove stale pool rows from previous days
    cursor.execute(
        "DELETE FROM daily_tasks_pool WHERE pool_date != ? AND pool_date != ''", (today,)
    )

    conn.commit()
    print(f"[DailyTasks] Reset complete for {today}")


# ══════════════════════════════════════════════════════════════════
# Task generation per city
# ══════════════════════════════════════════════════════════════════

def generate_daily_tasks_for_city(city_id: int) -> str:
    """
    Assigns TASKS_PER_DAY tasks to the city for today.
    - Idempotent: if tasks already exist for today, returns immediately.
    - Balanced: 3 easy + 3 medium + 1 hard.
    - No duplicate task IDs for the same city on the same day.
    - Expands pool automatically if not enough tasks remain.
    """
    today = _today_yemen()
    conn  = get_db_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # ── idempotency check ─────────────────────────────────────────
    cursor.execute(
        "SELECT COUNT(*) AS c FROM daily_tasks WHERE city_id = ? AND date_key = ?",
        (city_id, today)
    )
    if cursor.fetchone()["c"] >= TASKS_PER_DAY:
        return "✅ المهام اليومية محددة بالفعل."

    # ── get pool ──────────────────────────────────────────────────
    pool = _get_pool_for_today(cursor)

    # ── exclude task IDs already assigned to this city today ──────
    cursor.execute(
        "SELECT task_pool_id FROM daily_tasks WHERE city_id = ? AND date_key = ?",
        (city_id, today)
    )
    used_ids = {r["task_pool_id"] for r in cursor.fetchall()}
    available = [t for t in pool if t["id"] not in used_ids]

    # ── expand pool if needed ─────────────────────────────────────
    if len(available) < TASKS_PER_DAY:
        with _POOL_LOCK:
            _expand_pool_if_needed(cursor, len(pool) + TASKS_PER_DAY * 10)
        pool = _get_pool_for_today(cursor)
        available = [t for t in pool if t["id"] not in used_ids]

    if len(available) < TASKS_PER_DAY:
        # Absolute fallback — pick any from pool even if reused
        available = pool

    # ── balanced selection ────────────────────────────────────────
    by_diff: dict[int, list] = {1: [], 2: [], 3: []}
    for t in available:
        by_diff[t.get("difficulty", 1)].append(t)

    chosen: list[dict] = []
    for diff, count in [(1, 3), (2, 3), (3, 1)]:
        bucket = by_diff[diff]
        if bucket:
            chosen.extend(random.sample(bucket, min(count, len(bucket))))

    # top up if buckets were thin
    if len(chosen) < TASKS_PER_DAY:
        picked_ids = {t["id"] for t in chosen}
        extras = [t for t in available if t["id"] not in picked_ids]
        random.shuffle(extras)
        chosen.extend(extras[:TASKS_PER_DAY - len(chosen)])

    chosen = chosen[:TASKS_PER_DAY]

    # ── insert ────────────────────────────────────────────────────
    now = int(time.time())
    for task in chosen:
        snapshot = {
            "id":                task["id"],
            "type":              task["type"],
            "description":       task["description"],
            "asset_id":          task.get("asset_id"),
            "troop_type_id":     task.get("troop_type_id"),
            "equipment_type_id": task.get("equipment_type_id"),
            "required_level":    task.get("required_level"),
            "required_quantity": task.get("required_quantity"),
            "reward_gold":       task.get("reward_gold", 200),
            "difficulty":        task.get("difficulty", 1),
            "category":          task.get("category", "general"),
            "income_collected":  0,
        }
        cursor.execute("""
            INSERT OR IGNORE INTO daily_tasks
            (city_id, task_data, date_key, task_pool_id, assigned_at)
            VALUES (?, ?, ?, ?, ?)
        """, (city_id, json.dumps(snapshot, ensure_ascii=False),
              today, task["id"], now))

    conn.commit()
    return f"✅ تم توليد {TASKS_PER_DAY} مهام يومية جديدة!"


# ══════════════════════════════════════════════════════════════════
# Status checking
# ══════════════════════════════════════════════════════════════════

def update_daily_tasks_status(city_id: int):
    """Re-evaluates every incomplete task and marks completed=1 when met."""
    today = _today_yemen()
    conn  = get_db_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT owner_id FROM cities WHERE id = ?", (city_id,))
    city_row = cursor.fetchone()
    owner_id = city_row["owner_id"] if city_row else None

    cursor.execute("""
        SELECT id, task_data FROM daily_tasks
        WHERE city_id = ? AND date_key = ? AND completed = 0
    """, (city_id, today))

    for task in cursor.fetchall():
        info = json.loads(task["task_data"])
        if _check_task(cursor, city_id, owner_id, info):
            cursor.execute(
                "UPDATE daily_tasks SET completed = 1 WHERE id = ?", (task["id"],)
            )

    conn.commit()


def _check_task(cursor, city_id: int, owner_id, info: dict) -> bool:
    t       = info.get("type")
    req_lvl = info.get("required_level")
    req_qty = info.get("required_quantity")

    if t == "upgrade_asset":
        aid = info.get("asset_id")
        if not aid or not req_lvl:
            return False
        cursor.execute(
            "SELECT MAX(level) AS lvl FROM city_assets WHERE city_id=? AND asset_id=?",
            (city_id, aid)
        )
        row = cursor.fetchone()
        return bool(row and row["lvl"] and row["lvl"] >= req_lvl)

    if t == "upgrade_city_level":
        if not req_lvl:
            return False
        cursor.execute("SELECT level FROM cities WHERE id=?", (city_id,))
        row = cursor.fetchone()
        return bool(row and row["level"] >= req_lvl)

    if t == "buy_troops":
        tid = info.get("troop_type_id")
        if not tid or not req_qty:
            return False
        cursor.execute(
            "SELECT quantity FROM city_troops WHERE city_id=? AND troop_type_id=?",
            (city_id, tid)
        )
        row = cursor.fetchone()
        return bool(row and row["quantity"] >= req_qty)

    if t == "buy_equipment":
        eid = info.get("equipment_type_id")
        if not eid or not req_qty:
            return False
        cursor.execute(
            "SELECT quantity FROM city_equipment WHERE city_id=? AND equipment_type_id=?",
            (city_id, eid)
        )
        row = cursor.fetchone()
        return bool(row and row["quantity"] >= req_qty)

    if t == "accumulate_balance":
        if not owner_id or not req_qty:
            return False
        cursor.execute(
            "SELECT balance FROM user_accounts WHERE user_id=?", (owner_id,)
        )
        row = cursor.fetchone()
        return bool(row and row["balance"] >= req_qty)

    if t == "total_army_power":
        if not req_qty:
            return False
        return _compute_army_power(cursor, city_id) >= req_qty

    if t == "reach_asset_count":
        sector_id = req_lvl   # required_level stores sector_id
        if not sector_id or not req_qty:
            return False
        cursor.execute("""
            SELECT COALESCE(SUM(ca.quantity), 0) AS total
            FROM city_assets ca
            JOIN assets a ON ca.asset_id = a.id
            WHERE ca.city_id=? AND a.sector_id=?
        """, (city_id, sector_id))
        row = cursor.fetchone()
        return bool(row and row["total"] >= req_qty)

    if t == "collect_income":
        return bool(req_qty and info.get("income_collected", 0) >= req_qty)

    return False


def _compute_army_power(cursor, city_id: int) -> float:
    cursor.execute("""
        SELECT ct.quantity, tt.attack, tt.defense, tt.hp
        FROM city_troops ct JOIN troop_types tt ON ct.troop_type_id=tt.id
        WHERE ct.city_id=?
    """, (city_id,))
    troop_power = sum(
        r["quantity"] * ((r["attack"] * 1.2 + r["defense"]) * (r["hp"] / 100))
        for r in cursor.fetchall()
    )
    cursor.execute("""
        SELECT ce.quantity, et.attack_bonus, et.defense_bonus
        FROM city_equipment ce JOIN equipment_types et ON ce.equipment_type_id=et.id
        WHERE ce.city_id=?
    """, (city_id,))
    equip_power = sum(
        r["quantity"] * (r["attack_bonus"] + r["defense_bonus"])
        for r in cursor.fetchall()
    )
    return troop_power + equip_power


# ══════════════════════════════════════════════════════════════════
# Income counter (called from economy_service)
# ══════════════════════════════════════════════════════════════════

def increment_income_collected(city_id: int):
    """Increments the income_collected counter for active collect_income tasks."""
    today = _today_yemen()
    conn  = get_db_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, task_data FROM daily_tasks
        WHERE city_id=? AND date_key=? AND completed=0
    """, (city_id, today))

    for row in cursor.fetchall():
        info = json.loads(row["task_data"])
        if info.get("type") == "collect_income":
            info["income_collected"] = info.get("income_collected", 0) + 1
            cursor.execute(
                "UPDATE daily_tasks SET task_data=? WHERE id=?",
                (json.dumps(info, ensure_ascii=False), row["id"])
            )
    conn.commit()


# ══════════════════════════════════════════════════════════════════
# Display
# ══════════════════════════════════════════════════════════════════

def show_daily_tasks(city_id: int) -> str:
    today = _today_yemen()
    conn  = get_db_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) AS c FROM daily_tasks WHERE city_id=? AND date_key=?",
        (city_id, today)
    )
    if cursor.fetchone()["c"] == 0:
        generate_daily_tasks_for_city(city_id)

    update_daily_tasks_status(city_id)

    cursor.execute(
        "SELECT * FROM daily_tasks WHERE city_id=? AND date_key=?", (city_id, today)
    )
    tasks = cursor.fetchall()

    if not tasks:
        return "لا توجد مهام اليوم."

    completed = sum(1 for t in tasks if t["completed"])
    total     = len(tasks)

    lines = [f"📝 <b>مهام مدينتك اليومية</b> ({completed}/{total} مكتملة)\n"]
    for i, task in enumerate(tasks, 1):
        info   = json.loads(task["task_data"])
        status = "✅" if task["completed"] else "❌"
        diff   = _DIFF_LABEL.get(info.get("difficulty", 1), "")
        cat    = _CAT_EMOJI.get(info.get("category", "general"), "📋")
        gold   = info.get("reward_gold", 200)
        lines.append(
            f"{i}. {cat} {info['description']} {status}\n"
            f"   {diff} | 💰 {gold:,} ذهب\n"
        )

    if completed == total:
        lines.append("\n🎉 أكملت جميع المهام! اكتب <code>جائزة مهامي</code> لاستلام مكافأتك.")
    else:
        lines.append("\n💡 أكمل المهام واكتب <code>جائزة مهامي</code> لاستلام المكافأة.")

    return "".join(lines)


# ══════════════════════════════════════════════════════════════════
# Reward collection
# ══════════════════════════════════════════════════════════════════

def collect_daily_task_rewards(city_id: int) -> str:
    today = _today_yemen()
    conn  = get_db_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    update_daily_tasks_status(city_id)

    cursor.execute(
        "SELECT COUNT(*) AS c FROM daily_tasks WHERE city_id=? AND date_key=?",
        (city_id, today)
    )
    total = cursor.fetchone()["c"]

    cursor.execute(
        "SELECT COUNT(*) AS c FROM daily_tasks WHERE city_id=? AND date_key=? AND completed=1",
        (city_id, today)
    )
    completed = cursor.fetchone()["c"]

    if completed < total:
        return (f"❌ لم تكمل المهام بعد!\n"
                f"باقي لك {total - completed} مهمة.\n"
                f"اكتب <code>مهامي</code> لمعرفة التفاصيل.")

    cursor.execute(
        "SELECT COUNT(*) AS c FROM daily_tasks WHERE city_id=? AND date_key=? AND reward_collected=1",
        (city_id, today)
    )
    if cursor.fetchone()["c"] == total:
        return "🎁 لقد استلمت مكافأة اليوم بالفعل!"

    # ── compute reward ────────────────────────────────────────────
    cursor.execute(
        "SELECT task_data FROM daily_tasks WHERE city_id=? AND date_key=?",
        (city_id, today)
    )
    all_tasks  = cursor.fetchall()
    total_gold = sum(json.loads(t["task_data"]).get("reward_gold", 200) for t in all_tasks)
    hard_count = sum(
        1 for t in all_tasks
        if json.loads(t["task_data"]).get("difficulty", 1) == 3
    )
    if hard_count >= 1:
        total_gold = int(total_gold * 1.15)

    # ── pay gold ──────────────────────────────────────────────────
    cursor.execute("SELECT owner_id FROM cities WHERE id=?", (city_id,))
    city_row = cursor.fetchone()
    rewards  = [f"💰 +{total_gold:,} ذهب"]

    if city_row and city_row["owner_id"]:
        try:
            from database.db_queries.bank_queries import update_bank_balance
            update_bank_balance(city_row["owner_id"], total_gold)
        except Exception:
            pass

    # ── bonus troops ──────────────────────────────────────────────
    bonus_qty = 2 + hard_count
    try:
        cursor.execute("""
            INSERT INTO city_troops (city_id, troop_type_id, quantity)
            VALUES (?,4,?)
            ON CONFLICT(city_id, troop_type_id)
            DO UPDATE SET quantity = quantity + excluded.quantity
        """, (city_id, bonus_qty))
        rewards.append(f"🔥 +{bonus_qty} قوات خاصة")
    except Exception:
        pass

    cursor.execute(
        "UPDATE daily_tasks SET reward_collected=1 WHERE city_id=? AND date_key=?",
        (city_id, today)
    )
    conn.commit()

    return "🎉 <b>تم إكمال جميع المهام!</b>\n\n" + "\n".join(rewards)


# ══════════════════════════════════════════════════════════════════
# Helper
# ══════════════════════════════════════════════════════════════════

def get_user_city(telegram_user_id: int) -> dict | None:
    conn = get_db_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM cities WHERE owner_id=? LIMIT 1", (telegram_user_id,))
    row = cursor.fetchone()
    return dict(row) if row else None
