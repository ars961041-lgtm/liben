"""
خدمة الحرب السياسية — نسخة محسّنة للإنتاج
Political War Service — Production-Level Business Logic
"""
import time
from database.db_queries.political_war_queries import (
    declare_political_war, cast_war_vote, get_war_votes, get_vote_summary,
    set_war_preparation, start_political_war, end_political_war, cancel_political_war,
    get_political_war, get_active_political_wars, get_voting_wars_expired,
    get_preparation_wars_ready, add_war_member, withdraw_from_war, get_war_members,
    get_total_side_power, is_country_in_war, get_war_log,
    check_war_cooldown, set_war_cooldown,
    update_loyalty, get_loyalty_score, get_alliance_loyalty_board,
    recalc_preparation_power, _log_event,
    LOYALTY_SUPPORT_BONUS, LOYALTY_IGNORE_PENALTY, LOYALTY_WIN_BONUS,
    DEFENSIVE_IGNORE_PENALTY, VOTE_THRESHOLD,
)
from database.db_queries.countries_queries import get_country_by_owner, get_country_budget
from database.db_queries.alliances_queries import (
    get_alliance_by_country, get_alliance_by_id, get_alliance_power,
)
from modules.war.power_calculator import get_country_power
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

WAR_DECLARATION_COST = 500
LOOT_PERCENT = 0.10


# ══════════════════════════════════════════
# 📣 إعلان الحرب
# ══════════════════════════════════════════

def declare_war(user_id, war_type, declaration_type,
                target_country_id=None, target_alliance_id=None, reason=""):
    from database.db_queries.bank_queries import get_user_balance, deduct_user_balance

    country = get_country_by_owner(user_id)
    if not country:
        return False, "❌ لا تملك دولة لإعلان الحرب.", None
    country = dict(country)
    country_id = country["id"]

    if is_country_in_war(country_id):
        return False, "❌ دولتك مشاركة بالفعل في حرب سياسية نشطة.", None

    # جلب التحالف أولاً — يُستخدم في فحص الكولداون وفحص التكرار
    alliance = get_alliance_by_country(country_id)
    attacker_alliance_id = alliance["id"] if alliance else None

    # كولداون التحالف — يُطبَّق على مستوى التحالف كاملاً
    # أي عضو في التحالف يُعلن حرباً → يُقفل التحالف بأكمله
    if attacker_alliance_id:
        can, remaining = check_war_cooldown(attacker_alliance_id)
        if not can:
            from utils.helpers import format_remaining_time
            return False, f"❌ تحالفك في فترة هدنة. انتظر {format_remaining_time(remaining)}.", None

    # فحص تكرار الحرب: لا يمكن إعلان حرب على نفس الهدف إذا كانت هناك حرب نشطة بينهما
    if target_country_id or target_alliance_id:
        try:
            from database.connection import get_db_conn as _gdb
            _conn = _gdb()
            _cur  = _conn.cursor()
            if target_country_id:
                _cur.execute("""
                    SELECT id FROM political_wars
                    WHERE status IN ('voting','preparation','active')
                      AND ((attacker_country_id=? AND defender_country_id=?)
                        OR (attacker_country_id=? AND defender_country_id=?))
                """, (country_id, target_country_id,
                      target_country_id, country_id))
            else:
                _cur.execute("""
                    SELECT id FROM political_wars
                    WHERE status IN ('voting','preparation','active')
                      AND ((attacker_alliance_id=? AND defender_alliance_id=?)
                        OR (attacker_alliance_id=? AND defender_alliance_id=?))
                """, (attacker_alliance_id, target_alliance_id,
                      target_alliance_id, attacker_alliance_id))
            if _cur.fetchone():
                return False, "❌ توجد حرب نشطة بالفعل بين هذين الطرفين.", None
        except Exception:
            pass

    if war_type == "country_vs_country":
        if not target_country_id:
            return False, "❌ يجب تحديد دولة هدف.", None
        if target_country_id == country_id:
            return False, "❌ لا يمكنك إعلان الحرب على نفسك.", None
        defender_country_id = target_country_id
        defender_alliance_id = None
    elif war_type == "alliance_vs_alliance":
        if not attacker_alliance_id:
            return False, "❌ يجب أن تكون في تحالف.", None
        if not target_alliance_id or target_alliance_id == attacker_alliance_id:
            return False, "❌ هدف التحالف غير صالح.", None
        defender_country_id = None
        defender_alliance_id = target_alliance_id
    elif war_type == "hybrid":
        if not attacker_alliance_id:
            return False, "❌ يجب أن تكون في تحالف للحرب الهجينة.", None
        if not target_country_id:
            return False, "❌ يجب تحديد دولة هدف.", None
        defender_country_id = target_country_id
        defender_alliance_id = None
    else:
        return False, "❌ نوع حرب غير صالح.", None

    # فحص معاهدة عدم الاعتداء
    try:
        from database.db_queries.alliance_diplomacy_queries import has_non_aggression
        att_a = get_alliance_by_country(country_id)
        def_a = get_alliance_by_country(defender_country_id) if defender_country_id else None
        if att_a and def_a and has_non_aggression(att_a["id"], def_a["id"]):
            return False, "❌ يوجد اتفاقية عدم اعتداء نشطة. اكسرها أولاً.", None
    except Exception:
        pass

    balance = get_user_balance(user_id)
    if balance < WAR_DECLARATION_COST:
        return False, f"❌ تحتاج {WAR_DECLARATION_COST} {CURRENCY_ARABIC_NAME}. رصيدك: {balance:.0f}", None

    deduct_user_balance(user_id, WAR_DECLARATION_COST)

    war_id = declare_political_war(
        declared_by_user_id=user_id,
        war_type=war_type,
        declaration_type=declaration_type,
        attacker_country_id=country_id,
        attacker_alliance_id=attacker_alliance_id,
        defender_country_id=defender_country_id,
        defender_alliance_id=defender_alliance_id,
        reason=reason,
        war_cost=WAR_DECLARATION_COST,
    )

    if attacker_alliance_id:
        set_war_cooldown(attacker_alliance_id)

    power = get_country_power(country_id)
    add_war_member(war_id, country_id, user_id, "attacker", power, joined_before_start=True)

    if attacker_alliance_id:
        _notify_alliance_for_vote(war_id, attacker_alliance_id, "attacker", user_id)
    _notify_defender_side(war_id, defender_country_id, defender_alliance_id)

    # 📰 News: war declared
    try:
        from modules.magazine.news_generator import on_war_started
        attacker_name = country.get("name", f"#{country_id}")
        if defender_country_id:
            from database.db_queries.countries_queries import get_country_by_owner as _gcbo
            from database.connection import get_db_conn as _gdb
            _conn = _gdb(); _cur = _conn.cursor()
            _cur.execute("SELECT name FROM countries WHERE id=?", (defender_country_id,))
            _row = _cur.fetchone()
            defender_name = _row[0] if _row else f"#{defender_country_id}"
        elif defender_alliance_id:
            _def_a = get_alliance_by_id(defender_alliance_id)
            defender_name = _def_a["name"] if _def_a else f"تحالف #{defender_alliance_id}"
        else:
            defender_name = "هدف مجهول"
        on_war_started(war_id, attacker_name, defender_name,
                       war_type, reason, int(VOTE_THRESHOLD * 100))
    except Exception:
        pass

    type_ar = {"offensive": "هجومية", "defensive": "دفاعية"}.get(declaration_type, declaration_type)
    return True, (
        f"⚔️ تم إعلان الحرب السياسية!\n"
        f"🆔 رقم الحرب: #{war_id}\n"
        f"📋 النوع: {type_ar}\n"
        f"🗳️ التصويت مفتوح 24 ساعة — يلزم {int(VOTE_THRESHOLD*100)}% دعم.\n"
        f"💰 تكلفة الإعلان: {WAR_DECLARATION_COST} {CURRENCY_ARABIC_NAME}"
    ), war_id


