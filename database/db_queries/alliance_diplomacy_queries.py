# diplomacy queries

"""
استعلامات نظام الدبلوماسية الاستراتيجية
Alliance Diplomacy — DB Queries
"""
import json
import time
from ..connection import get_db_conn

# ── ثوابت ──
TREATY_BETRAYAL_REP_PENALTY = -60   # خصم سمعة عند خيانة معاهدة
INFLUENCE_DECAY_RATE         = 2.0  # نقاط تتناقص يومياً
MAX_INFLUENCE                = 100.0
LARGE_ALLIANCE_THRESHOLD     = 7    # عدد أعضاء يُفعّل عقوبة التناقص
INSTABILITY_THRESHOLD        = 9    # عدد أعضاء يُفعّل عقوبة عدم الاستقرار


# ══════════════════════════════════════════
# 🤝 المعاهدات
# ══════════════════════════════════════════

def propose_treaty(alliance_a: int, alliance_b: int, treaty_type: str,
                   proposed_by: int, duration_days: int = 30,
                   terms: dict = None) -> tuple[bool, str, int]:
    """
    يُنشئ اقتراح معاهدة. يُعيد (success, msg, treaty_id).
    treaty_type: 'non_aggression' | 'military_alliance' | 'trade' | 'protectorate'
    """
    if alliance_a == alliance_b:
        return False, "❌ لا يمكن عقد معاهدة مع نفسك.", 0

    # فحص معاهدة نشطة من نفس النوع
    existing = get_active_treaty(alliance_a, alliance_b, treaty_type)
    if existing:
        return False, "❌ توجد معاهدة نشطة من هذا النوع بالفعل.", 0

    # فحص اقتراح معلق
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM alliance_treaties
        WHERE ((alliance_a=? AND alliance_b=?) OR (alliance_a=? AND alliance_b=?))
          AND treaty_type=? AND status='pending'
    """, (alliance_a, alliance_b, alliance_b, alliance_a, treaty_type))
    if cursor.fetchone():
        return False, "❌ يوجد اقتراح معلق لهذه المعاهدة.", 0

    cursor.execute("""
        INSERT INTO alliance_treaties
        (alliance_a, alliance_b, treaty_type, status, proposed_by, duration_days, terms)
        VALUES (?,?,?,'pending',?,?,?)
    """, (alliance_a, alliance_b, treaty_type, proposed_by, duration_days,
          json.dumps(terms or {}, ensure_ascii=False)))
    treaty_id = cursor.lastrowid
    conn.commit()
    _log_treaty(treaty_id, "proposed", alliance_a)
    return True, "✅ تم إرسال اقتراح المعاهدة.", treaty_id


def accept_treaty(treaty_id: int, accepted_by: int) -> tuple[bool, str]:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alliance_treaties WHERE id=? AND status='pending'", (treaty_id,))
    row = cursor.fetchone()
    if not row:
        return False, "❌ الاقتراح غير موجود أو انتهى."
    row = dict(row)
    now = int(time.time())
    expires = now + row["duration_days"] * 86400 if row["duration_days"] > 0 else None
    cursor.execute("""
        UPDATE alliance_treaties
        SET status='active', accepted_by=?, starts_at=?, expires_at=?
        WHERE id=?
    """, (accepted_by, now, expires, treaty_id))
    conn.commit()
    _log_treaty(treaty_id, "accepted", row["alliance_b"])
    return True, "✅ تم قبول المعاهدة وأصبحت سارية."


def reject_treaty(treaty_id: int, rejected_by_alliance: int) -> tuple[bool, str]:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE alliance_treaties SET status='rejected' WHERE id=? AND status='pending'
    """, (treaty_id,))
    conn.commit()
    _log_treaty(treaty_id, "rejected", rejected_by_alliance)
    return True, "❌ تم رفض المعاهدة."


