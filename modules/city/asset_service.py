"""
Asset purchase & upgrade service.
All business logic lives here — handlers just call these functions.
"""
from database.db_queries.bank_queries import get_user_balance, deduct_user_balance
from database.db_queries.assets_queries import (
    get_asset_by_name, get_asset_by_id, get_asset_branch,
    get_city_asset, upsert_city_asset, upgrade_city_asset,
    log_asset_action, calculate_city_effects
)
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

MAX_LEVEL = 10  # can be overridden per-asset via assets.max_level


# ══════════════════════════════════════════
# 💰 حساب التكاليف
# ══════════════════════════════════════════

def calc_buy_cost(asset: dict, quantity: int) -> float:
    return round(asset["base_price"] * quantity, 2)


def calc_upgrade_cost(asset: dict, from_level: int, quantity: int) -> float:
    """Cost to upgrade `quantity` units from from_level → from_level+1."""
    cost_per = asset["base_price"] * (asset["cost_scale"] ** (from_level - 1))
    return round(cost_per * quantity, 2)


# ══════════════════════════════════════════
# 🟢 شراء
# ══════════════════════════════════════════

def buy_asset(user_id: int, city_id: int, asset_name: str,
              quantity: int, branch_id: int = None):
    if quantity <= 0:
        return False, "❌ الكمية يجب أن تكون أكبر من صفر"

    asset = get_asset_by_name(asset_name)
    if not asset:
        return False, f"❌ العنصر '{asset_name}' غير موجود"

    if branch_id is not None:
        branch = get_asset_branch(branch_id)
        if not branch or branch["asset_id"] != asset["id"]:
            return False, "❌ الفرع المختار غير صالح لهذا المورد"
    else:
        branch = None

    cost = calc_buy_cost(asset, quantity)
    balance = get_user_balance(user_id)
    if balance < cost:
        return False, f"❌ رصيدك {balance:.0f} {CURRENCY_ARABIC_NAME} — تحتاج {cost:.0f} {CURRENCY_ARABIC_NAME}"

    # insert into city_assets FIRST — if this fails, no money is lost
    try:
        upsert_city_asset(city_id, asset["id"], level=1,
                         quantity_delta=quantity, branch_id=branch_id)
    except Exception as e:
        return False, f"❌ خطأ في قاعدة البيانات: {str(e)}"

    # only deduct after successful DB write
    if not deduct_user_balance(user_id, cost):
        # rollback the asset insert
        upsert_city_asset(city_id, asset["id"], level=1,
                         quantity_delta=-quantity, branch_id=branch_id)
        return False, "❌ فشل خصم الرصيد"

    log_asset_action(city_id, user_id, asset["id"], "buy", quantity, 1, 1, cost)

    # record spending for leaderboards
    _record_spending(city_id, cost)

    branch_label = f" {branch['emoji']} {branch['name_ar']}" if branch else ""
    return True, (
        f"✅ تم شراء {quantity} × {asset['emoji']} {asset['name_ar']}{branch_label}\n"
        f"💸 التكلفة: {cost:.0f} {CURRENCY_ARABIC_NAME}\n"
        f"💰 الرصيد المتبقي: {balance - cost:.0f} {CURRENCY_ARABIC_NAME}"
    )


# ══════════════════════════════════════════
# 🔼 ترقية
# ══════════════════════════════════════════

def upgrade_asset(user_id: int, city_id: int, asset_name: str,
                  quantity: int, from_level: int, branch_id: int = None):
    if quantity <= 0:
        return False, "❌ الكمية يجب أن تكون أكبر من صفر"

    asset = get_asset_by_name(asset_name)
    if not asset:
        return False, f"❌ العنصر '{asset_name}' غير موجود"

    max_lvl = asset.get("max_level", MAX_LEVEL)
    if from_level >= max_lvl:
        return False, f"❌ وصلت للمستوى الأقصى ({max_lvl})"

    row = get_city_asset(city_id, asset["id"], from_level, branch_id=branch_id)
    if not row or row["quantity"] < quantity:
        owned = row["quantity"] if row else 0
        return False, f"❌ لديك {owned} وحدة فقط من المستوى {from_level}"

    cost = calc_upgrade_cost(asset, from_level, quantity)
    balance = get_user_balance(user_id)
    if balance < cost:
        return False, f"❌ رصيدك {balance:.0f} {CURRENCY_ARABIC_NAME} — تحتاج {cost:.0f} {CURRENCY_ARABIC_NAME}"

    if not deduct_user_balance(user_id, cost):
        return False, "❌ فشل خصم الرصيد"

    upgrade_city_asset(city_id, asset["id"], from_level, quantity, branch_id=branch_id)
    log_asset_action(city_id, user_id, asset["id"], "upgrade",
                     quantity, from_level, from_level + 1, cost)

    # record spending for leaderboards
    _record_spending(city_id, cost)

    return True, (
        f"⬆️ تمت ترقية {quantity} × {asset['emoji']} {asset['name_ar']}\n"
        f"المستوى: {from_level} → {from_level + 1}\n"
        f"💸 التكلفة: {cost:.0f} {CURRENCY_ARABIC_NAME}\n"
        f"💰 الرصيد المتبقي: {balance - cost:.0f} {CURRENCY_ARABIC_NAME}"
    )


# ══════════════════════════════════════════
# 📊 ملخص المدينة
# ══════════════════════════════════════════

def get_city_summary(city_id: int) -> dict:
    return calculate_city_effects(city_id)


def _record_spending(city_id: int, amount: float):
    """Update city_spending.total_spent and economy_stats — used for leaderboards and macro tracking."""
    try:
        from database.connection import get_db_conn
        conn = get_db_conn()
        conn.execute("""
            INSERT INTO city_spending (city_id, total_spent)
            VALUES (?, ?)
            ON CONFLICT(city_id) DO UPDATE SET total_spent = total_spent + excluded.total_spent
        """, (city_id, amount))
        conn.commit()
    except Exception as e:
        print(f"[asset_service] record_spending failed: {e}")

    # track macro economy stat — total currency spent on city development
    try:
        from database.db_queries.economy_queries import get_economy_stat, set_economy_stat
        from modules.economy.services.economy_service import money_sink
        set_economy_stat("total_city_spending",
                         get_economy_stat("total_city_spending", 0.0) + amount)
        # asset purchases are a money sink (currency leaves circulation)
        money_sink(amount)
    except Exception:
        pass