# ══════════════════════════════════════════
# 🗳️ التصويت
# ══════════════════════════════════════════

def vote_on_war(user_id, war_id, vote):
    country = get_country_by_owner(user_id)
    if not country:
        return False, "❌ لا تملك دولة."
    country = dict(country)
    country_id = country["id"]

    war = get_political_war(war_id)
    if not war:
        return False, "❌ الحرب غير موجودة."

    # فحص الحالة والموعد النهائي قبل أي عمل مكلف
    if war["status"] != "voting":
        return False, "❌ التصويت على هذه الحرب مغلق."
    if int(time.time()) > war["voting_ends_at"]:
        return False, "⏰ انتهى وقت التصويت على هذه الحرب."

    alliance = get_alliance_by_country(country_id)
    if not alliance:
        return False, "❌ يجب أن تكون في تحالف للتصويت."

    if alliance["id"] not in (war.get("attacker_alliance_id"), war.get("defender_alliance_id")):
        return False, "❌ تحالفك غير معني بهذه الحرب."

    military_power = get_country_power(country_id)
    economy_score  = get_country_budget(country_id)

    role_weight = 1
    try:
        from database.db_queries.alliance_governance_queries import get_member_role
        role = get_member_role(alliance["id"], user_id)
        role_weight = 3 if role == "leader" else (2 if role == "officer" else 1)
    except Exception:
        pass

    try:
        from modules.alliances.diplomacy_service import get_diplomacy_vote_bonus
        military_power *= (1.0 + get_diplomacy_vote_bonus(alliance["id"]))
    except Exception:
        pass

    # مكافأة السمعة على وزن التصويت (سقف ناعم +0.30)
    try:
        from database.db_queries.alliance_governance_queries import get_reputation_vote_weight_bonus
        rep_bonus = get_reputation_vote_weight_bonus(alliance["id"])
        military_power = max(0.0, military_power * (1.0 + rep_bonus))
    except Exception:
        pass

    # الضغط السياسي — تحالفات قوية تُعزّز وزن تصويت حلفائها
    # الصيغة:
    #   avg_power    = متوسط قوة جميع التحالفات
    #   power_ratio  = قوة التحالف / avg_power  (مقيّد بين 0.5 و 3.0)
    #   rep_factor   = get_reputation_bonus()    (0.90 – 1.15)
    #   raw_bonus    = (power_ratio - 1.0) × 0.05 × rep_factor
    #   pressure     = مقيّد بين -0.05 و +0.20  (سقف ناعم)
    try:
        from database.db_queries.alliance_governance_queries import get_reputation_bonus
        from database.connection import get_db_conn as _gdb
        _conn   = _gdb()
        _cursor = _conn.cursor()
        _cursor.execute("SELECT AVG(power) FROM alliances WHERE power > 0")
        _avg_row = _cursor.fetchone()
        avg_power = float(_avg_row[0]) if _avg_row and _avg_row[0] else 1.0

        my_power   = float(alliance.get("power") or 0.0)
        power_ratio = max(0.5, min(3.0, my_power / max(1.0, avg_power)))
        rep_factor  = get_reputation_bonus(alliance["id"])   # 0.90–1.15
        raw_bonus   = (power_ratio - 1.0) * 0.05 * rep_factor
        pressure    = max(-0.05, min(0.20, raw_bonus))       # سقف ناعم

        if pressure != 0.0:
            military_power = max(0.0, military_power * (1.0 + pressure))
    except Exception:
        pass

    success, reason = cast_war_vote(
        war_id=war_id,
        voter_country_id=country_id,
        voter_user_id=user_id,
        alliance_id=alliance["id"],
        vote=vote,
        military_power=military_power,
        economy_score=economy_score,
        alliance_rank=role_weight,
    )

    if not success:
        # الفحص الحاسم داخل المعاملة قد يكشف انتهاء الموعد بعد الفحص الأولي
        if reason == "expired":
            return False, "⏰ انتهى وقت التصويت — لم يُسجَّل صوتك."
        if reason == "locked":
            return False, "🔒 التصويت مقفل في آخر 60 ثانية — لا يمكن تغيير صوتك."
        if reason == "change_limit":
            return False, "⛔ وصلت للحد الأقصى لتغيير التصويت (2 مرات)."
        return False, "❌ فشل تسجيل التصويت. الحرب لم تعد في مرحلة التصويت."

    vote_ar = {"support": "✅ دعم", "reject": "❌ رفض", "neutral": "⚪ محايد"}.get(vote, vote)
    summary = get_vote_summary(war_id)

    return True, (
        f"🗳️ تم تسجيل تصويتك: {vote_ar}\n"
        f"{_full_vote_breakdown(summary)}"
    )


