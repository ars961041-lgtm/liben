"""
استعلامات نظام حوكمة التحالفات
Alliance Governance — DB Queries
"""
import time
from ..connection import get_db_conn

# ── ثوابت السمعة ──
REP_WAR_WIN      =  50
REP_WAR_LOSS     = -20
REP_HELPED_ALLY  =  15
REP_BETRAYAL     = -40
REP_INACTIVE     = -10
REP_WEEKLY_DECAY =  -5   # خصم أسبوعي للتحالفات الخاملة


# ══════════════════════════════════════════
# 🏦 الخزينة
# ══════════════════════════════════════════

def ensure_treasury(alliance_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO alliance_treasury (alliance_id) VALUES (?)
    """, (alliance_id,))
    conn.commit()


def get_treasury(alliance_id: int) -> dict:
    ensure_treasury(alliance_id)
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alliance_treasury WHERE alliance_id = ?", (alliance_id,))
    row = cursor.fetchone()
    return dict(row) if row else {"alliance_id": alliance_id, "balance": 0.0}


def deposit_treasury(alliance_id: int, user_id: int, amount: float, note: str = "") -> tuple[bool, str]:
    """يودع مبلغاً من رصيد اللاعب إلى الخزينة."""
    if amount <= 0:
        return False, "❌ المبلغ يجب أن يكون أكبر من صفر."
    from database.db_queries.bank_queries import get_user_balance, deduct_user_balance
    from modules.bank.utils.constants import CURRENCY_ARABIC_NAME
    bal = get_user_balance(user_id)
    if bal < amount:
        return False, f"❌ رصيدك غير كافٍ ({bal:.0f} {CURRENCY_ARABIC_NAME})."
    deduct_user_balance(user_id, amount)
    _apply_treasury_change(alliance_id, user_id, "deposit", amount, note or "إيداع يدوي")
    return True, f"✅ تم إيداع {amount:.0f} في خزينة التحالف."


def withdraw_treasury(alliance_id: int, user_id: int, amount: float, note: str = "") -> tuple[bool, str]:
    """يسحب مبلغاً من الخزينة إلى رصيد اللاعب."""
    if amount <= 0:
        return False, "❌ المبلغ يجب أن يكون أكبر من صفر."
    treasury = get_treasury(alliance_id)
    from modules.bank.utils.constants import CURRENCY_ARABIC_NAME
    if treasury["balance"] < amount:
        return False, f"❌ رصيد الخزينة غير كافٍ ({treasury['balance']:.0f} {CURRENCY_ARABIC_NAME})."
    from database.db_queries.bank_queries import update_bank_balance
    update_bank_balance(user_id, amount)
    _apply_treasury_change(alliance_id, user_id, "withdraw", -amount, note or "سحب يدوي")
    return True, f"✅ تم سحب {amount:.0f} من خزينة التحالف."


def treasury_loot_share(alliance_id: int, total_loot: float, note: str = "حصة الغنائم"):
    """يضيف حصة الغنائم للخزينة (20% من الغنائم)."""
    share = round(total_loot * 0.20, 2)
    if share > 0:
        _apply_treasury_change(alliance_id, None, "loot_share", share, note)
    return share


def reward_member(alliance_id: int, from_user_id: int, to_user_id: int, amount: float) -> tuple[bool, str]:
    """يكافئ عضواً من الخزينة."""
    treasury = get_treasury(alliance_id)
    from modules.bank.utils.constants import CURRENCY_ARABIC_NAME
    if treasury["balance"] < amount:
        return False, f"❌ رصيد الخزينة غير كافٍ ({treasury['balance']:.0f} {CURRENCY_ARABIC_NAME})."
    from database.db_queries.bank_queries import update_bank_balance
    update_bank_balance(to_user_id, amount)
    _apply_treasury_change(alliance_id, from_user_id, "reward",
                           -amount, f"مكافأة للعضو {to_user_id}")
    return True, f"✅ تم منح {amount:.0f} {CURRENCY_ARABIC_NAME} للعضو."


def get_treasury_log(alliance_id: int, limit: int = 20) -> list[dict]:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM alliance_treasury_log
        WHERE alliance_id = ?
        ORDER BY created_at DESC LIMIT ?
    """, (alliance_id, limit))
    return [dict(r) for r in cursor.fetchall()]


