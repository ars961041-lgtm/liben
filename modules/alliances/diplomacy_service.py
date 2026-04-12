# diplomacy service

"""
خدمة الدبلوماسية الاستراتيجية
Alliance Diplomacy Service — Business Logic

يتعامل مع:
  - التحقق من صلاحية المعاهدات
  - تنفيذ الاندماج / الاستيعاب
  - حساب النفوذ بناءً على القوة
  - التكامل مع نظام التصويت والحرب
"""
import time
from database.db_queries.alliance_diplomacy_queries import (
    propose_treaty, accept_treaty, reject_treaty, break_treaty,
    get_alliance_treaties, get_pending_treaties_for_alliance,
    has_non_aggression, has_military_alliance,
    propose_expansion, accept_expansion, reject_expansion,
    get_pending_expansion_for_alliance,
    create_federation, get_federation_by_alliance, get_federation_members,
    compute_intelligence, get_intelligence,
    apply_balance_rules, get_influence, add_influence,
    apply_diplomatic_pressure,
)
from database.db_queries.alliances_queries import (
    get_alliance_by_id, get_alliance_by_user, get_alliance_member_count,
    delete_alliance,
)
from database.db_queries.alliance_governance_queries import (
    get_treasury, _apply_treasury_change, update_alliance_reputation,
    has_permission,
)
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

TREATY_COST = 200   # تكلفة اقتراح معاهدة


# ══════════════════════════════════════════
# 🤝 المعاهدات
# ══════════════════════════════════════════

def send_treaty_proposal(user_id: int, target_alliance_id: int,
                         treaty_type: str, duration_days: int = 30) -> tuple[bool, str]:
    """يُرسل اقتراح معاهدة بعد التحقق من الصلاحيات والتكلفة."""
    alliance = get_alliance_by_user(user_id)
    if not alliance:
        return False, "❌ لا تملك تحالفاً."
    alliance = dict(alliance)
    aid = alliance["id"]

    if not has_permission(aid, user_id, "declare_war"):
        return False, "❌ لا تملك صلاحية إرسال معاهدات (مطلوب: قائد أو ضابط)."

    from database.db_queries.bank_queries import get_user_balance, deduct_user_balance
    if get_user_balance(user_id) < TREATY_COST:
        return False, f"❌ تحتاج {TREATY_COST} {CURRENCY_ARABIC_NAME} لاقتراح معاهدة."
    deduct_user_balance(user_id, TREATY_COST)

    ok, msg, treaty_id = propose_treaty(aid, target_alliance_id, treaty_type,
                                        user_id, duration_days)
    if ok:
        _notify_alliance_leader(target_alliance_id,
            f"📜 تلقّى تحالفك اقتراح معاهدة ({_treaty_ar(treaty_type)}) "
            f"من تحالف <b>{alliance['name']}</b>.\n"
            f"استخدم: دبلوماسية التحالف")
    return ok, msg


def respond_to_treaty(user_id: int, treaty_id: int, accept: bool) -> tuple[bool, str]:
    """يقبل أو يرفض معاهدة معلقة."""
    alliance = get_alliance_by_user(user_id)
    if not alliance:
        return False, "❌ لا تملك تحالفاً."
    alliance = dict(alliance)

    if not has_permission(alliance["id"], user_id, "declare_war"):
        return False, "❌ لا تملك صلاحية الرد على المعاهدات."

    if accept:
        ok, msg = accept_treaty(treaty_id, user_id)
        if ok:
            # زيادة النفوذ المتبادل عند قبول معاهدة عسكرية
            from database.db_queries.alliance_diplomacy_queries import get_alliance_treaties
            from database.connection import get_db_conn
            conn = get_db_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM alliance_treaties WHERE id=?", (treaty_id,))
            t = cursor.fetchone()
            if t:
                t = dict(t)
                if t["treaty_type"] == "military_alliance":
                    add_influence(t["alliance_a"], t["alliance_b"], 20.0)
                    add_influence(t["alliance_b"], t["alliance_a"], 20.0)
                    update_alliance_reputation(t["alliance_a"], "helped_ally",
                                               "تحالف عسكري جديد")
                    update_alliance_reputation(t["alliance_b"], "helped_ally",
                                               "تحالف عسكري جديد")
        return ok, msg
    else:
        return reject_treaty(treaty_id, alliance["id"])


