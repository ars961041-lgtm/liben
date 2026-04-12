# political war queries

"""
استعلامات نظام الحرب السياسية — نسخة محسّنة
Political War System — DB Queries (Production-Level)
"""
import json
import time
from ..connection import get_db_conn

VOTING_WINDOW              = 24 * 60 * 60   # 24 ساعة للتصويت
PREPARATION_WINDOW         = 20 * 60        # 20 دقيقة للتحضير
VOTE_THRESHOLD             = 0.60           # 60% من الأوزان يجب أن تدعم
WAR_COOLDOWN_SEC           = 12 * 60 * 60   # 12 ساعة بين إعلانات الحرب
WITHDRAWAL_REP_PENALTY     = 15
DEFENSIVE_IGNORE_PENALTY   = 20             # عقوبة تجاهل الحرب الدفاعية
LOYALTY_SUPPORT_BONUS      = 10.0
LOYALTY_IGNORE_PENALTY     = -15.0
LOYALTY_WITHDRAW_PENALTY   = -20.0
LOYALTY_WIN_BONUS          = 5.0


# ══════════════════════════════════════════
# 📣 إعلان الحرب
# ══════════════════════════════════════════

def declare_political_war(
    declared_by_user_id: int,
    war_type: str,
    declaration_type: str,
    attacker_country_id=None,
    attacker_alliance_id=None,
    defender_country_id=None,
    defender_alliance_id=None,
    reason: str = "",
    war_cost: float = 0,
) -> int:
    """
    يُنشئ إعلان حرب جديد.
    BEGIN IMMEDIATE يمنع إنشاء حربين متطابقتين في نفس اللحظة.
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        voting_ends = int(time.time()) + VOTING_WINDOW
        cursor.execute("""
            INSERT INTO political_wars
            (war_type, declaration_type,
             attacker_country_id, attacker_alliance_id,
             defender_country_id, defender_alliance_id,
             reason, status, voting_ends_at, vote_threshold, war_cost, declared_by_user_id)
            VALUES (?,?,?,?,?,?,?,'voting',?,?,?,?)
        """, (war_type, declaration_type,
              attacker_country_id, attacker_alliance_id,
              defender_country_id, defender_alliance_id,
              reason, voting_ends, VOTE_THRESHOLD, war_cost, declared_by_user_id))
        war_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO political_war_log
            (war_id, country_id, user_id, event_type, event_data)
            VALUES (?,?,?,?,?)
        """, (war_id, attacker_country_id, declared_by_user_id, "declared",
              json.dumps({"war_type": war_type,
                          "declaration_type": declaration_type,
                          "reason": reason}, ensure_ascii=False)))

        conn.commit()
        return war_id
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise


# ══════════════════════════════════════════
# ⏱️ كولداون الحرب
# ══════════════════════════════════════════

def check_war_cooldown(alliance_id: int) -> tuple[bool, int]:
    """يُعيد (can_declare, remaining_seconds)."""
    if not alliance_id:
        return True, 0
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT last_declared, cooldown_sec FROM war_cooldowns WHERE alliance_id=?",
                   (alliance_id,))
    row = cursor.fetchone()
    if not row:
        return True, 0
    elapsed = int(time.time()) - row[0]
    if elapsed >= row[1]:
        return True, 0
    return False, row[1] - elapsed