def _vote_bar(pct: float) -> str:
    filled = int(pct / 10)
    empty  = 10 - filled
    return f"[{'█' * filled}{'░' * empty}] {pct:.1f}%"


def _full_vote_breakdown(summary: dict) -> str:
    """
    يُعيد نص التصويت الكامل مع ثلاثة أشرطة ملوّنة:
      🟢 دعم   ████░░░░░░ 40.0%
      🔴 رفض   ██░░░░░░░░ 20.0%
      🟡 محايد ██░░░░░░░░ 20.0%
      🎯 العتبة: 60% | 🟢 سيبدأ / 🔴 لن يبدأ
    """
    def bar(pct):
        f = int(pct / 10)
        return f"{'█'*f}{'░'*(10-f)}"

    s_pct = summary["support_pct"]
    r_pct = summary["reject_pct"]
    n_pct = summary["neutral_pct"]
    thr   = summary["threshold_pct"]
    total = summary["total"]
    count = summary["count"]

    verdict = "🟢 سيبدأ" if summary["passes"] else "🔴 لن يبدأ"

    return (
        f"\n🟢 دعم    [{bar(s_pct)}] {s_pct:.1f}%\n"
        f"🔴 رفض   [{bar(r_pct)}] {r_pct:.1f}%\n"
        f"🟡 محايد [{bar(n_pct)}] {n_pct:.1f}%\n"
        f"🎯 العتبة: {thr:.0f}%  |  {verdict}\n"
        f"📊 الأوزان: دعم {summary['support']:.1f} / رفض {summary['reject']:.1f} "
        f"/ محايد {summary['neutral']:.1f}  ({count} صوت)"
    )


# ══════════════════════════════════════════
# ⚙️ معالجة نتيجة التصويت
# ══════════════════════════════════════════

def resolve_voting(war_id):
    war = get_political_war(war_id)
    if not war or war["status"] != "voting":
        return False, "الحرب ليست في مرحلة التصويت."

    summary  = get_vote_summary(war_id)
    votes    = get_war_votes(war_id)
    passes   = summary["passes"]

    # عقوبة الدول التي لم تصوّت
    _penalize_non_voters(war_id, war, votes)

    if passes:
        set_war_preparation(war_id)
        _add_supporters_as_members(war_id, votes, war)
        _notify_preparation_phase(war_id, war)
        return True, (
            f"✅ الحرب #{war_id} اجتازت التصويت ({summary['support_pct']:.1f}%)!\n"
            f"⏳ مرحلة التحضير: 20 دقيقة."
        )
    else:
        cancel_political_war(war_id, reason="فشل التصويت")
        # عقوبة سمعة المُعلِن
        try:
            from database.db_queries.advanced_war_queries import update_reputation
            update_reputation(war["declared_by_user_id"], ignored=1)
        except Exception:
            pass
        return False, (
            f"🕊️ الحرب #{war_id} أُلغيت.\n"
            f"الدعم: {summary['support_pct']:.1f}% (مطلوب: {summary['threshold_pct']:.0f}%)"
        )