def break_treaty(treaty_id: int, breaking_alliance: int) -> tuple[bool, str]:
    """يكسر معاهدة نشطة مع عقوبة سمعة."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alliance_treaties WHERE id=? AND status='active'", (treaty_id,))
    row = cursor.fetchone()
    if not row:
        return False, "❌ المعاهدة غير نشطة."
    row = dict(row)
    now = int(time.time())
    cursor.execute("""
        UPDATE alliance_treaties
        SET status='broken', broken_at=?, broken_by=?
        WHERE id=?
    """, (now, breaking_alliance, treaty_id))
    conn.commit()
    _log_treaty(treaty_id, "broken", breaking_alliance, "خيانة معاهدة")

    # عقوبة السمعة
    from database.db_queries.alliance_governance_queries import update_alliance_reputation
    update_alliance_reputation(breaking_alliance, "betrayal", f"كسر معاهدة #{treaty_id}")
    return True, f"⚠️ تم كسر المعاهدة. خُصمت نقاط سمعة من تحالفك."


def get_active_treaty(alliance_a: int, alliance_b: int,
                      treaty_type: str = None) -> dict | None:
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    if treaty_type:
        cursor.execute("""
            SELECT * FROM alliance_treaties
            WHERE ((alliance_a=? AND alliance_b=?) OR (alliance_a=? AND alliance_b=?))
              AND treaty_type=? AND status='active'
              AND (expires_at IS NULL OR expires_at > ?)
        """, (alliance_a, alliance_b, alliance_b, alliance_a, treaty_type, now))
    else:
        cursor.execute("""
            SELECT * FROM alliance_treaties
            WHERE ((alliance_a=? AND alliance_b=?) OR (alliance_a=? AND alliance_b=?))
              AND status='active' AND (expires_at IS NULL OR expires_at > ?)
        """, (alliance_a, alliance_b, alliance_b, alliance_a, now))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_alliance_treaties(alliance_id: int, status: str = None) -> list[dict]:
    conn = get_db_conn()
    cursor = conn.cursor()
    if status:
        cursor.execute("""
            SELECT at.*, a1.name as name_a, a2.name as name_b
            FROM alliance_treaties at
            JOIN alliances a1 ON at.alliance_a = a1.id
            JOIN alliances a2 ON at.alliance_b = a2.id
            WHERE (at.alliance_a=? OR at.alliance_b=?) AND at.status=?
            ORDER BY at.created_at DESC
        """, (alliance_id, alliance_id, status))
    else:
        cursor.execute("""
            SELECT at.*, a1.name as name_a, a2.name as name_b
            FROM alliance_treaties at
            JOIN alliances a1 ON at.alliance_a = a1.id
            JOIN alliances a2 ON at.alliance_b = a2.id
            WHERE (at.alliance_a=? OR at.alliance_b=?)
            ORDER BY at.created_at DESC LIMIT 30
        """, (alliance_id, alliance_id))
    return [dict(r) for r in cursor.fetchall()]


def get_pending_treaties_for_alliance(alliance_id: int) -> list[dict]:
    """المعاهدات المعلقة التي تنتظر رد هذا التحالف."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT at.*, a1.name as name_a, a2.name as name_b
        FROM alliance_treaties at
        JOIN alliances a1 ON at.alliance_a = a1.id
        JOIN alliances a2 ON at.alliance_b = a2.id
        WHERE at.alliance_b=? AND at.status='pending'
        ORDER BY at.created_at DESC
    """, (alliance_id,))
    return [dict(r) for r in cursor.fetchall()]


def expire_old_treaties():
    """يُنهي المعاهدات المنتهية الصلاحية. يُستدعى من المجدول."""
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        UPDATE alliance_treaties SET status='expired'
        WHERE status='active' AND expires_at IS NOT NULL AND expires_at <= ?
    """, (now,))
    conn.commit()


def has_non_aggression(alliance_a: int, alliance_b: int) -> bool:
    return get_active_treaty(alliance_a, alliance_b, "non_aggression") is not None


def has_military_alliance(alliance_a: int, alliance_b: int) -> bool:
    return get_active_treaty(alliance_a, alliance_b, "military_alliance") is not None


def _log_treaty(treaty_id: int, event_type: str, actor_id: int, note: str = ""):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alliance_treaty_log (treaty_id, event_type, actor_id, note)
        VALUES (?,?,?,?)
    """, (treaty_id, event_type, actor_id, note))
    conn.commit()


# ══════════════════════════════════════════
# 🧭 النفوذ والقوة الناعمة
# ══════════════════════════════════════════

def get_influence(source: int, target: int) -> float:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT influence_pts FROM alliance_influence
        WHERE source_alliance=? AND target_alliance=?
    """, (source, target))
    row = cursor.fetchone()
    return float(row[0]) if row else 0.0