def set_war_cooldown(alliance_id: int):
    if not alliance_id:
        return
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO war_cooldowns (alliance_id, last_declared, cooldown_sec)
        VALUES (?,?,?)
        ON CONFLICT(alliance_id) DO UPDATE SET last_declared=excluded.last_declared
    """, (alliance_id, int(time.time()), WAR_COOLDOWN_SEC))
    conn.commit()


# ══════════════════════════════════════════
# 🗳️ التصويت
# ══════════════════════════════════════════

def cast_war_vote(
    war_id: int,
    voter_country_id: int,
    voter_user_id: int,
    alliance_id: int,
    vote: str,
    military_power: float,
    economy_score: float,
    alliance_rank: int,
) -> tuple[bool, str]:
    """
    يُسجّل تصويت دولة بشكل آمن تماماً من التزامن.

    يستخدم BEGIN IMMEDIATE لاكتساب قفل كتابة فوري على قاعدة البيانات
    قبل قراءة حالة الحرب، مما يضمن:
    - لا يمكن لدولتين التصويت في نفس اللحظة بشكل متعارض
    - حالة الحرب لا تتغير بين القراءة والكتابة
    - وزن التصويت يُحسب ويُكتب في نفس المعاملة
    - التصويت بعد انتهاء الموعد مرفوض بشكل قاطع

    يُعيد (success: bool, reason: str)
    reason: 'ok' | 'expired' | 'wrong_status' | 'locked' | 'change_limit' | 'error'
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")

        # قراءة حالة الحرب داخل القفل — لا يمكن لأي thread آخر تغييرها الآن
        cursor.execute(
            "SELECT status, voting_ends_at, vote_threshold FROM political_wars WHERE id=?",
            (war_id,)
        )
        row = cursor.fetchone()
        if not row:
            conn.rollback()
            return False, "wrong_status"

        # فحص الحالة أولاً
        if row["status"] != "voting":
            conn.rollback()
            return False, "wrong_status"

        # فحص الموعد النهائي — الفحص الحاسم داخل القفل
        now = int(time.time())
        if now > row["voting_ends_at"]:
            conn.rollback()
            return False, "expired"

        # حساب الوزن الخام
        weight = round(
            (military_power / 1000.0) + (economy_score / 5000.0) + alliance_rank,
            2
        )
        weight = max(1.0, weight)

        # تأثير الولاء — قراءة داخل نفس المعاملة
        cursor.execute(
            "SELECT loyalty_score FROM alliance_loyalty WHERE alliance_id=? AND country_id=?",
            (alliance_id, voter_country_id)
        )
        loyalty_row = cursor.fetchone()
        loyalty = float(loyalty_row[0]) if loyalty_row else 50.0
        loyalty_mult = 0.7 + (loyalty / 100.0) * 0.6   # 0.7x–1.3x
        weight = round(weight * loyalty_mult, 2)

        # كتابة التصويت — UPSERT آمن مع تتبع عدد التغييرات
        # قواعد تغيير التصويت:
        #   - إذا لم يصوّت بعد: مسموح دائماً (vote_change_count يبقى 0)
        #   - إذا صوّت مسبقاً: يُعدّ تغييراً، حد أقصى 2 تغيير
        #   - مقفل في آخر 60 ثانية قبل انتهاء التصويت
        VOTE_CHANGE_LIMIT  = 2
        LOCK_BEFORE_END_SEC = 60

        cursor.execute(
            "SELECT vote, vote_change_count FROM political_war_votes "
            "WHERE war_id=? AND voter_country_id=?",
            (war_id, voter_country_id)
        )
        existing = cursor.fetchone()

        if existing:
            # هذا تغيير — تحقق من القيود
            change_count = int(existing["vote_change_count"] or 0)

            # قفل آخر 60 ثانية
            time_left = row["voting_ends_at"] - now
            if time_left <= LOCK_BEFORE_END_SEC:
                conn.rollback()
                return False, "locked"

            # حد أقصى 2 تغيير
            if change_count >= VOTE_CHANGE_LIMIT:
                conn.rollback()
                return False, "change_limit"

            cursor.execute("""
                UPDATE political_war_votes
                SET vote             = ?,
                    vote_weight      = ?,
                    military_power   = ?,
                    economy_score    = ?,
                    alliance_rank    = ?,
                    vote_change_count = vote_change_count + 1,
                    voted_at         = ?
                WHERE war_id=? AND voter_country_id=?
            """, (vote, weight, military_power, economy_score, alliance_rank,
                  now, war_id, voter_country_id))
        else:
            # تصويت أول — لا قيود
            cursor.execute("""
                INSERT INTO political_war_votes
                (war_id, voter_country_id, voter_user_id, alliance_id,
                 vote, vote_weight, military_power, economy_score, alliance_rank,
                 vote_change_count, voted_at)
                VALUES (?,?,?,?,?,?,?,?,?,0,?)
            """, (war_id, voter_country_id, voter_user_id, alliance_id,
                  vote, weight, military_power, economy_score, alliance_rank, now))

        # تسجيل الحدث داخل نفس المعاملة
        event_map = {
            "support": "voted_support",
            "reject":  "voted_reject",
            "neutral": "voted_neutral",
        }
        cursor.execute("""
            INSERT INTO political_war_log
            (war_id, country_id, user_id, event_type, event_data)
            VALUES (?,?,?,?,?)
        """, (war_id, voter_country_id, voter_user_id,
              event_map.get(vote, "voted_neutral"),
              json.dumps({"weight": weight}, ensure_ascii=False)))

        conn.commit()
        return True, "ok"

    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise


def get_war_votes(war_id: int) -> list[dict]:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pv.*, c.name as country_name
        FROM political_war_votes pv
        JOIN countries c ON pv.voter_country_id = c.id
        WHERE pv.war_id = ?
        ORDER BY pv.vote_weight DESC
    """, (war_id,))
    return [dict(r) for r in cursor.fetchall()]


def get_vote_summary(war_id: int) -> dict:
    """
    يُعيد ملخص التصويت مع النسب المئوية والعتبة.
    يقرأ الأصوات والعتبة في استعلام واحد لضمان الاتساق.
    يُحسب فقط الأصوات المُسجَّلة قبل انتهاء الموعد النهائي.
    """
    conn = get_db_conn()
    cursor = conn.cursor()

    # استعلام واحد يجمع الأصوات والعتبة معاً.
    # pv.voted_at <= pw.voting_ends_at يضمن استبعاد أي صوت متأخر
    # حتى لو تسرّب بطريقة ما.
    cursor.execute("""
        SELECT
            pw.vote_threshold,
            pw.voting_ends_at,
            COALESCE(SUM(CASE WHEN pv.vote='support'
                              AND pv.voted_at <= pw.voting_ends_at
                         THEN pv.vote_weight ELSE 0 END), 0) AS support,
            COALESCE(SUM(CASE WHEN pv.vote='reject'
                              AND pv.voted_at <= pw.voting_ends_at
                         THEN pv.vote_weight ELSE 0 END), 0) AS reject,
            COALESCE(SUM(CASE WHEN pv.vote='neutral'
                              AND pv.voted_at <= pw.voting_ends_at
                         THEN pv.vote_weight ELSE 0 END), 0) AS neutral,
            COUNT(CASE WHEN pv.voted_at <= pw.voting_ends_at
                       THEN pv.id END) AS count
        FROM political_wars pw
        LEFT JOIN political_war_votes pv ON pv.war_id = pw.id
        WHERE pw.id = ?
        GROUP BY pw.id
    """, (war_id,))
    row = cursor.fetchone()

    if not row:
        return {
            "support": 0.0, "reject": 0.0, "neutral": 0.0,
            "total": 0.0, "count": 0,
            "support_pct": 0.0, "reject_pct": 0.0, "neutral_pct": 0.0,
            "threshold_pct": round(VOTE_THRESHOLD * 100, 0),
            "passes": False,
        }

    threshold = float(row["vote_threshold"]) if row["vote_threshold"] else VOTE_THRESHOLD
    support   = float(row["support"])
    reject    = float(row["reject"])
    neutral   = float(row["neutral"])
    total     = support + reject + neutral
    denom     = total if total > 0 else 1.0

    return {
        "support":       support,
        "reject":        reject,
        "neutral":       neutral,
        "total":         total,
        "count":         int(row["count"] or 0),
        "support_pct":   round(support  / denom * 100, 1),
        "reject_pct":    round(reject   / denom * 100, 1),
        "neutral_pct":   round(neutral  / denom * 100, 1),
        "threshold_pct": round(threshold * 100, 0),
        "passes":        (support / denom) >= threshold if total > 0 else False,
    }


def get_user_vote(war_id: int, voter_country_id: int) -> dict | None:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM political_war_votes WHERE war_id=? AND voter_country_id=?",
                   (war_id, voter_country_id))
    row = cursor.fetchone()
    return dict(row) if row else None


# ══════════════════════════════════════════
# ⚔️ إدارة الحرب — مراحل
# ══════════════════════════════════════════

def set_war_preparation(war_id: int) -> bool:
    """
    يُحوّل الحرب من 'voting' إلى 'preparation'.
    BEGIN IMMEDIATE يمنع تشغيل هذا الانتقال مرتين في نفس الوقت.
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        prep_ends = int(time.time()) + PREPARATION_WINDOW
        cursor.execute("""
            UPDATE political_wars
            SET status='preparation', preparation_ends_at=?
            WHERE id=? AND status='voting'
        """, (prep_ends, war_id))
        changed = cursor.rowcount
        if changed:
            cursor.execute("""
                INSERT INTO political_war_log
                (war_id, country_id, user_id, event_type, event_data)
                VALUES (?,NULL,NULL,'preparation_started',?)
            """, (war_id, json.dumps({"ends_at": prep_ends})))
        conn.commit()
        return bool(changed)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise


def start_political_war(war_id: int) -> bool:
    """
    يُحوّل الحرب من 'preparation' إلى 'active'.
    BEGIN IMMEDIATE يمنع بدء الحرب مرتين.
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        now = int(time.time())
        cursor.execute("""
            UPDATE political_wars
            SET status='active', started_at=?
            WHERE id=? AND status IN ('voting','preparation')
        """, (now, war_id))
        changed = cursor.rowcount
        if changed:
            cursor.execute("""
                INSERT INTO political_war_log
                (war_id, country_id, user_id, event_type, event_data)
                VALUES (?,NULL,NULL,'war_started',?)
            """, (war_id, json.dumps({"started_at": now})))
        conn.commit()
        return bool(changed)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise


def end_political_war(war_id: int, winner_side: str) -> bool:
    """
    يُنهي الحرب ويُسجّل الفائز.
    BEGIN IMMEDIATE يمنع إنهاء الحرب مرتين.
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        now = int(time.time())
        cursor.execute("""
            UPDATE political_wars
            SET status='ended', ended_at=?, winner_side=?
            WHERE id=? AND status='active'
        """, (now, winner_side, war_id))
        changed = cursor.rowcount
        if changed:
            cursor.execute("""
                INSERT INTO political_war_log
                (war_id, country_id, user_id, event_type, event_data)
                VALUES (?,NULL,NULL,'war_ended',?)
            """, (war_id, json.dumps({"winner_side": winner_side})))
        conn.commit()
        return bool(changed)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise


def cancel_political_war(war_id: int, reason: str = "") -> bool:
    """
    يُلغي الحرب.
    BEGIN IMMEDIATE يمنع إلغاء الحرب مرتين أو إلغاءها بعد انتهائها.
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("""
            UPDATE political_wars SET status='cancelled', ended_at=?
            WHERE id=? AND status IN ('voting','preparation','active')
        """, (int(time.time()), war_id))
        changed = cursor.rowcount
        if changed:
            cursor.execute("""
                INSERT INTO political_war_log
                (war_id, country_id, user_id, event_type, event_data)
                VALUES (?,NULL,NULL,'cancelled',?)
            """, (war_id, json.dumps({"reason": reason})))
        conn.commit()
        return bool(changed)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise


def get_political_war(war_id: int) -> dict | None:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM political_wars WHERE id=?", (war_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_active_political_wars() -> list[dict]:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM political_wars
        WHERE status IN ('voting','preparation','active')
        ORDER BY created_at DESC
    """)
    return [dict(r) for r in cursor.fetchall()]


def get_wars_for_country(country_id: int, limit: int = 10) -> list[dict]:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pw.* FROM political_wars pw
        WHERE pw.attacker_country_id=? OR pw.defender_country_id=?
        UNION
        SELECT pw.* FROM political_wars pw
        JOIN political_war_members pwm ON pw.id=pwm.war_id
        WHERE pwm.country_id=?
        ORDER BY created_at DESC LIMIT ?
    """, (country_id, country_id, country_id, limit))
    return [dict(r) for r in cursor.fetchall()]


def get_wars_for_alliance(alliance_id: int, limit: int = 10) -> list[dict]:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM political_wars
        WHERE attacker_alliance_id=? OR defender_alliance_id=?
        ORDER BY created_at DESC LIMIT ?
    """, (alliance_id, alliance_id, limit))
    return [dict(r) for r in cursor.fetchall()]