def _apply_treasury_change(alliance_id: int, user_id, tx_type: str, amount: float, note: str):
    conn = get_db_conn()
    cursor = conn.cursor()
    ensure_treasury(alliance_id)
    cursor.execute("""
        UPDATE alliance_treasury
        SET balance = balance + ?,
            total_deposited = total_deposited + MAX(0, ?),
            total_withdrawn = total_withdrawn + MAX(0, -?),
            last_updated = ?
        WHERE alliance_id = ?
    """, (amount, amount, amount, int(time.time()), alliance_id))
    cursor.execute("""
        INSERT INTO alliance_treasury_log (alliance_id, user_id, tx_type, amount, note)
        VALUES (?, ?, ?, ?, ?)
    """, (alliance_id, user_id, tx_type, amount, note))
    conn.commit()


# ══════════════════════════════════════════
# ⭐ السمعة
# ══════════════════════════════════════════

def ensure_reputation(alliance_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO alliance_reputation (alliance_id) VALUES (?)
    """, (alliance_id,))
    conn.commit()


def get_alliance_reputation(alliance_id: int) -> dict:
    ensure_reputation(alliance_id)
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alliance_reputation WHERE alliance_id = ?", (alliance_id,))
    row = cursor.fetchone()
    return dict(row) if row else {}


def update_alliance_reputation(alliance_id: int, event_type: str, note: str = ""):
    """يُحدّث سمعة التحالف بناءً على نوع الحدث."""
    delta_map = {
        "war_won":      REP_WAR_WIN,
        "war_lost":     REP_WAR_LOSS,
        "helped_ally":  REP_HELPED_ALLY,
        "betrayal":     REP_BETRAYAL,
        "inactive":     REP_INACTIVE,
        "weekly_decay": REP_WEEKLY_DECAY,
    }
    delta = delta_map.get(event_type, 0)
    if delta == 0:
        return

    ensure_reputation(alliance_id)
    conn = get_db_conn()
    cursor = conn.cursor()

    field_map = {
        "war_won":     "wars_won",
        "war_lost":    "wars_lost",
        "helped_ally": "allies_helped",
        "betrayal":    "betrayals",
        "inactive":    "inactive_wars",
    }
    field = field_map.get(event_type)
    if field:
        cursor.execute(f"""
            UPDATE alliance_reputation
            SET score = MAX(0, MIN(1000, score + ?)),
                {field} = {field} + 1,
                last_updated = ?
            WHERE alliance_id = ?
        """, (delta, int(time.time()), alliance_id))
    else:
        cursor.execute("""
            UPDATE alliance_reputation
            SET score = MAX(0, MIN(1000, score + ?)),
                last_updated = ?
            WHERE alliance_id = ?
        """, (delta, int(time.time()), alliance_id))

    cursor.execute("""
        INSERT INTO alliance_reputation_log (alliance_id, event_type, delta, note)
        VALUES (?, ?, ?, ?)
    """, (alliance_id, event_type, delta, note))
    conn.commit()
    _recalc_reputation_title(alliance_id)


def _recalc_reputation_title(alliance_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT score, betrayals FROM alliance_reputation WHERE alliance_id = ?", (alliance_id,))
    row = cursor.fetchone()
    if not row:
        return
    score, betrayals = row[0], row[1]
    if betrayals >= 3:
        title = "🐍 خائن"
    elif score >= 800:
        title = "👑 إمبراطورية"
    elif score >= 600:
        title = "⚔️ قوة عظمى"
    elif score >= 400:
        title = "🏰 تحالف راسخ"
    elif score >= 200:
        title = "🤝 تحالف ناشئ"
    else:
        title = "😶 غير معروف"
    cursor.execute("UPDATE alliance_reputation SET title = ? WHERE alliance_id = ?", (title, alliance_id))
    conn.commit()


def get_reputation_bonus(alliance_id: int) -> float:
    """
    يُعيد مضاعف قوة بناءً على السمعة — مع سقف ناعم.

    score 0–200:   0.90x  (عقوبة)
    score 200–400: 1.00x  (محايد)
    score 400–600: 1.05x  (+5%)
    score 600–800: 1.10x  (+10%)
    score 800+:    1.15x  (+15%)  ← سقف ناعم

    السقف الناعم يمنع الهيمنة الكاملة عبر السمعة وحدها.
    """
    rep = get_alliance_reputation(alliance_id)
    score = rep.get("score", 100)
    if score >= 800:
        return 1.15
    elif score >= 600:
        return 1.10
    elif score >= 400:
        return 1.05
    elif score >= 200:
        return 1.00
    else:
        return 0.90


def get_reputation_vote_weight_bonus(alliance_id: int) -> float:
    """
    مكافأة وزن التصويت بناءً على السمعة.
    سقف ناعم: +0.30 كحد أقصى لمنع الهيمنة.

    score 0–200:   -0.10  (عقوبة)
    score 200–400:  0.00
    score 400–600: +0.10
    score 600–800: +0.20
    score 800+:    +0.30  ← سقف ناعم
    """
    rep = get_alliance_reputation(alliance_id)
    score = rep.get("score", 100)
    if score >= 800:
        return 0.30
    elif score >= 600:
        return 0.20
    elif score >= 400:
        return 0.10
    elif score >= 200:
        return 0.00
    else:
        return -0.10


def get_top_alliances_by_reputation(limit: int = 10) -> list[dict]:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ar.*, a.name
        FROM alliance_reputation ar
        JOIN alliances a ON ar.alliance_id = a.id
        ORDER BY ar.score DESC LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# 🏆 الألقاب
# ══════════════════════════════════════════

TITLE_DEFINITIONS = {
    "season_empire":      ("🏆 إمبراطورية الموسم",    "🏆"),
    "strongest_military": ("⚔️ أقوى تحالف عسكري",    "⚔️"),
    "richest":            ("💰 أغنى تحالف",            "💰"),
    "spy_master":         ("🕵️ سيد الجواسيس",         "🕵️"),
    "most_supportive":    ("🤝 أكثر تحالف داعم",       "🤝"),
}


def assign_title(alliance_id: int, title_key: str, expires_days: int = 7):
    """يمنح لقباً لتحالف ويُزيله من التحالف السابق."""
    if title_key not in TITLE_DEFINITIONS:
        return
    title_ar, emoji = TITLE_DEFINITIONS[title_key]
    conn = get_db_conn()
    cursor = conn.cursor()
    expires_at = int(time.time()) + expires_days * 86400
    # UNIQUE(title_key) — يستبدل الحامل السابق
    cursor.execute("""
        INSERT INTO alliance_titles (alliance_id, title_key, title_ar, emoji, expires_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(title_key) DO UPDATE SET
            alliance_id = excluded.alliance_id,
            title_ar    = excluded.title_ar,
            emoji       = excluded.emoji,
            earned_at   = excluded.earned_at,
            expires_at  = excluded.expires_at
    """, (alliance_id, title_key, title_ar, emoji, expires_at))
    conn.commit()


def get_alliance_titles(alliance_id: int) -> list[dict]:
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        SELECT * FROM alliance_titles
        WHERE alliance_id = ? AND (expires_at IS NULL OR expires_at > ?)
    """, (alliance_id, now))
    return [dict(r) for r in cursor.fetchall()]


def get_all_current_titles() -> list[dict]:
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        SELECT at.*, a.name as alliance_name
        FROM alliance_titles at
        JOIN alliances a ON at.alliance_id = a.id
        WHERE at.expires_at IS NULL OR at.expires_at > ?
        ORDER BY at.earned_at DESC
    """, (now,))
    return [dict(r) for r in cursor.fetchall()]


def refresh_all_titles():
    """
    يُعيد حساب وتوزيع جميع الألقاب الأسبوعية.
    يُستدعى من المجدول الأسبوعي.
    """
    conn = get_db_conn()
    cursor = conn.cursor()

    # 🏆 إمبراطورية الموسم — أعلى سمعة
    cursor.execute("""
        SELECT alliance_id FROM alliance_reputation ORDER BY score DESC LIMIT 1
    """)
    row = cursor.fetchone()
    if row:
        assign_title(row[0], "season_empire")

    # ⚔️ أقوى تحالف عسكري — أعلى power
    cursor.execute("SELECT id FROM alliances ORDER BY power DESC LIMIT 1")
    row = cursor.fetchone()
    if row:
        assign_title(row[0], "strongest_military")

    # 💰 أغنى تحالف — أعلى رصيد خزينة
    cursor.execute("""
        SELECT alliance_id FROM alliance_treasury ORDER BY balance DESC LIMIT 1
    """)
    row = cursor.fetchone()
    if row:
        assign_title(row[0], "richest")

    # 🕵️ سيد الجواسيس — أعلى مجموع spy_level لأعضائه
    cursor.execute("""
        SELECT am.alliance_id, COALESCE(SUM(su.spy_level), 0) as total_spy
        FROM alliance_members am
        LEFT JOIN spy_units su ON su.country_id = am.country_id
        GROUP BY am.alliance_id
        ORDER BY total_spy DESC LIMIT 1
    """)
    row = cursor.fetchone()
    if row:
        assign_title(row[0], "spy_master")

    # 🤝 أكثر تحالف داعم — أعلى allies_helped
    cursor.execute("""
        SELECT alliance_id FROM alliance_reputation ORDER BY allies_helped DESC LIMIT 1
    """)
    row = cursor.fetchone()
    if row:
        assign_title(row[0], "most_supportive")


# ══════════════════════════════════════════
# 🧬 الأدوار والصلاحيات
# ══════════════════════════════════════════

def has_permission(alliance_id: int, user_id: int, permission: str) -> bool:
    """يتحقق إذا كان المستخدم يملك صلاحية معينة في التحالف."""
    conn = get_db_conn()
    cursor = conn.cursor()
    # جلب دور المستخدم
    cursor.execute("""
        SELECT role FROM alliance_members
        WHERE alliance_id = ? AND user_id = ?
    """, (alliance_id, user_id))
    row = cursor.fetchone()
    if not row:
        return False
    role = row[0]

    # فحص صلاحية خاصة بالتحالف أولاً، ثم الافتراضية
    cursor.execute("""
        SELECT granted FROM alliance_role_permissions
        WHERE (alliance_id = ? OR alliance_id IS NULL)
          AND role = ? AND permission = ?
        ORDER BY alliance_id DESC NULLS LAST
        LIMIT 1
    """, (alliance_id, role, permission))
    perm_row = cursor.fetchone()
    return bool(perm_row[0]) if perm_row else False


def set_permission(alliance_id: int, role: str, permission: str, granted: bool):
    """يُعدّل صلاحية دور معين في تحالف محدد."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alliance_role_permissions (alliance_id, role, permission, granted)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(alliance_id, role, permission) DO UPDATE SET granted = excluded.granted
    """, (alliance_id, role, permission, 1 if granted else 0))
    conn.commit()


def promote_member(alliance_id: int, target_user_id: int) -> tuple[bool, str]:
    """يرفع عضو إلى ضابط."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role FROM alliance_members WHERE alliance_id = ? AND user_id = ?
    """, (alliance_id, target_user_id))
    row = cursor.fetchone()
    if not row:
        return False, "❌ المستخدم ليس عضواً في التحالف."
    if row[0] == "leader":
        return False, "❌ لا يمكن ترقية القائد."
    if row[0] == "officer":
        return False, "❌ المستخدم ضابط بالفعل."
    cursor.execute("""
        UPDATE alliance_members SET role = 'officer'
        WHERE alliance_id = ? AND user_id = ?
    """, (alliance_id, target_user_id))
    conn.commit()
    return True, "✅ تمت ترقية العضو إلى ضابط ⭐"


def demote_member(alliance_id: int, target_user_id: int) -> tuple[bool, str]:
    """يُخفّض ضابط إلى عضو."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role FROM alliance_members WHERE alliance_id = ? AND user_id = ?
    """, (alliance_id, target_user_id))
    row = cursor.fetchone()
    if not row:
        return False, "❌ المستخدم ليس عضواً في التحالف."
    if row[0] != "officer":
        return False, "❌ المستخدم ليس ضابطاً."
    cursor.execute("""
        UPDATE alliance_members SET role = 'member'
        WHERE alliance_id = ? AND user_id = ?
    """, (alliance_id, target_user_id))
    conn.commit()
    return True, "✅ تم تخفيض الضابط إلى عضو 🪖"


def get_member_role(alliance_id: int, user_id: int) -> str | None:
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role FROM alliance_members WHERE alliance_id = ? AND user_id = ?
    """, (alliance_id, user_id))
    row = cursor.fetchone()
    return row[0] if row else None