def add_influence(source: int, target: int, delta: float):
    """يُضيف نقاط نفوذ (أو يُنقص إذا سالب)."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alliance_influence (source_alliance, target_alliance, influence_pts, last_updated)
        VALUES (?,?, MAX(0, MIN(?, ?)), ?)
        ON CONFLICT(source_alliance, target_alliance) DO UPDATE SET
            influence_pts = MAX(0, MIN(?, influence_pts + ?)),
            last_updated  = excluded.last_updated
    """, (source, target, MAX_INFLUENCE, max(0.0, delta), int(time.time()),
          MAX_INFLUENCE, delta))
    conn.commit()


def apply_diplomatic_pressure(source: int, target: int) -> tuple[bool, str]:
    """يُفعّل الضغط الدبلوماسي إذا كان النفوذ كافياً (≥ 40)."""
    pts = get_influence(source, target)
    if pts < 40:
        return False, f"❌ نفوذك غير كافٍ ({pts:.0f}/40 مطلوب)."
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE alliance_influence SET pressure_active=1
        WHERE source_alliance=? AND target_alliance=?
    """, (source, target))
    conn.commit()
    return True, "✅ تم تفعيل الضغط الدبلوماسي."


def get_influence_bonus_on_vote(alliance_id: int, war_id: int) -> float:
    """
    يُعيد مضاعف إضافي لوزن التصويت بناءً على النفوذ المُمارَس على التحالفات الأخرى.
    كل 10 نقاط نفوذ نشطة = +0.05 على وزن التصويت.
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COALESCE(SUM(influence_pts), 0)
        FROM alliance_influence
        WHERE source_alliance=? AND pressure_active=1
    """, (alliance_id,))
    row = cursor.fetchone()
    total_pressure = float(row[0]) if row else 0.0
    return round(total_pressure / 10.0 * 0.05, 3)


def decay_influence():
    """يُطبّق تناقص يومي على نقاط النفوذ."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE alliance_influence
        SET influence_pts = MAX(0, influence_pts - ?),
            pressure_active = CASE WHEN influence_pts - ? < 40 THEN 0 ELSE pressure_active END,
            last_updated = ?
    """, (INFLUENCE_DECAY_RATE, INFLUENCE_DECAY_RATE, int(time.time())))
    conn.commit()


# ══════════════════════════════════════════
# 🌍 التوسع — استيعاب / اندماج / اتحاد
# ══════════════════════════════════════════

def propose_expansion(initiator_id: int, target_id: int,
                      expansion_type: str, proposed_by: int,
                      terms: dict = None) -> tuple[bool, str, int]:
    """
    يُنشئ اقتراح توسع.
    expansion_type: 'absorb' | 'merge' | 'federate'
    """
    if initiator_id == target_id:
        return False, "❌ لا يمكن التوسع نحو نفسك.", 0

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM alliance_expansion
        WHERE initiator_id=? AND target_id=? AND status='pending'
    """, (initiator_id, target_id))
    if cursor.fetchone():
        return False, "❌ يوجد اقتراح توسع معلق بالفعل.", 0

    cursor.execute("""
        INSERT INTO alliance_expansion
        (initiator_id, target_id, expansion_type, status, proposed_by, terms)
        VALUES (?,?,?,'pending',?,?)
    """, (initiator_id, target_id, expansion_type, proposed_by,
          json.dumps(terms or {}, ensure_ascii=False)))
    exp_id = cursor.lastrowid
    conn.commit()
    return True, "✅ تم إرسال اقتراح التوسع.", exp_id


def accept_expansion(exp_id: int, accepted_by_user: int) -> tuple[bool, str]:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alliance_expansion WHERE id=? AND status='pending'", (exp_id,))
    row = cursor.fetchone()
    if not row:
        return False, "❌ الاقتراح غير موجود."
    row = dict(row)
    now = int(time.time())
    cursor.execute("""
        UPDATE alliance_expansion SET status='accepted', resolved_at=? WHERE id=?
    """, (now, exp_id))
    conn.commit()
    return True, row["expansion_type"]   # caller handles the actual merge/absorb


