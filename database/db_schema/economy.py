from ..connection import get_db_conn

def create_economy_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # TABLE: economy_stats
    # PURPOSE: Global economy statistics stored as key-value pairs.
    #          Acts as the macro-economic layer of the game.
    #          Values are read and written by bank_service, asset_service,
    #          and economy_service to track the health of the game economy.
    #
    # COLUMNS:
    #   name         — Primary key. The stat name (see keys below).
    #   value        — Current value, stored as TEXT. Cast to float at call site.
    #   last_updated — Unix timestamp of the last update.
    #
    # KEYS AND THEIR MEANING:
    #   inflation          — Current inflation index (0.75–2.5). Computed from
    #                        total money in circulation vs baseline (1,000,000).
    #                        Used to scale salary and investment outcomes.
    #   event_multiplier   — Active global event multiplier (e.g. 1.12 = +12%).
    #                        Applied to salary, investment, and loot calculations.
    #   sink               — Cumulative total of currency removed from circulation
    #                        (transfer fees + asset purchases). Tracks deflation pressure.
    #   total_salary_paid  — Running total of all salary payouts. Tracks money injection.
    #   total_investments  — Count of all investment actions taken.
    #   total_investment_profit — Total currency gained from successful investments.
    #   total_investment_loss   — Total currency lost from failed investments.
    #   total_transfers         — Count of all bank transfers.
    #   total_transfer_volume   — Total currency moved via transfers.
    #   total_transfer_fees     — Total fees collected from transfers (money sink).
    #   total_city_spending     — Total currency spent on city assets/upgrades.
    # ─────────────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS economy_stats (
        name         TEXT PRIMARY KEY,
        value        TEXT    DEFAULT '0.0',
        last_updated INTEGER
    );
    ''')

    # Seed all known keys so they always exist with a default of 0
    _seed_economy_stats(cursor)
    conn.commit()


def _seed_economy_stats(cursor):
    keys = [
        ("inflation",               "1.0"),
        ("event_multiplier",        "1.0"),
        ("sink",                    "0.0"),
        ("total_salary_paid",       "0.0"),
        ("total_investments",       "0.0"),
        ("total_investment_profit", "0.0"),
        ("total_investment_loss",   "0.0"),
        ("total_transfers",         "0.0"),
        ("total_transfer_volume",   "0.0"),
        ("total_transfer_fees",     "0.0"),
        ("total_city_spending",     "0.0"),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO economy_stats (name, value) VALUES (?, ?)", keys
    )
