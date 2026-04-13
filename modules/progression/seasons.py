"""
نظام المواسم — إعادة ضبط دورية مع مكافآت للفائزين
"""
import time
from database.connection import get_db_conn
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME, WARRIOR_OF_SEASON_AWARD, KNIGHT_OF_SEASON_AWARD, SEASON_CHAMPION_AWARD


def _c(name, default):
    try:
        from core.admin import get_const_int, get_const_float
        if isinstance(default, float):
            return get_const_float(name, default)
        return get_const_int(name, int(default))
    except Exception:
        return default


# ══════════════════════════════════════════
# 🗓️ إدارة المواسم
# ══════════════════════════════════════════

def get_active_season() -> dict | None:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM seasons WHERE status = 'active' ORDER BY started_at DESC LIMIT 1
    """)
    row = cursor.fetchone()
    return dict(row) if row else None


def create_season(name: str = None) -> int:
    """يُنشئ موسماً جديداً"""
    conn = get_db_conn()
    cursor = conn.cursor()
    now      = int(time.time())
    duration = _c("season_duration_days", 30) * 86400
    ends_at  = now + duration
    season_name = name or f"موسم {_get_next_season_number()}"

    cursor.execute("""
        INSERT INTO seasons (name, started_at, ends_at, status)
        VALUES (?, ?, ?, 'active')
    """, (season_name, now, ends_at))
    conn.commit()
    return cursor.lastrowid


def _get_next_season_number() -> int:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM seasons")
    return (cursor.fetchone()[0] or 0) + 1


def check_and_end_season():
    """يفحص إذا انتهى الموسم ويُنهيه"""
    season = get_active_season()
    if not season:
        _ensure_active_season()
        return

    if int(time.time()) >= season["ends_at"]:
        _end_season(season["id"])
        _ensure_active_season()


def _ensure_active_season():
    """يتأكد من وجود موسم نشط، ينشئ واحداً إذا لم يكن"""
    if not get_active_season():
        create_season()


def _end_season(season_id: int):
    """يُنهي الموسم ويوزع المكافآت"""
    conn = get_db_conn()
    cursor = conn.cursor()

    # حفظ الترتيب قبل الإعادة
    _save_season_rankings(season_id, cursor)

    # توزيع المكافآت
    _distribute_season_rewards(season_id, cursor)

    # تحديث حالة الموسم
    cursor.execute("UPDATE seasons SET status = 'ended', rewards_distributed = 1 WHERE id = ?",
                   (season_id,))
    conn.commit()

    # إشعار اللاعبين
    _notify_season_end(season_id)


def _save_season_rankings(season_id: int, cursor):
    """يحفظ ترتيب الموسم في سجل التاريخ"""
    # توب الدول بالانتصارات
    cursor.execute("""
        SELECT c.owner_id, c.id as country_id,
               COUNT(*) as wins
        FROM country_battles cb
        JOIN countries c ON cb.winner_country_id = c.id
        WHERE cb.status = 'finished'
        GROUP BY c.id ORDER BY wins DESC LIMIT 10
    """)
    for rank, row in enumerate(cursor.fetchall(), 1):
        cursor.execute("""
            INSERT INTO season_history
            (season_id, category, rank, user_id, country_id, score)
            VALUES (?, 'battles', ?, ?, ?, ?)
        """, (season_id, rank, row[0], row[1], row[2]))

    # توب التحالفات بالقوة
    cursor.execute("""
        SELECT id, leader_id, power FROM alliances ORDER BY power DESC LIMIT 10
    """)
    for rank, row in enumerate(cursor.fetchall(), 1):
        cursor.execute("""
            INSERT INTO season_history
            (season_id, category, rank, user_id, alliance_id, score)
            VALUES (?, 'alliances', ?, ?, ?, ?)
        """, (season_id, rank, row[1], row[0], row[2]))

    # توب الجواسيس
    cursor.execute("""
        SELECT c.owner_id, COUNT(*) as ops
        FROM spy_operations so
        JOIN countries c ON so.attacker_country_id = c.id
        WHERE so.result IN ('success', 'partial')
        GROUP BY c.owner_id ORDER BY ops DESC LIMIT 10
    """)
    for rank, row in enumerate(cursor.fetchall(), 1):
        cursor.execute("""
            INSERT INTO season_history
            (season_id, category, rank, user_id, score)
            VALUES (?, 'spies', ?, ?, ?)
        """, (season_id, rank, row[0], row[1]))


def _distribute_season_rewards(season_id: int, cursor):
    """يوزع مكافآت الموسم على الفائزين ويمنح الألقاب"""
    top_n = _c("season_top_rewards", 3)
    reward_map = {
        1: _c("season_reward_conis_1", f"{SEASON_CHAMPION_AWARD:,}"),
        2: _c("season_reward_conis_2", f"{WARRIOR_OF_SEASON_AWARD:,}"),
        3: _c("season_reward_conis_3", f"{KNIGHT_OF_SEASON_AWARD:,}"),
    }
    title_map = {
        ("battles", 1): "👑 بطل الموسم",
        ("battles", 2): "🥈 محارب الموسم",
        ("battles", 3): "🥉 فارس الموسم",
        ("alliances", 1): "🏰 قائد التحالفات",
        ("spies", 1):    "🕵️ سيد الجواسيس",
    }

    for category in ("battles", "alliances", "spies"):
        cursor.execute("""
            SELECT user_id, rank FROM season_history
            WHERE season_id = ? AND category = ? AND rank <= ?
        """, (season_id, category, top_n))

        for row in cursor.fetchall():
            uid, rank = row[0], row[1]
            if not uid:
                continue

            # مكافأة belo (للمعارك فقط)
            if category == "battles":
                reward = reward_map.get(rank, 0)
                if reward > 0:
                    try:
                        from database.db_queries.bank_queries import update_bank_balance
                        update_bank_balance(uid, reward)
                        cursor.execute("""
                            UPDATE season_history SET reward_given = ?
                            WHERE season_id = ? AND user_id = ? AND category = ?
                        """, (f"{reward} {CURRENCY_ARABIC_NAME}", season_id, uid, category))
                    except Exception:
                        pass

            # منح اللقب
            title = title_map.get((category, rank))
            if title:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO season_titles
                        (user_id, season_id, title, category, rank)
                        VALUES (?, ?, ?, ?, ?)
                    """, (uid, season_id, title, category, rank))
                    cursor.execute("""
                        UPDATE season_history SET title_awarded = ?
                        WHERE season_id = ? AND user_id = ? AND category = ?
                    """, (title, season_id, uid, category))
                    # إشعار اللقب
                    _notify_title(uid, title, season_id)
                except Exception:
                    pass