def reject_expansion(exp_id: int) -> tuple[bool, str]:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE alliance_expansion SET status='rejected', resolved_at=?
        WHERE id=? AND status='pending'
    """, (int(time.time()), exp_id))
    conn.commit()
    return True, "❌ تم رفض اقتراح التوسع."


def get_pending_expansion_for_alliance(alliance_id: int) -> list[dict]:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ae.*, a1.name as initiator_name, a2.name as target_name
        FROM alliance_expansion ae
        JOIN alliances a1 ON ae.initiator_id = a1.id
        JOIN alliances a2 ON ae.target_id    = a2.id
        WHERE ae.target_id=? AND ae.status='pending'
    """, (alliance_id,))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# 🌐 الاتحادات
# ══════════════════════════════════════════

def create_federation(name: str, leader_alliance_id: int,
                      member_ids: list[int]) -> tuple[bool, str, int]:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM alliance_federation WHERE name=? AND dissolved_at IS NULL",
                   (name,))
    if cursor.fetchone():
        return False, "❌ اسم الاتحاد مستخدم.", 0
    cursor.execute("""
        INSERT INTO alliance_federation (name, leader_id) VALUES (?,?)
    """, (name, leader_alliance_id))
    fed_id = cursor.lastrowid
    all_members = list({leader_alliance_id} | set(member_ids))
    cursor.executemany("""
        INSERT OR IGNORE INTO alliance_federation_members (federation_id, alliance_id)
        VALUES (?,?)
    """, [(fed_id, mid) for mid in all_members])
    conn.commit()
    return True, f"✅ تم تأسيس اتحاد '{name}'.", fed_id


def get_federation_by_alliance(alliance_id: int) -> dict | None:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT af.* FROM alliance_federation af
        JOIN alliance_federation_members afm ON af.id = afm.federation_id
        WHERE afm.alliance_id=? AND af.dissolved_at IS NULL
    """, (alliance_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_federation_members(federation_id: int) -> list[dict]:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.name, a.power FROM alliances a
        JOIN alliance_federation_members afm ON a.id = afm.alliance_id
        WHERE afm.federation_id=?
    """, (federation_id,))
    return [dict(r) for r in cursor.fetchall()]


def get_all_active_federations() -> list[dict]:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT af.*, a.name as leader_name,
               (SELECT COUNT(*) FROM alliance_federation_members WHERE federation_id=af.id) as member_count
        FROM alliance_federation af
        JOIN alliances a ON af.leader_id = a.id
        WHERE af.dissolved_at IS NULL
        ORDER BY af.created_at DESC
    """)
    return [dict(r) for r in cursor.fetchall()]


def dissolve_federation(federation_id: int) -> bool:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE alliance_federation SET dissolved_at=? WHERE id=?
    """, (int(time.time()), federation_id))
    conn.commit()
    return cursor.rowcount > 0


# ══════════════════════════════════════════
# 🧠 الاستخبارات
# ══════════════════════════════════════════

def compute_intelligence(alliance_id: int) -> dict:
    """
    يحسب ويُخزّن بيانات الاستخبارات لتحالف.
    يُعيد dict بالنتائج.
    """
    conn = get_db_conn()
    cursor = conn.cursor()

    # نشاط: عدد الحروب السياسية خلال 30 يوماً
    month_ago = int(time.time()) - 30 * 86400
    cursor.execute("""
        SELECT COUNT(*) FROM political_war_members pwm
        JOIN alliance_members am ON pwm.country_id = am.country_id
        WHERE am.alliance_id=? AND pwm.joined_at > ?
    """, (alliance_id, month_ago))
    war_count = cursor.fetchone()[0] or 0
    activity = min(100.0, war_count * 20.0)

    # جاهزية الحرب: قوة التحالف مقارنة بالمتوسط
    cursor.execute("SELECT AVG(power) FROM alliances WHERE power > 0")
    avg_power = cursor.fetchone()[0] or 1.0
    cursor.execute("SELECT power FROM alliances WHERE id=?", (alliance_id,))
    my_power = (cursor.fetchone() or [0.0])[0] or 0.0
    war_readiness = min(100.0, (my_power / avg_power) * 50.0)

    # الاستقرار الاقتصادي: رصيد الخزينة
    cursor.execute("""
        SELECT COALESCE(balance, 0) FROM alliance_treasury WHERE alliance_id=?
    """, (alliance_id,))
    balance = (cursor.fetchone() or [0.0])[0] or 0.0
    economic_stability = min(100.0, balance / 1000.0 * 10.0)

    # مستوى التهديد: مركّب
    threat = round((war_readiness * 0.5 + activity * 0.3 + economic_stability * 0.2), 1)

    cursor.execute("""
        INSERT INTO alliance_intelligence
        (alliance_id, activity_score, war_readiness, economic_stability, threat_level, last_computed)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(alliance_id) DO UPDATE SET
            activity_score=excluded.activity_score,
            war_readiness=excluded.war_readiness,
            economic_stability=excluded.economic_stability,
            threat_level=excluded.threat_level,
            last_computed=excluded.last_computed
    """, (alliance_id, activity, war_readiness, economic_stability, threat, int(time.time())))
    conn.commit()
    return {
        "activity_score": activity,
        "war_readiness": war_readiness,
        "economic_stability": economic_stability,
        "threat_level": threat,
    }