def get_voting_wars_expired() -> list[dict]:
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        SELECT * FROM political_wars
        WHERE status='voting' AND voting_ends_at<=?
    """, (now,))
    return [dict(r) for r in cursor.fetchall()]


def get_preparation_wars_ready() -> list[dict]:
    """حروب انتهت مرحلة التحضير وجاهزة للبدء."""
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        SELECT * FROM political_wars
        WHERE status='preparation' AND preparation_ends_at<=?
    """, (now,))
    return [dict(r) for r in cursor.fetchall()]


def recalc_preparation_power(war_id: int) -> dict:
    """
    يُعيد حساب قوى الجانبين بناءً على الأعضاء النشطين فعلاً
    (غير المنسحبين) خلال مرحلة التحضير.

    يُحدّث power_contributed لكل عضو بالقوة الحالية الفعلية،
    ثم يُعيد ملخصاً بعدد الأعضاء وإجمالي القوة لكل جانب.

    يُستدعى بعد كل انسحاب في مرحلة التحضير.
    """
    from modules.war.power_calculator import get_country_power as _get_power

    conn = get_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")

        # جلب الأعضاء النشطين
        cursor.execute("""
            SELECT country_id, user_id, side
            FROM political_war_members
            WHERE war_id=? AND withdrew=0
        """, (war_id,))
        members = cursor.fetchall()

        sides = {"attacker": {"count": 0, "power": 0.0},
                 "defender": {"count": 0, "power": 0.0}}

        for m in members:
            cid  = m["country_id"]
            side = m["side"]
            # حساب القوة الحالية الفعلية
            try:
                power = _get_power(cid)
            except Exception:
                power = 0.0

            # تحديث power_contributed بالقيمة الحالية
            cursor.execute("""
                UPDATE political_war_members
                SET power_contributed=?
                WHERE war_id=? AND country_id=?
            """, (power, war_id, cid))

            sides[side]["count"] += 1
            sides[side]["power"] += power

        conn.commit()
        return sides

    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise


# ══════════════════════════════════════════
# 👥 أعضاء الحرب
# ══════════════════════════════════════════

def add_war_member(war_id: int, country_id: int, user_id: int,
                   side: str, power: float, joined_before_start: bool = True) -> bool:
    """
    يُضيف دولة كعضو في الحرب بشكل آمن.
    BEGIN IMMEDIATE يمنع إضافة نفس الدولة مرتين في نفس الوقت.
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("""
            INSERT OR IGNORE INTO political_war_members
            (war_id, country_id, user_id, side, power_contributed, joined_before_start)
            VALUES (?,?,?,?,?,?)
        """, (war_id, country_id, user_id, side, power, 1 if joined_before_start else 0))
        changed = cursor.rowcount
        if changed:
            event = "joined_late" if not joined_before_start else "voted_support"
            cursor.execute("""
                INSERT INTO political_war_log
                (war_id, country_id, user_id, event_type, event_data)
                VALUES (?,?,?,?,?)
            """, (war_id, country_id, user_id, event,
                  json.dumps({"side": side, "power": power})))
        conn.commit()
        return bool(changed)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise


def withdraw_from_war(war_id: int, country_id: int, user_id: int) -> tuple[bool, str]:
    """
    يُسجّل انسحاب دولة من الحرب بشكل آمن.
    BEGIN IMMEDIATE يمنع انسحابين متزامنين أو انسحاباً بعد انتهاء الحرب.
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute("""
            SELECT pwm.withdrew, pwm.loyalty_delta,
                   pw.status, pw.declaration_type,
                   pw.attacker_alliance_id, pw.defender_alliance_id
            FROM political_war_members pwm
            JOIN political_wars pw ON pwm.war_id = pw.id
            WHERE pwm.war_id=? AND pwm.country_id=?
        """, (war_id, country_id))
        row = cursor.fetchone()
        if not row:
            conn.rollback()
            return False, "❌ دولتك ليست مشاركة في هذه الحرب."
        row = dict(row)
        if row["withdrew"]:
            conn.rollback()
            return False, "❌ انسحبت بالفعل من هذه الحرب."

        war_active = row["status"] == "active"
        penalty       = 0.0
        loyalty_delta = 0.0
        msg           = "✅ انسحبت من الحرب."

        if war_active:
            penalty       = WITHDRAWAL_REP_PENALTY
            loyalty_delta = LOYALTY_WITHDRAW_PENALTY
            msg = f"⚠️ انسحبت بعد بدء الحرب. خُصم {penalty} نقطة من سمعتك وولائك."
        elif row["status"] == "preparation":
            loyalty_delta = LOYALTY_WITHDRAW_PENALTY / 2
            msg = "⚠️ انسحبت خلال مرحلة التحضير."

        cursor.execute("""
            UPDATE political_war_members
            SET withdrew=1, withdrew_at=?, reputation_penalty=?, loyalty_delta=?
            WHERE war_id=? AND country_id=?
        """, (int(time.time()), penalty, loyalty_delta, war_id, country_id))

        event = "withdrew_after" if war_active else "withdrew_before"
        cursor.execute("""
            INSERT INTO political_war_log
            (war_id, country_id, user_id, event_type, event_data)
            VALUES (?,?,?,?,?)
        """, (war_id, country_id, user_id, event,
              json.dumps({"penalty": penalty})))

        conn.commit()

        # عقوبة السمعة والولاء خارج المعاملة (لا تؤثر على اتساق بيانات الحرب)
        if war_active:
            try:
                from database.db_queries.advanced_war_queries import update_reputation
                update_reputation(user_id, betrayed=1)
            except Exception:
                pass
        if loyalty_delta != 0:
            alliance_id = row["attacker_alliance_id"] or row["defender_alliance_id"]
            if alliance_id:
                update_loyalty(alliance_id, country_id, user_id, loyalty_delta)

        return True, msg

    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise


def get_war_members(war_id: int, side: str = None) -> list[dict]:
    conn = get_db_conn()
    cursor = conn.cursor()
    if side:
        cursor.execute("""
            SELECT pwm.*, c.name as country_name
            FROM political_war_members pwm
            JOIN countries c ON pwm.country_id=c.id
            WHERE pwm.war_id=? AND pwm.side=? AND pwm.withdrew=0
        """, (war_id, side))
    else:
        cursor.execute("""
            SELECT pwm.*, c.name as country_name
            FROM political_war_members pwm
            JOIN countries c ON pwm.country_id=c.id
            WHERE pwm.war_id=? AND pwm.withdrew=0
        """, (war_id,))
    return [dict(r) for r in cursor.fetchall()]


def get_total_side_power(war_id: int, side: str) -> float:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COALESCE(SUM(power_contributed),0)
        FROM political_war_members
        WHERE war_id=? AND side=? AND withdrew=0
    """, (war_id, side))
    row = cursor.fetchone()
    return float(row[0]) if row else 0.0


def is_country_in_war(country_id: int) -> bool:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM political_war_members pwm
        JOIN political_wars pw ON pwm.war_id=pw.id
        WHERE pwm.country_id=? AND pw.status IN ('voting','preparation','active')
          AND pwm.withdrew=0
        LIMIT 1
    """, (country_id,))
    return cursor.fetchone() is not None


# ══════════════════════════════════════════
# 🏅 الولاء
# ══════════════════════════════════════════

def ensure_loyalty(alliance_id: int, country_id: int, user_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO alliance_loyalty (alliance_id, country_id, user_id)
        VALUES (?,?,?)
    """, (alliance_id, country_id, user_id))
    conn.commit()


def get_loyalty_score(alliance_id: int, country_id: int) -> float:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT loyalty_score FROM alliance_loyalty
        WHERE alliance_id=? AND country_id=?
    """, (alliance_id, country_id))
    row = cursor.fetchone()
    return float(row[0]) if row else 50.0