def betray_treaty(user_id: int, treaty_id: int) -> tuple[bool, str]:
    """يكسر معاهدة نشطة مع عقوبة سمعة."""
    alliance = get_alliance_by_user(user_id)
    if not alliance:
        return False, "❌ لا تملك تحالفاً."
    alliance = dict(alliance)
    if alliance["leader_id"] != user_id:
        return False, "❌ فقط القائد يمكنه كسر المعاهدات."
    return break_treaty(treaty_id, alliance["id"])


# ══════════════════════════════════════════
# 🌍 التوسع
# ══════════════════════════════════════════

def send_expansion_proposal(user_id: int, target_alliance_id: int,
                            expansion_type: str) -> tuple[bool, str]:
    """يُرسل اقتراح توسع (استيعاب / اندماج / اتحاد)."""
    alliance = get_alliance_by_user(user_id)
    if not alliance:
        return False, "❌ لا تملك تحالفاً."
    alliance = dict(alliance)
    aid = alliance["id"]

    if alliance["leader_id"] != user_id:
        return False, "❌ فقط القائد يمكنه اقتراح التوسع."

    # للاستيعاب: يجب أن يكون المُبادر أقوى
    if expansion_type == "absorb":
        target = get_alliance_by_id(target_alliance_id)
        if not target:
            return False, "❌ التحالف الهدف غير موجود."
        if alliance.get("power", 0) < target.get("power", 0) * 1.5:
            return False, "❌ قوتك يجب أن تكون 1.5× قوة الهدف للاستيعاب."

    ok, msg, exp_id = propose_expansion(aid, target_alliance_id, expansion_type, user_id)
    if ok:
        _notify_alliance_leader(target_alliance_id,
            f"🌍 تلقّى تحالفك اقتراح {_expansion_ar(expansion_type)} "
            f"من تحالف <b>{alliance['name']}</b>.\n"
            f"استخدم: دبلوماسية التحالف")
    return ok, msg


def execute_expansion(user_id: int, exp_id: int, accept: bool) -> tuple[bool, str]:
    """يُنفّذ أو يرفض اقتراح التوسع."""
    alliance = get_alliance_by_user(user_id)
    if not alliance:
        return False, "❌ لا تملك تحالفاً."
    alliance = dict(alliance)
    if alliance["leader_id"] != user_id:
        return False, "❌ فقط القائد يمكنه الرد على اقتراحات التوسع."

    if not accept:
        return reject_expansion(exp_id)

    ok, expansion_type = accept_expansion(exp_id, user_id)
    if not ok:
        return False, expansion_type

    from database.connection import get_db_conn
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alliance_expansion WHERE id=?", (exp_id,))
    exp = dict(cursor.fetchone())
    initiator_id = exp["initiator_id"]
    target_id    = exp["target_id"]

    if expansion_type == "absorb":
        return _do_absorb(initiator_id, target_id)
    elif expansion_type == "merge":
        return _do_merge(initiator_id, target_id)
    elif expansion_type == "federate":
        return _do_federate(initiator_id, target_id)
    return False, "❌ نوع توسع غير معروف."


def _do_absorb(initiator_id: int, target_id: int) -> tuple[bool, str]:
    """يستوعب التحالف الهدف — ينقل أعضاءه وخزينته ثم يحذفه."""
    conn = get_db_conn()
    cursor = conn.cursor()

    # نقل الأعضاء
    cursor.execute("""
        UPDATE alliance_members SET alliance_id=?, role='member'
        WHERE alliance_id=?
    """, (initiator_id, target_id))

    # نقل الخزينة
    cursor.execute("SELECT balance FROM alliance_treasury WHERE alliance_id=?", (target_id,))
    row = cursor.fetchone()
    if row and row[0] > 0:
        _apply_treasury_change(initiator_id, None, "loot_share", row[0],
                               f"استيعاب تحالف #{target_id}")
        cursor.execute("UPDATE alliance_treasury SET balance=0 WHERE alliance_id=?", (target_id,))

    conn.commit()
    delete_alliance(target_id)
    update_alliance_reputation(initiator_id, "war_won", "استيعاب تحالف")
    return True, "✅ تم استيعاب التحالف. انضم أعضاؤه وخزينته إليك."