def get_intelligence(alliance_id: int) -> dict:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alliance_intelligence WHERE alliance_id=?", (alliance_id,))
    row = cursor.fetchone()
    return dict(row) if row else {}


def get_all_intelligence_ranked() -> list[dict]:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ai.*, a.name FROM alliance_intelligence ai
        JOIN alliances a ON ai.alliance_id = a.id
        ORDER BY ai.threat_level DESC
    """)
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# ⚖️ قواعد التوازن
# ══════════════════════════════════════════

def apply_balance_rules(alliance_id: int) -> list[str]:
    """
    يُطبّق قواعد التوازن ويُعيد قائمة بالعقوبات المُطبَّقة.
    يُستدعى يومياً من المجدول.
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    penalties = []

    cursor.execute("SELECT COUNT(*) FROM alliance_members WHERE alliance_id=?", (alliance_id,))
    member_count = cursor.fetchone()[0]

    # 1. تناقص العوائد للتحالفات الكبيرة
    if member_count >= LARGE_ALLIANCE_THRESHOLD:
        excess = member_count - LARGE_ALLIANCE_THRESHOLD + 1
        power_penalty = excess * 0.02   # -2% لكل عضو زائد
        cursor.execute("""
            UPDATE alliances SET power = power * ? WHERE id=?
        """, (1.0 - power_penalty, alliance_id))
        _log_balance(alliance_id, "diminishing_returns",
                     power_penalty, f"تحالف كبير ({member_count} أعضاء)")
        penalties.append(f"📉 تناقص العوائد: -{power_penalty*100:.0f}% قوة")

    # 2. عدم الاستقرار الداخلي
    if member_count >= INSTABILITY_THRESHOLD:
        from database.db_queries.alliance_governance_queries import update_alliance_reputation
        update_alliance_reputation(alliance_id, "inactive",
                                   f"عدم استقرار داخلي ({member_count} أعضاء)")
        _log_balance(alliance_id, "internal_instability", 0,
                     f"عدد الأعضاء {member_count} تجاوز الحد")
        penalties.append(f"⚠️ عدم استقرار داخلي: -سمعة")

    # 3. سلسلة الخيانات — عقوبة مضاعفة
    cursor.execute("""
        SELECT COUNT(*) FROM alliance_treaty_log atl
        JOIN alliance_treaties at ON atl.treaty_id = at.id
        WHERE atl.event_type='broken' AND atl.actor_id=?
          AND atl.created_at > ?
    """, (alliance_id, int(time.time()) - 30 * 86400))
    recent_betrayals = cursor.fetchone()[0]
    if recent_betrayals >= 2:
        from database.db_queries.alliance_governance_queries import update_alliance_reputation
        update_alliance_reputation(alliance_id, "betrayal",
                                   f"سلسلة خيانات ({recent_betrayals} خلال 30 يوماً)")
        _log_balance(alliance_id, "betrayal_chain", 0,
                     f"{recent_betrayals} خيانات خلال 30 يوماً")
        penalties.append(f"🐍 سلسلة خيانات: -سمعة مضاعفة")

    conn.commit()
    return penalties


def _log_balance(alliance_id: int, rule_type: str, penalty: float, note: str):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alliance_balance_log (alliance_id, rule_type, penalty, note)
        VALUES (?,?,?,?)
    """, (alliance_id, rule_type, penalty, note))
    conn.commit()


def get_balance_log(alliance_id: int, limit: int = 10) -> list[dict]:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM alliance_balance_log WHERE alliance_id=?
        ORDER BY created_at DESC LIMIT ?
    """, (alliance_id, limit))
    return [dict(r) for r in cursor.fetchall()]
