"""
Government Decision System
Allows country leaders to make strategic decisions with trade-offs.

Available decisions (one active at a time, 3-day cooldown):

  TAX_INCREASE    — tax +10% → income +15%, satisfaction -10
  TAX_DECREASE    — tax -10% → income -10%, satisfaction +10
  MILITARY_FOCUS  — army capacity +20%, income -10%, XP +15%
  ECONOMIC_BOOST  — income +20%, army capacity -10%, satisfaction +5
  INFRA_INVEST    — population cap +20%, income -5%, satisfaction +8
  EDUCATION_DRIVE — XP +30%, scholars +5%, income -5%

Each decision:
  - Lasts 3 days
  - Has a 3-day cooldown after expiry
  - Affects the whole country (all cities)

TABLE: country_decisions
  country_id, decision_key, started_at, expires_at, active
"""
import time
from database.connection import get_db_conn

DECISION_COOLDOWN_DAYS = 3
DECISION_DURATION_DAYS = 3

DECISIONS = {
    "tax_increase": {
        "name_ar": "رفع الضرائب",
        "emoji": "💸",
        "description_ar": "دخل +15%، رضا -10 لمدة 3 أيام",
        "effects": {"income_bonus": 0.15, "satisfaction_delta": -10},
    },
    "tax_decrease": {
        "name_ar": "خفض الضرائب",
        "emoji": "🎁",
        "description_ar": "دخل -10%، رضا +10 لمدة 3 أيام",
        "effects": {"income_bonus": -0.10, "satisfaction_delta": +10},
    },
    "military_focus": {
        "name_ar": "التركيز العسكري",
        "emoji": "⚔️",
        "description_ar": "طاقة الجيش +20%، دخل -10%، XP +15% لمدة 3 أيام",
        "effects": {"army_bonus": 0.20, "income_bonus": -0.10, "xp_bonus": 0.15},
    },
    "economic_boost": {
        "name_ar": "دفعة اقتصادية",
        "emoji": "📈",
        "description_ar": "دخل +20%، طاقة الجيش -10%، رضا +5 لمدة 3 أيام",
        "effects": {"income_bonus": 0.20, "army_bonus": -0.10, "satisfaction_delta": +5},
    },
    "infra_invest": {
        "name_ar": "استثمار البنية التحتية",
        "emoji": "🏗",
        "description_ar": "طاقة السكان +20%، دخل -5%، رضا +8 لمدة 3 أيام",
        "effects": {"pop_cap_bonus": 0.20, "income_bonus": -0.05, "satisfaction_delta": +8},
    },
    "education_drive": {
        "name_ar": "حملة التعليم",
        "emoji": "📚",
        "description_ar": "XP +30%، علماء +5%، دخل -5% لمدة 3 أيام",
        "effects": {"xp_bonus": 0.30, "scholar_bonus": 0.05, "income_bonus": -0.05},
    },
}


def _ensure_table():
    conn = get_db_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS country_decisions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            country_id  INTEGER NOT NULL,
            decision_key TEXT NOT NULL,
            started_at  INTEGER NOT NULL,
            expires_at  INTEGER NOT NULL,
            active      INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (country_id) REFERENCES countries(id)
        )
    """)
    conn.commit()


def get_active_decision(country_id: int) -> dict | None:
    """Returns the active decision for a country, or None."""
    try:
        _ensure_table()
        conn = get_db_conn()
        cursor = conn.cursor()
        now = int(time.time())
        cursor.execute("""
            SELECT * FROM country_decisions
            WHERE country_id = ? AND active = 1 AND expires_at > ?
            ORDER BY started_at DESC LIMIT 1
        """, (country_id, now))
        row = cursor.fetchone()
        if row:
            d = dict(row)
            d["definition"] = DECISIONS.get(d["decision_key"], {})
            return d
        return None
    except Exception:
        return None


def get_decision_effect(country_id: int, effect_key: str) -> float:
    """Returns the value of a specific effect from the active decision."""
    decision = get_active_decision(country_id)
    if not decision:
        return 0.0
    return decision.get("definition", {}).get("effects", {}).get(effect_key, 0.0)


def can_make_decision(country_id: int) -> tuple:
    """Returns (can_decide, reason). Checks cooldown and active decision."""
    try:
        _ensure_table()
        active = get_active_decision(country_id)
        if active:
            remaining = max(0, active["expires_at"] - int(time.time()))
            hours = remaining // 3600
            return False, f"⏳ القرار الحالي ينتهي خلال {hours} ساعة"

        conn = get_db_conn()
        cursor = conn.cursor()
        cooldown_cutoff = int(time.time()) - DECISION_COOLDOWN_DAYS * 86400
        cursor.execute("""
            SELECT expires_at FROM country_decisions
            WHERE country_id = ? AND active = 0
            ORDER BY expires_at DESC LIMIT 1
        """, (country_id,))
        row = cursor.fetchone()
        if row and row[0] > cooldown_cutoff:
            remaining = max(0, row[0] + DECISION_COOLDOWN_DAYS * 86400 - int(time.time()))
            hours = remaining // 3600
            return False, f"⏳ كولداون: {hours} ساعة متبقية"

        return True, "✅ يمكنك اتخاذ قرار جديد"
    except Exception:
        return True, ""


def make_decision(country_id: int, decision_key: str) -> tuple:
    """
    Apply a government decision. Returns (success, message).
    Applies immediate satisfaction delta to all cities.
    """
    if decision_key not in DECISIONS:
        return False, "❌ قرار غير معروف"

    can, reason = can_make_decision(country_id)
    if not can:
        return False, reason

    defn = DECISIONS[decision_key]
    now = int(time.time())
    expires = now + DECISION_DURATION_DAYS * 86400

    try:
        _ensure_table()
        conn = get_db_conn()
        conn.execute("""
            INSERT INTO country_decisions (country_id, decision_key, started_at, expires_at, active)
            VALUES (?, ?, ?, ?, 1)
        """, (country_id, decision_key, now, expires))
        conn.commit()

        # Apply immediate satisfaction delta to all cities
        sat_delta = defn["effects"].get("satisfaction_delta", 0)
        if sat_delta != 0:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM cities WHERE country_id = ?", (country_id,))
            for row in cursor.fetchall():
                from database.db_queries.city_progression_queries import adjust_city_satisfaction
                adjust_city_satisfaction(row[0], float(sat_delta))

        return True, (
            f"{defn['emoji']} <b>تم تفعيل: {defn['name_ar']}</b>\n"
            f"📝 {defn['description_ar']}\n"
            f"⏱️ المدة: {DECISION_DURATION_DAYS} أيام"
        )
    except Exception as e:
        return False, f"❌ خطأ: {e}"


def expire_old_decisions():
    """Called daily to mark expired decisions as inactive."""
    try:
        _ensure_table()
        conn = get_db_conn()
        now = int(time.time())
        conn.execute("""
            UPDATE country_decisions SET active = 0
            WHERE active = 1 AND expires_at <= ?
        """, (now,))
        conn.commit()
    except Exception:
        pass