def update_loyalty(alliance_id: int, country_id: int, user_id: int, delta: float):
    """
    يُحدّث درجة الولاء بشكل آمن.
    BEGIN IMMEDIATE يمنع تحديثين متزامنين يتسببان في قيمة خاطئة.
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")

        # ensure row exists inside the lock
        cursor.execute("""
            INSERT OR IGNORE INTO alliance_loyalty (alliance_id, country_id, user_id)
            VALUES (?,?,?)
        """, (alliance_id, country_id, user_id))

        cursor.execute("""
            UPDATE alliance_loyalty
            SET loyalty_score = MAX(0, MIN(100, loyalty_score + ?)),
                updated_at    = ?
            WHERE alliance_id=? AND country_id=?
        """, (delta, int(time.time()), alliance_id, country_id))

        # حساب اللقب داخل نفس المعاملة
        cursor.execute(
            "SELECT loyalty_score FROM alliance_loyalty WHERE alliance_id=? AND country_id=?",
            (alliance_id, country_id)
        )
        score_row = cursor.fetchone()
        if score_row:
            score = score_row[0]
            label = "🤝 وفي" if score >= 75 else ("😐 محايد" if score >= 40 else "⚠️ غير موثوق")
            cursor.execute(
                "UPDATE alliance_loyalty SET label=? WHERE alliance_id=? AND country_id=?",
                (label, alliance_id, country_id)
            )

        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise


def _recalc_loyalty_label(alliance_id: int, country_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT loyalty_score FROM alliance_loyalty WHERE alliance_id=? AND country_id=?",
                   (alliance_id, country_id))
    row = cursor.fetchone()
    if not row:
        return
    score = row[0]
    if score >= 75:
        label = "🤝 وفي"
    elif score >= 40:
        label = "😐 محايد"
    else:
        label = "⚠️ غير موثوق"
    cursor.execute("UPDATE alliance_loyalty SET label=? WHERE alliance_id=? AND country_id=?",
                   (label, alliance_id, country_id))
    conn.commit()


def get_alliance_loyalty_board(alliance_id: int) -> list[dict]:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT al.*, c.name as country_name
        FROM alliance_loyalty al
        JOIN countries c ON al.country_id=c.id
        WHERE al.alliance_id=?
        ORDER BY al.loyalty_score DESC
    """, (alliance_id,))
    return [dict(r) for r in cursor.fetchall()]


def _update_loyalty_from_war(war_id: int, country_id: int, user_id: int, delta: float):
    """يُحدّث الولاء بناءً على حدث حرب."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT attacker_alliance_id, defender_alliance_id
        FROM political_wars WHERE id=?
    """, (war_id,))
    row = cursor.fetchone()
    if not row:
        return
    alliance_id = row[0] or row[1]
    if alliance_id:
        update_loyalty(alliance_id, country_id, user_id, delta)


# ══════════════════════════════════════════
# 📋 السجل
# ══════════════════════════════════════════

def get_war_log(war_id: int, limit: int = 50) -> list[dict]:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pl.*, c.name as country_name
        FROM political_war_log pl
        LEFT JOIN countries c ON pl.country_id=c.id
        WHERE pl.war_id=?
        ORDER BY pl.created_at DESC LIMIT ?
    """, (war_id, limit))
    return [dict(r) for r in cursor.fetchall()]


def get_user_war_stats(user_id: int) -> dict:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            COUNT(CASE WHEN event_type='voted_support'  THEN 1 END) as supported,
            COUNT(CASE WHEN event_type='voted_reject'   THEN 1 END) as rejected,
            COUNT(CASE WHEN event_type='voted_neutral'  THEN 1 END) as neutral,
            COUNT(CASE WHEN event_type='withdrew_after' THEN 1 END) as withdrew_after,
            COUNT(CASE WHEN event_type='withdrew_before'THEN 1 END) as withdrew_before
        FROM political_war_log WHERE user_id=?
    """, (user_id,))
    row = cursor.fetchone()
    return dict(row) if row else {}


# ══════════════════════════════════════════
# 🔧 مساعدات داخلية
# ══════════════════════════════════════════

def _log_event(war_id: int, country_id, user_id, event_type: str, data: dict):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO political_war_log (war_id, country_id, user_id, event_type, event_data)
        VALUES (?,?,?,?,?)
    """, (war_id, country_id, user_id, event_type,
          json.dumps(data, ensure_ascii=False)))
    conn.commit()