def _do_merge(initiator_id: int, target_id: int) -> tuple[bool, str]:
    """يدمج تحالفين — ينقل أعضاء الهدف للمُبادر ويحذف الهدف."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE alliance_members SET alliance_id=?, role='member'
        WHERE alliance_id=?
    """, (initiator_id, target_id))

    # دمج الخزينتين
    cursor.execute("SELECT balance FROM alliance_treasury WHERE alliance_id=?", (target_id,))
    row = cursor.fetchone()
    if row and row[0] > 0:
        _apply_treasury_change(initiator_id, None, "loot_share", row[0] * 0.5,
                               f"اندماج مع تحالف #{target_id} (50%)")
        cursor.execute("UPDATE alliance_treasury SET balance=0 WHERE alliance_id=?", (target_id,))

    conn.commit()
    delete_alliance(target_id)
    update_alliance_reputation(initiator_id, "helped_ally", "اندماج تحالفات")
    return True, "✅ تم الاندماج. أعضاء التحالف الآخر انضموا إليك."


def _do_federate(initiator_id: int, target_id: int) -> tuple[bool, str]:
    """يُنشئ اتحاداً بين التحالفين دون دمج."""
    initiator = get_alliance_by_id(initiator_id)
    target    = get_alliance_by_id(target_id)
    if not initiator or not target:
        return False, "❌ أحد التحالفين غير موجود."

    fed_name = f"اتحاد {initiator['name']} و{target['name']}"
    ok, msg, fed_id = create_federation(fed_name, initiator_id, [target_id])
    if ok:
        add_influence(initiator_id, target_id, 30.0)
        add_influence(target_id, initiator_id, 30.0)
    return ok, msg


# ══════════════════════════════════════════
# 🧭 النفوذ
# ══════════════════════════════════════════

def recalc_influence_from_power(alliance_id: int):
    """
    يُعيد حساب نفوذ التحالف على الآخرين بناءً على فارق القوة.
    يُستدعى يومياً.
    """
    from database.db_queries.alliances_queries import get_all_active_alliances
    my = get_alliance_by_id(alliance_id)
    if not my:
        return
    my_power = my.get("power", 0)
    for other in get_all_active_alliances(exclude_id=alliance_id):
        other_power = other.get("power", 1)
        if my_power > other_power * 1.2:
            delta = min(5.0, (my_power / other_power - 1.0) * 3.0)
            add_influence(alliance_id, other["id"], delta)


# ══════════════════════════════════════════
# 🔔 مساعدات
# ══════════════════════════════════════════

def _notify_alliance_leader(alliance_id: int, text: str):
    try:
        from core.bot import bot
        alliance = get_alliance_by_id(alliance_id)
        if alliance:
            bot.send_message(alliance["leader_id"], text, parse_mode="HTML")
    except Exception:
        pass


def _treaty_ar(t: str) -> str:
    return {
        "non_aggression":    "عدم اعتداء",
        "military_alliance": "تحالف عسكري",
        "trade":             "تجارة",
        "protectorate":      "حماية",
    }.get(t, t)


def _expansion_ar(e: str) -> str:
    return {"absorb": "استيعاب", "merge": "اندماج", "federate": "اتحاد"}.get(e, e)


# ══════════════════════════════════════════
# 🗳️ تكامل التصويت — وزن إضافي من النفوذ والمعاهدات
# ══════════════════════════════════════════

def get_diplomacy_vote_bonus(alliance_id: int) -> float:
    """
    يُعيد مضاعف إضافي لوزن التصويت بناءً على:
    - النفوذ النشط على تحالفات أخرى
    - المعاهدات العسكرية النشطة
    - عضوية الاتحاد
    """
    bonus = 0.0

    # نفوذ نشط
    from database.db_queries.alliance_diplomacy_queries import get_influence_bonus_on_vote
    bonus += get_influence_bonus_on_vote(alliance_id, 0)

    # معاهدات عسكرية نشطة
    treaties = get_alliance_treaties(alliance_id, status="active")
    mil_count = sum(1 for t in treaties if t["treaty_type"] == "military_alliance")
    bonus += mil_count * 0.10

    # عضوية اتحاد
    fed = get_federation_by_alliance(alliance_id)
    if fed:
        members = get_federation_members(fed["id"])
        bonus += len(members) * 0.05

    return round(min(bonus, 1.0), 3)   # حد أقصى +100%
