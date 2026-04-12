"""
Internal Economy System
Adds a dynamic economic cycle to each city:

  Taxes:       collected from population based on tax rate
  Consumption: costs based on population size and satisfaction
  Production:  influenced by education, infrastructure, and workers

This makes the economy self-sustaining rather than purely asset-based.

═══════════════════════════════════════════════════════════
FORMULAS:
  tax_income    = workers × TAX_PER_WORKER × tax_rate
  consumption   = population × CONSUMPTION_PER_CAPITA
  production    = workers × PRODUCTION_PER_WORKER × (1 + edu_bonus + infra_bonus)
  net_internal  = tax_income + production - consumption

TAX_PER_WORKER       = 0.05   (5 coins per worker per day)
CONSUMPTION_PER_CAPITA = 0.002 (2 coins per person per day)
PRODUCTION_PER_WORKER  = 0.10  (10 coins per worker per day)

Tax rate is set per country (default 0.15 = 15%).
Range: 0.05 (5%) to 0.40 (40%).
High tax → more income but satisfaction -2/day per 5% above 20%.
Low tax  → less income but satisfaction +1/day per 5% below 15%.

TABLE: country_tax_policy
  country_id, tax_rate (0.05–0.40), last_changed
═══════════════════════════════════════════════════════════
"""
import time
from database.connection import get_db_conn
from database.db_queries.city_progression_queries import (
    get_city_population, get_city_satisfaction, adjust_city_satisfaction
)
from database.db_queries.assets_queries import calculate_city_effects

TAX_PER_WORKER         = 0.05
CONSUMPTION_PER_CAPITA = 0.002
PRODUCTION_PER_WORKER  = 0.10
DEFAULT_TAX_RATE       = 0.15
MIN_TAX_RATE           = 0.05
MAX_TAX_RATE           = 0.40


def _ensure_table():
    conn = get_db_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS country_tax_policy (
            country_id   INTEGER PRIMARY KEY,
            tax_rate     REAL    NOT NULL DEFAULT 0.15,
            last_changed INTEGER DEFAULT (strftime('%s','now')),
            FOREIGN KEY (country_id) REFERENCES countries(id)
        )
    """)
    conn.commit()


def get_tax_rate(country_id: int) -> float:
    try:
        _ensure_table()
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT tax_rate FROM country_tax_policy WHERE country_id = ?", (country_id,))
        row = cursor.fetchone()
        return float(row[0]) if row else DEFAULT_TAX_RATE
    except Exception:
        return DEFAULT_TAX_RATE


def set_tax_rate(country_id: int, rate: float) -> tuple:
    """Set tax rate. Returns (success, message)."""
    rate = max(MIN_TAX_RATE, min(MAX_TAX_RATE, round(rate, 2)))
    try:
        _ensure_table()
        conn = get_db_conn()
        now = int(time.time())
        conn.execute("""
            INSERT INTO country_tax_policy (country_id, tax_rate, last_changed)
            VALUES (?, ?, ?)
            ON CONFLICT(country_id) DO UPDATE SET tax_rate = ?, last_changed = ?
        """, (country_id, rate, now, rate, now))
        conn.commit()
        return True, f"✅ تم تعيين معدل الضريبة إلى {rate*100:.0f}%"
    except Exception as e:
        return False, f"❌ خطأ: {e}"


def calculate_internal_economy(city_id: int, country_id: int) -> dict:
    """
    Calculate daily internal economy for a city.
    Returns dict with tax_income, consumption, production, net_internal.
    """
    pop = get_city_population(city_id)
    effects = calculate_city_effects(city_id)
    edu_bonus   = effects.get("education_bonus", 0.0)
    infra_bonus = effects.get("infra_bonus", 0.0)
    tax_rate    = get_tax_rate(country_id)

    try:
        from modules.city.population_types import get_population_types
        dist = get_population_types(city_id)
        workers = dist["workers"]
    except Exception:
        workers = int(pop * 0.60)

    tax_income  = round(workers * TAX_PER_WORKER * tax_rate, 2)
    consumption = round(pop * CONSUMPTION_PER_CAPITA, 2)
    production  = round(workers * PRODUCTION_PER_WORKER * (1 + edu_bonus + infra_bonus), 2)
    net         = round(tax_income + production - consumption, 2)

    return {
        "tax_income":  tax_income,
        "consumption": consumption,
        "production":  production,
        "net_internal": net,
        "tax_rate":    tax_rate,
    }


def apply_tax_satisfaction_effect(city_id: int, country_id: int):
    """
    Daily satisfaction adjustment based on tax rate.
    High tax (> 20%) → satisfaction -2 per 5% above 20%
    Low tax  (< 15%) → satisfaction +1 per 5% below 15%
    """
    rate = get_tax_rate(country_id)
    if rate > 0.20:
        excess = (rate - 0.20) / 0.05
        adjust_city_satisfaction(city_id, -2.0 * excess)
    elif rate < 0.15:
        deficit = (0.15 - rate) / 0.05
        adjust_city_satisfaction(city_id, +1.0 * deficit)


def tick_internal_economy(city_id: int, country_id: int, owner_id: int):
    """
    Daily tick: collect taxes + production, deduct consumption.
    Deposits net_internal into city owner's balance.
    """
    try:
        eco = calculate_internal_economy(city_id, country_id)
        net = eco["net_internal"]
        if net == 0:
            return

        from database.db_queries.bank_queries import get_user_balance, deduct_user_balance
        from modules.bank.utils.bank_service import add_user_balance
        if net > 0:
            add_user_balance(owner_id, net)
        else:
            balance = get_user_balance(owner_id)
            if balance >= abs(net):
                deduct_user_balance(owner_id, abs(net))
            else:
                adjust_city_satisfaction(city_id, -3.0)

        apply_tax_satisfaction_effect(city_id, country_id)
    except Exception as e:
        print(f"[internal_economy] tick failed city={city_id}: {e}")