def resolve_preparation(war_id):
    """
    يُحوّل الحرب من التحضير إلى النشطة.

    قبل التفعيل:
    1. يُعيد حساب قوى الجانبين بناءً على الأعضاء النشطين الحاليين.
    2. يتحقق من وجود عضو واحد على الأقل في كل جانب.
    3. إذا أحد الجانبين فارغ → يُلغي الحرب بدلاً من تفعيلها.
    """
    war = get_political_war(war_id)
    if not war or war["status"] != "preparation":
        return False, "الحرب ليست في مرحلة التحضير."

    # إعادة حساب القوى الحالية
    sides = recalc_preparation_power(war_id)

    att_count = sides["attacker"]["count"]
    def_count  = sides["defender"]["count"]
    att_power  = sides["attacker"]["power"]
    def_power  = sides["defender"]["power"]

    # التحقق من الجدوى: يجب أن يكون لكل جانب عضو واحد على الأقل
    if att_count == 0 or def_count == 0:
        empty_side = "المهاجمون" if att_count == 0 else "المدافعون"
        cancel_political_war(war_id, reason=f"لا يوجد أعضاء في جانب {empty_side}")
        return False, (
            f"❌ الحرب #{war_id} أُلغيت — جانب {empty_side} لا يملك أعضاء نشطين."
        )

    start_political_war(war_id)
    _notify_war_started(war_id, war)
    return True, (
        f"⚔️ الحرب #{war_id} بدأت رسمياً!\n"
        f"💪 المهاجمون ({att_count}): {att_power:.0f}\n"
        f"🛡️ المدافعون ({def_count}): {def_power:.0f}"
    )


def _add_supporters_as_members(war_id, votes, war):
    for v in votes:
        if v["vote"] != "support":
            continue
        cid = v["voter_country_id"]
        uid = v["voter_user_id"]
        power = get_country_power(cid)
        side = "attacker" if war.get("attacker_alliance_id") == v["alliance_id"] else "defender"
        add_war_member(war_id, cid, uid, side, power, joined_before_start=True)
        # مكافأة الولاء للداعمين
        _update_loyalty_for_vote(war_id, v["alliance_id"], cid, uid, "support",
                                 war.get("declaration_type", "offensive"))


def _penalize_non_voters(war_id, war, votes):
    """يُعاقب الدول التي لم تصوّت — عقوبة أشد في الحروب الدفاعية."""
    from database.db_queries.advanced_war_queries import update_reputation
    alliance_id = war.get("attacker_alliance_id") or war.get("defender_alliance_id")
    if not alliance_id:
        return
    alliance = get_alliance_by_id(alliance_id)
    if not alliance:
        return

    voted_countries = {v["voter_country_id"] for v in votes}
    is_defensive = war.get("declaration_type") == "defensive"

    for member in alliance.get("members", []):
        cid = member.get("country_id")
        uid = member.get("user_id")
        if not cid or cid in voted_countries:
            continue
        # عقوبة السمعة
        rep_penalty = DEFENSIVE_IGNORE_PENALTY if is_defensive else 5
        update_reputation(uid, ignored=1)
        # عقوبة الولاء
        loyalty_delta = LOYALTY_IGNORE_PENALTY * (1.5 if is_defensive else 1.0)
        update_loyalty(alliance_id, cid, uid, loyalty_delta)


def _update_loyalty_for_vote(war_id, alliance_id, country_id, user_id, vote, declaration_type):
    if vote == "support":
        delta = LOYALTY_SUPPORT_BONUS * (1.5 if declaration_type == "defensive" else 1.0)
        update_loyalty(alliance_id, country_id, user_id, delta)


# ══════════════════════════════════════════
# 🏁 نتيجة الحرب
# ══════════════════════════════════════════

def resolve_war_outcome(war_id):
    war = get_political_war(war_id)
    if not war or war["status"] != "active":
        return False, "الحرب غير نشطة."

    att_power = get_total_side_power(war_id, "attacker")
    def_power = get_total_side_power(war_id, "defender")

    if att_power > def_power * 1.1:
        winner_side, loser_side = "attacker", "defender"
    elif def_power > att_power * 1.1:
        winner_side, loser_side = "defender", "attacker"
    else:
        winner_side, loser_side = "draw", None

    end_political_war(war_id, winner_side)
    loot_msg = ""
    if winner_side != "draw" and loser_side:
        loot_msg = _distribute_loot(war_id, war, winner_side, loser_side)

    _update_member_reputations_and_loyalty(war_id, winner_side)
    _update_war_momentum(war_id, war, winner_side)

    # 📰 News: war ended
    try:
        from modules.magazine.news_generator import on_war_ended
        att_name = _resolve_side_name(war, "attacker")
        def_name = _resolve_side_name(war, "defender")
        total_loot = _calc_total_loot(war_id)
        on_war_ended(war_id, winner_side, att_name, def_name,
                     att_power, def_power, total_loot)
    except Exception:
        pass

    result_ar = {"attacker": "⚔️ المهاجمون", "defender": "🛡️ المدافعون",
                 "draw": "🤝 تعادل"}.get(winner_side, winner_side)
    return True, (
        f"🏁 انتهت الحرب السياسية #{war_id}\n"
        f"🏆 الفائز: {result_ar}\n"
        f"💪 المهاجمون: {att_power:.0f} | 🛡️ المدافعون: {def_power:.0f}\n"
        f"{loot_msg}"
    )