def _notify_season_end(season_id: int):
    """يُرسل إشعار نهاية الموسم لمجموعة المطورين."""
    try:
        from core.dev_notifier import send_to_dev_group

        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM seasons WHERE id = ?", (season_id,))
        row = cursor.fetchone()
        season_name = row[0] if row else f"#{season_id}"

        cursor.execute("""
            SELECT sh.rank, sh.user_id, sh.score
            FROM season_history sh
            WHERE sh.season_id = ? AND sh.category = 'battles' AND sh.rank <= 3
            ORDER BY sh.rank
        """, (season_id,))
        winners = cursor.fetchall()

        medals = ["🥇", "🥈", "🥉"]
        text = f"🏆 <b>انتهى {season_name}!</b>\n\n🎖 الفائزون:\n"
        for row in winners:
            rank, uid, score = row[0], row[1], row[2]
            text += f"{medals[rank-1]} ID:{uid} — {score:.0f} انتصار\n"

        send_to_dev_group(text)
    except Exception:
        pass


def get_season_history(limit: int = 5) -> list:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM seasons ORDER BY started_at DESC LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


def get_season_leaderboard(season_id: int, category: str = "battles") -> list:
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            sh.*, 
            COALESCE(NULLIF(u.name, ''), 'مجهول') AS user_name
        FROM season_history sh
        LEFT JOIN users u ON sh.user_id = u.user_id
        WHERE sh.season_id = ? AND sh.category = ?
        ORDER BY sh.rank ASC 
        LIMIT 10
    """, (season_id, category))

    return [dict(r) for r in cursor.fetchall()]

def _notify_title(user_id: int, title: str, season_id: int):
    try:
        from core.bot import bot
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM seasons WHERE id = ?", (season_id,))
        row = cursor.fetchone()
        season_name = row[0] if row else f"#{season_id}"
        bot.send_message(
            user_id,
            f"🏆 <b>حصلت على لقب موسمي!</b>\n\n"
            f"{title}\n"
            f"من موسم: {season_name}\n\n"
            f"يظهر لقبك في ملفك الشخصي!",
            parse_mode="HTML"
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# 🎖 ألقاب المستخدم
# ══════════════════════════════════════════

def get_user_titles(user_id: int) -> list:
    """يرجع كل ألقاب المستخدم الموسمية"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT st.*, s.name AS season_name
        FROM season_titles st
        JOIN seasons s ON st.season_id = s.id
        WHERE st.user_id = ?
        ORDER BY st.awarded_at DESC
    """, (user_id,))
    return [dict(r) for r in cursor.fetchall()]


def get_latest_title(user_id: int) -> str | None:
    """يرجع أحدث لقب للمستخدم"""
    titles = get_user_titles(user_id)
    return titles[0]["title"] if titles else None


def get_season_status() -> dict:
    """يرجع حالة الموسم الحالي"""
    season = get_active_season()
    if not season:
        return {"active": False}
    now       = int(time.time())
    remaining = max(0, season["ends_at"] - now)
    days      = remaining // 86400
    hours     = (remaining % 86400) // 3600
    return {
        "active":     True,
        "name":       season["name"],
        "days_left":  days,
        "hours_left": hours,
        "remaining":  remaining,   # ثواني كاملة للاستخدام مع format_remaining_time
        "ends_at":    season["ends_at"],
    }