# ══════════════════════════════════════════
# 💸 الضرائب
# ══════════════════════════════════════════

def ensure_tax_config(alliance_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO alliance_tax_config (alliance_id) VALUES (?)
    """, (alliance_id,))
    conn.commit()


def get_tax_config(alliance_id: int) -> dict:
    ensure_tax_config(alliance_id)
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alliance_tax_config WHERE alliance_id = ?", (alliance_id,))
    row = cursor.fetchone()
    return dict(row) if row else {"tax_rate": 0.0, "enabled": 0}


def set_tax_rate(alliance_id: int, rate: float, enabled: bool) -> tuple[bool, str]:
    if rate < 0 or rate > 0.20:
        return False, "❌ معدل الضريبة يجب أن يكون بين 0% و20%."
    ensure_tax_config(alliance_id)
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE alliance_tax_config SET tax_rate = ?, enabled = ?
        WHERE alliance_id = ?
    """, (rate, 1 if enabled else 0, alliance_id))
    conn.commit()
    status = "مفعّل" if enabled else "معطّل"
    return True, f"✅ تم تعيين الضريبة على {rate*100:.0f}% ({status})."


def collect_alliance_taxes():
    """
    يجمع الضرائب من جميع التحالفات المفعّلة.
    يُستدعى يومياً من المجدول.
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT atc.alliance_id, atc.tax_rate
        FROM alliance_tax_config atc
        WHERE atc.enabled = 1 AND atc.tax_rate > 0
    """)
    configs = cursor.fetchall()

    for cfg in configs:
        alliance_id = cfg[0]
        rate = cfg[1]
        # جلب أعضاء التحالف
        cursor.execute("""
            SELECT user_id FROM alliance_members WHERE alliance_id = ?
        """, (alliance_id,))
        members = cursor.fetchall()

        total_collected = 0.0
        for (uid,) in members:
            try:
                from database.db_queries.bank_queries import get_user_balance, deduct_user_balance
                bal = get_user_balance(uid)
                tax = round(bal * rate, 2)
                if tax > 0:
                    deduct_user_balance(uid, tax)
                    total_collected += tax
            except Exception:
                pass

        if total_collected > 0:
            _apply_treasury_change(alliance_id, None, "tax", total_collected,
                                   f"ضريبة يومية {rate*100:.0f}%")

        # تحديث وقت آخر جمع
        cursor.execute("""
            UPDATE alliance_tax_config SET last_collect = ? WHERE alliance_id = ?
        """, (int(time.time()), alliance_id))
    conn.commit()


# ══════════════════════════════════════════
# 📊 إحصائيات شاملة
# ══════════════════════════════════════════

def get_alliance_full_stats(alliance_id: int) -> dict:
    """يُعيد ملخصاً شاملاً للتحالف للعرض في الواجهة."""
    treasury = get_treasury(alliance_id)
    reputation = get_alliance_reputation(alliance_id)
    titles = get_alliance_titles(alliance_id)
    tax = get_tax_config(alliance_id)
    return {
        "treasury": treasury,
        "reputation": reputation,
        "titles": titles,
        "tax": tax,
    }