def _distribute_loot(war_id, war, winner_side, loser_side):
    from database.db_queries.bank_queries import deduct_user_balance, update_bank_balance
    from database.db_queries.alliance_governance_queries import (
        treasury_loot_share, update_alliance_reputation,
    )
    losers  = get_war_members(war_id, loser_side)
    winners = get_war_members(war_id, winner_side)
    if not losers or not winners:
        return ""

    total_loot = 0.0
    for loser in losers:
        budget = get_country_budget(loser["country_id"])
        loot = budget * LOOT_PERCENT
        if loot > 0:
            try:
                deduct_user_balance(loser["user_id"], loot)
                total_loot += loot
            except Exception:
                pass

    if total_loot > 0:
        winner_alliance_id = None
        try:
            w0 = winners[0]
            a = get_alliance_by_country(w0["country_id"])
            if a:
                winner_alliance_id = a["id"]
        except Exception:
            pass

        treasury_cut = 0.0
        if winner_alliance_id:
            treasury_cut = treasury_loot_share(winner_alliance_id, total_loot,
                                               f"غنائم حرب #{war_id}")
            update_alliance_reputation(winner_alliance_id, "war_won", f"فوز في حرب #{war_id}")

        member_loot = total_loot - treasury_cut
        per_winner  = member_loot / max(1, len(winners))
        for winner in winners:
            try:
                update_bank_balance(winner["user_id"], per_winner)
            except Exception:
                pass

        loser_alliance_id = None
        try:
            l0 = losers[0]
            a = get_alliance_by_country(l0["country_id"])
            if a:
                loser_alliance_id = a["id"]
        except Exception:
            pass
        if loser_alliance_id:
            update_alliance_reputation(loser_alliance_id, "war_lost", f"خسارة في حرب #{war_id}")

    return f"💰 الغنائم: {total_loot:.0f} {CURRENCY_ARABIC_NAME} (لكل فائز: {total_loot/max(1,len(winners)):.0f})"


def _resolve_side_name(war: dict, side: str) -> str:
    """Returns a human-readable name for attacker or defender side."""
    try:
        if side == "attacker":
            aid = war.get("attacker_alliance_id")
            cid = war.get("attacker_country_id")
        else:
            aid = war.get("defender_alliance_id")
            cid = war.get("defender_country_id")
        if aid:
            a = get_alliance_by_id(aid)
            return a["name"] if a else f"تحالف #{aid}"
        if cid:
            from database.connection import get_db_conn as _gdb
            _conn = _gdb(); _cur = _conn.cursor()
            _cur.execute("SELECT name FROM countries WHERE id=?", (cid,))
            row = _cur.fetchone()
            return row[0] if row else f"دولة #{cid}"
    except Exception:
        pass
    return "مجهول"


def _calc_total_loot(war_id: int) -> float:
    """Estimates total loot from war members' budgets."""
    try:
        losers = get_war_members(war_id, "defender") or get_war_members(war_id, "attacker")
        total = 0.0
        for m in losers:
            total += get_country_budget(m["country_id"]) * LOOT_PERCENT
        return total
    except Exception:
        return 0.0


def _update_war_momentum(war_id, war, winner_side):
    """
    Updates win streak for both alliances after a war ends.
    Winner's streak increments (capped at 5), loser's resets to 0.
    Draws leave both streaks unchanged.
    """
    from database.db_queries.alliances_queries import record_war_result
    if winner_side == "draw":
        return

    att_alliance_id = war.get("attacker_alliance_id")
    def_alliance_id = war.get("defender_alliance_id")

    if winner_side == "attacker":
        winner_aid, loser_aid = att_alliance_id, def_alliance_id
    else:
        winner_aid, loser_aid = def_alliance_id, att_alliance_id

    try:
        if winner_aid:
            new_streak = record_war_result(winner_aid, won=True)
            bonus_pct  = min(new_streak, 5) * 2
            # إعادة حساب قوة التحالف الفائز لتطبيق المكافأة فوراً
            from database.db_queries.alliances_queries import _recalc_alliance_power
            _recalc_alliance_power(winner_aid)
    except Exception:
        pass

    try:
        if loser_aid:
            record_war_result(loser_aid, won=False)
            from database.db_queries.alliances_queries import _recalc_alliance_power
            _recalc_alliance_power(loser_aid)
    except Exception:
        pass


def _update_member_reputations_and_loyalty(war_id, winner_side):
    from database.db_queries.advanced_war_queries import update_reputation
    members = get_war_members(war_id)
    for m in members:
        if m["side"] == winner_side:
            update_reputation(m["user_id"], helped=1)
            _update_loyalty_for_member(war_id, m["country_id"], m["user_id"], LOYALTY_WIN_BONUS)
        else:
            _update_loyalty_for_member(war_id, m["country_id"], m["user_id"], -5.0)


def _update_loyalty_for_member(war_id, country_id, user_id, delta):
    from database.db_queries.political_war_queries import _update_loyalty_from_war
    _update_loyalty_from_war(war_id, country_id, user_id, delta)


# ══════════════════════════════════════════
# 🚪 الانسحاب
# ══════════════════════════════════════════

def withdraw_country_from_war(user_id, war_id):
    country = get_country_by_owner(user_id)
    if not country:
        return False, "❌ لا تملك دولة."
    country = dict(country)
    country_id = country["id"]

    ok, msg = withdraw_from_war(war_id, country_id, user_id)
    if not ok:
        return False, msg

    war = get_political_war(war_id)
    country_name = country.get("name", f"#{country_id}")

    # ─── تحديد اسم الخصم ───
    opponent_name = _get_opponent_name(war, country_id)

    # ─── بث الانسحاب لجميع المجموعات ───
    _broadcast_withdrawal(war_id, country_name, opponent_name, war)

    # ─── إشعار المشاركين في الحرب ───
    _notify_war_participants_withdrawal(war_id, country_name)

    if not war:
        return True, msg

    # ─── هل المنسحب هو الطرف الرئيسي؟ ───
    is_main_party = (
        war.get("attacker_country_id") == country_id or
        war.get("defender_country_id") == country_id
    )

    if war["status"] == "active":
        if is_main_party:
            _terminate_war_on_withdrawal(war_id, war, country_id, country_name)
        else:
            try:
                recalc_preparation_power(war_id)
            except Exception:
                pass

        # ─── إشعار خيانة في المجلة ───
        try:
            from modules.magazine.news_generator import on_war_betrayal
            from database.db_queries.alliances_queries import get_alliance_by_country as _gabc
            _alliance = _gabc(country_id)
            alliance_name = _alliance["name"] if _alliance else "تحالف مجهول"
            on_war_betrayal(war_id, country_name, alliance_name)
        except Exception:
            pass

    elif war["status"] == "preparation":
        if is_main_party:
            # الطرف الرئيسي ينسحب في التحضير → إلغاء فوري
            cancel_political_war(war_id, reason=f"انسحاب الطرف الرئيسي ({country_name}) في مرحلة التحضير")
            _log_event(war_id, country_id, user_id, "withdrawn",
                       {"reason": "main_party_withdrawal_preparation", "country": country_name})
            _notify_war_cancelled_preparation(war_id, country_name)
        else:
            _recalc_and_notify_preparation(war_id, war)

    elif war["status"] == "voting":
        # انسحاب في مرحلة التصويت — إذا كان الطرف الرئيسي → ألغِ الحرب
        if is_main_party:
            cancel_political_war(war_id, reason=f"انسحاب الطرف الرئيسي ({country_name}) في مرحلة التصويت")
            _log_event(war_id, country_id, user_id, "withdrawn",
                       {"reason": "main_party_withdrawal_voting", "country": country_name})
            _notify_war_cancelled_preparation(war_id, country_name)

    return True, msg


def _get_opponent_name(war: dict, country_id: int) -> str:
    """يرجع اسم الطرف الآخر في الحرب."""
    if not war:
        return "طرف مجهول"
    try:
        from database.connection import get_db_conn
        conn = get_db_conn()
        cursor = conn.cursor()
        # إذا كان المنسحب هو المهاجم → الخصم هو المدافع والعكس
        if war.get("attacker_country_id") == country_id:
            opp_id = war.get("defender_country_id")
        else:
            opp_id = war.get("attacker_country_id")
        if opp_id:
            cursor.execute("SELECT name FROM countries WHERE id=?", (opp_id,))
            row = cursor.fetchone()
            if row:
                return row[0]
        # تحالف
        if war.get("attacker_alliance_id") or war.get("defender_alliance_id"):
            from database.db_queries.alliances_queries import get_alliance_by_id
            aid = war.get("defender_alliance_id") or war.get("attacker_alliance_id")
            a = get_alliance_by_id(aid)
            if a:
                return a["name"]
    except Exception:
        pass
    return "الطرف الآخر"


def _broadcast_withdrawal(war_id: int, country_name: str, opponent_name: str, war: dict):
    """
    يبث إشعار الانسحاب لجميع المجموعات التي تملك enable_news=1.
    """
    try:
        from core.bot import bot
        from database.connection import get_db_conn
        import time as _time

        ts = _time.strftime("%H:%M", _time.localtime())
        war_status_ar = {
            "active":      "⚔️ نشطة",
            "preparation": "⏳ تحضير",
            "voting":      "🗳️ تصويت",
        }.get(war.get("status", ""), "")

        msg = (
            f"📢 <b>إشعار حرب سياسية</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🚪 <b>{country_name}</b> انسحبت من الحرب السياسية!\n"
            f"⚔️ الحرب: <b>#{war_id}</b> {war_status_ar}\n"
            f"🆚 ضد: <b>{opponent_name}</b>\n"
            f"🕐 الوقت: {ts}"
        )

        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT group_id FROM groups WHERE enable_news=1")
        groups = cursor.fetchall()

        for (gid,) in groups:
            try:
                bot.send_message(gid, msg, parse_mode="HTML")
            except Exception:
                pass
    except Exception:
        pass


def _notify_war_participants_withdrawal(war_id: int, country_name: str):
    """يُرسل إشعاراً خاصاً لجميع المشاركين في الحرب."""
    try:
        from core.bot import bot
        from database.connection import get_db_conn
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT user_id FROM political_war_members WHERE war_id=?",
            (war_id,)
        )
        for (uid,) in cursor.fetchall():
            try:
                bot.send_message(
                    uid,
                    f"🚪 <b>انسحاب من الحرب #{war_id}</b>\n"
                    f"دولة <b>{country_name}</b> انسحبت من الحرب.",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    except Exception:
        pass


def _terminate_war_on_withdrawal(war_id: int, war: dict, withdrawer_id: int, country_name: str):
    """
    ينهي الحرب فوراً عندما ينسحب الطرف الرئيسي (المهاجم أو المدافع).
    يُسجّل الحالة كـ 'withdrawn' في السجل ويُرسل إشعاراً للجميع.
    """
    try:
        # تحديد الفائز: الطرف الآخر يفوز تلقائياً
        if war.get("attacker_country_id") == withdrawer_id:
            winner_side = "defender"
        else:
            winner_side = "attacker"

        # إنهاء الحرب بحالة 'ended' مع تسجيل سبب الانسحاب
        end_political_war(war_id, winner_side)

        # تسجيل حدث الانسحاب في السجل
        _log_event(war_id, withdrawer_id, None, "withdrawn",
                   {"reason": "main_party_withdrawal", "country": country_name})

        # إشعار المشاركين بنتيجة الحرب
        try:
            from core.bot import bot
            winner_ar = "⚔️ المهاجمون" if winner_side == "attacker" else "🛡️ المدافعون"
            from database.connection import get_db_conn
            conn = get_db_conn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT user_id FROM political_war_members WHERE war_id=?",
                (war_id,)
            )
            for (uid,) in cursor.fetchall():
                try:
                    bot.send_message(
                        uid,
                        f"🏁 <b>الحرب #{war_id} انتهت بالانسحاب</b>\n"
                        f"انسحبت <b>{country_name}</b> — الطرف الرئيسي.\n"
                        f"🏆 الفائز: {winner_ar}",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
        except Exception:
            pass

    except Exception:
        pass


def _recalc_and_notify_preparation(war_id: int, war: dict):
    """
    يُعيد حساب قوى الجانبين بعد انسحاب في مرحلة التحضير
    ويُرسل إشعاراً لجميع الأعضاء بالأرقام المحدّثة.
    """
    try:
        sides = recalc_preparation_power(war_id)
        att   = sides["attacker"]
        dfd   = sides["defender"]

        # إذا أحد الجانبين أصبح فارغاً → إلغاء فوري
        if att["count"] == 0 or dfd["count"] == 0:
            empty = "المهاجمون" if att["count"] == 0 else "المدافعون"
            cancel_political_war(war_id, reason=f"لا أعضاء في جانب {empty} بعد الانسحاب")
            _notify_war_cancelled_preparation(war_id, f"جانب {empty} لم يعد يملك أعضاء نشطين")
            return

        # إشعار الأعضاء بالأرقام المحدّثة
        try:
            from core.bot import bot
            members = get_war_members(war_id)
            for m in members:
                try:
                    bot.send_message(
                        m["user_id"],
                        f"📊 <b>تحديث مرحلة التحضير — حرب #{war_id}</b>\n"
                        f"انسحب أحد الأعضاء. الأرقام المحدّثة:\n"
                        f"⚔️ المهاجمون ({att['count']}): {att['power']:.0f}\n"
                        f"🛡️ المدافعون ({dfd['count']}): {dfd['power']:.0f}",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
        except Exception:
            pass

    except Exception:
        pass


def _notify_war_cancelled_preparation(war_id: int, reason_label: str):
    """يُرسل إشعار إلغاء الحرب لجميع المشاركين."""
    try:
        from core.bot import bot
        from database.connection import get_db_conn
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT user_id FROM political_war_members WHERE war_id=?",
            (war_id,)
        )
        for (uid,) in cursor.fetchall():
            try:
                bot.send_message(
                    uid,
                    f"❌ <b>الحرب #{war_id} أُلغيت</b>\n"
                    f"السبب: {reason_label}",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    except Exception:
        pass


# ══════════════════════════════════════════
# 📊 نص حالة الحرب
# ══════════════════════════════════════════

def get_war_status_text(war_id):
    war = get_political_war(war_id)
    if not war:
        return "❌ الحرب غير موجودة."

    status_ar = {
        "voting":      "🗳️ تصويت",
        "preparation": "⏳ تحضير",
        "active":      "⚔️ نشطة",
        "ended":       "🏁 منتهية",
        "cancelled":   "❌ ملغاة",
    }.get(war["status"], war["status"])

    type_ar    = {"offensive": "هجومية", "defensive": "دفاعية"}.get(war["declaration_type"], "")
    wtype_ar   = {
        "country_vs_country":  "دولة ضد دولة",
        "alliance_vs_alliance":"تحالف ضد تحالف",
        "hybrid":              "هجين",
    }.get(war["war_type"], war["war_type"])

    lines = [
        f"⚔️ الحرب السياسية #{war_id}",
        f"📋 {wtype_ar} ({type_ar})",
        f"📌 الحالة: {status_ar}",
    ]

    if war["status"] == "voting":
        remaining = max(0, war["voting_ends_at"] - int(time.time()))
        from utils.helpers import format_remaining_time
        lines.append(f"⏳ ينتهي التصويت خلال: {format_remaining_time(remaining)}")
        summary = get_vote_summary(war_id)
        lines.append(_full_vote_breakdown(summary))

    elif war["status"] == "preparation":
        remaining = max(0, (war.get("preparation_ends_at") or 0) - int(time.time()))
        from utils.helpers import format_remaining_time
        lines.append(f"⏳ التحضير ينتهي خلال: {format_remaining_time(remaining)}")
        lines.append("يمكنك الانسحاب أو إرسال تعزيزات الآن.")

    elif war["status"] == "active":
        att = get_total_side_power(war_id, "attacker")
        dfd = get_total_side_power(war_id, "defender")
        lines.append(f"💪 المهاجمون: {att:.0f} | 🛡️ المدافعون: {dfd:.0f}")

    elif war["status"] == "ended" and war.get("winner_side"):
        winner_ar = {"attacker": "⚔️ المهاجمون", "defender": "🛡️ المدافعون",
                     "draw": "🤝 تعادل"}.get(war["winner_side"], "")
        lines.append(f"🏆 الفائز: {winner_ar}")

    if war.get("reason"):
        lines.append(f"📝 السبب: {war['reason']}")

    return "\n".join(lines)


# ══════════════════════════════════════════
# 🔔 الإشعارات
# ══════════════════════════════════════════

def _notify_alliance_for_vote(war_id, alliance_id, side, exclude_user_id):
    try:
        from core.bot import bot
        alliance = get_alliance_by_id(alliance_id)
        if not alliance:
            return
        side_ar = "المهاجم" if side == "attacker" else "المدافع"
        for member in alliance.get("members", []):
            uid = member["user_id"]
            if uid == exclude_user_id:
                continue
            try:
                bot.send_message(uid,
                    f"🗳️ <b>تصويت على حرب سياسية!</b>\n"
                    f"تحالفك طرف {side_ar} في حرب #{war_id}.\n"
                    f"يلزم {int(VOTE_THRESHOLD*100)}% دعم لبدء الحرب.\n"
                    f"استخدم: الحرب السياسية",
                    parse_mode="HTML")
            except Exception:
                pass
    except Exception:
        pass


def _notify_defender_side(war_id, defender_country_id, defender_alliance_id):
    try:
        from core.bot import bot
        from database.connection import get_db_conn
        if defender_country_id:
            conn = get_db_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT owner_id FROM countries WHERE id=?", (defender_country_id,))
            row = cursor.fetchone()
            if row:
                try:
                    bot.send_message(row[0],
                        f"⚠️ <b>تحذير: تم إعلان الحرب عليك!</b>\n"
                        f"حرب سياسية #{war_id} أُعلنت ضد دولتك.\n"
                        f"استخدم: الحرب السياسية",
                        parse_mode="HTML")
                except Exception:
                    pass
        if defender_alliance_id:
            from database.db_queries.alliances_queries import get_alliance_by_id
            alliance = get_alliance_by_id(defender_alliance_id)
            if alliance:
                for member in alliance.get("members", []):
                    try:
                        bot.send_message(member["user_id"],
                            f"⚠️ <b>تحذير: تم إعلان الحرب على تحالفك!</b>\n"
                            f"حرب سياسية #{war_id}.\nاستخدم: الحرب السياسية",
                            parse_mode="HTML")
                    except Exception:
                        pass
    except Exception:
        pass


def _notify_preparation_phase(war_id, war):
    try:
        from core.bot import bot
        alliance_id = war.get("attacker_alliance_id") or war.get("defender_alliance_id")
        if not alliance_id:
            return
        alliance = get_alliance_by_id(alliance_id)
        if not alliance:
            return
        for member in alliance.get("members", []):
            try:
                bot.send_message(member["user_id"],
                    f"⏳ <b>مرحلة التحضير بدأت!</b>\n"
                    f"الحرب #{war_id} اجتازت التصويت.\n"
                    f"لديك 20 دقيقة للانسحاب أو إرسال تعزيزات.\n"
                    f"استخدم: الحرب السياسية",
                    parse_mode="HTML")
            except Exception:
                pass
    except Exception:
        pass


def _notify_war_started(war_id, war):
    try:
        from core.bot import bot
        for side in ("attacker", "defender"):
            members = get_war_members(war_id, side)
            for m in members:
                try:
                    bot.send_message(m["user_id"],
                        f"⚔️ <b>الحرب #{war_id} بدأت رسمياً!</b>\n"
                        f"أنت في الجانب: {'⚔️ المهاجمين' if side == 'attacker' else '🛡️ المدافعين'}",
                        parse_mode="HTML")
                except Exception:
                    pass
    except Exception:
        pass
