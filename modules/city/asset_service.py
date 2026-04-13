"""
Asset purchase & upgrade service.
All business logic lives here — handlers just call these functions.
"""
import logging

from database.db_queries.bank_queries import get_user_balance, deduct_user_balance
from database.db_queries.assets_queries import (
    get_asset_by_name, get_asset_by_id,
    get_city_asset, upsert_city_asset, upgrade_city_asset,
    log_asset_action, calculate_city_effects
)
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

logger = logging.getLogger(__name__)

MAX_LEVEL = 10  # can be overridden per-asset via assets.max_level


def _apply_asset_discount(base_cost: float) -> tuple[float, float]:
    """Returns (final_cost, discount_pct). discount_pct=0 if no event active."""
    try:
        from modules.progression.global_events import get_event_effect
        discount = get_event_effect("asset_cost_discount")
        if discount > 0:
            final = round(base_cost * (1 - discount), 2)
            logger.info("[EVENT_APPLIED] type=asset_cost_discount, discount=%.0f%%, base=%.0f, final=%.0f",
                        discount * 100, base_cost, final)
            return final, discount
    except Exception:
        pass
    logger.debug("[EVENT_SKIP] asset_cost_discount — no active event or category mismatch")
    return base_cost, 0.0


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

def buy_asset(user_id: int, city_id: int, asset_name: str, quantity: int):
    if quantity <= 0:
        return False, "❌ الكمية يجب أن تكون أكبر من صفر"

    # Block construction during rebellion (stage 3)
    try:
        from modules.city.city_simulation import is_construction_blocked
        if is_construction_blocked(city_id):
            return False, "🔴 المدينة في حالة تمرد كامل! لا يمكن البناء حتى تستعيد الاستقرار."
    except Exception:
        pass

    asset = get_asset_by_name(asset_name)
    if not asset:
        return False, f"❌ العنصر '{asset_name}' غير موجود"

    cost = calc_buy_cost(asset, quantity)
    # ─── apply event discount (leaderboard uses base cost) ───
    final_cost, discount = _apply_asset_discount(cost)
    balance = get_user_balance(user_id)
    if balance < final_cost:
        return False, f"❌ رصيدك {balance:.0f} {CURRENCY_ARABIC_NAME} — تحتاج {final_cost:.0f} {CURRENCY_ARABIC_NAME}"

    try:
        upsert_city_asset(city_id, asset["id"], level=1, quantity_delta=quantity)
    except Exception as e:
        return False, f"❌ خطأ في قاعدة البيانات: {str(e)}"

    if not deduct_user_balance(user_id, final_cost):
        upsert_city_asset(city_id, asset["id"], level=1, quantity_delta=-quantity)
        return False, "❌ فشل خصم الرصيد"

    # log and track BASE cost so leaderboards are unaffected by event discounts
    log_asset_action(city_id, user_id, asset["id"], "buy", quantity, 1, 1, cost)
    _record_spending(city_id, cost)

    event_line = f"🎯 خصم الحدث: -{discount*100:.0f}% ({asset['name_ar']})\n💡 الخصم: -{cost - final_cost:.0f} {CURRENCY_ARABIC_NAME}\n" if discount > 0 else ""
    return True, (
        f"✅ تم الشراء بنجاح\n"
        f"📦 العنصر: {asset['emoji']} {asset['name_ar']}\n"
        f"🔢 الكمية: {quantity}\n"
        f"🪖 السعر الأصلي: {cost:.0f} {CURRENCY_ARABIC_NAME}\n"
        f"{event_line}"
        f"✔ المدفوع الفعلي: {final_cost:.0f} {CURRENCY_ARABIC_NAME}\n"
        f"💳 الرصيد المتبقي: {balance - final_cost:.0f} {CURRENCY_ARABIC_NAME}"
    )


# ══════════════════════════════════════════
# 🔼 ترقية
# ══════════════════════════════════════════

def upgrade_asset(user_id: int, city_id: int, asset_name: str,
                  quantity: int, from_level: int):
    if quantity <= 0:
        return False, "❌ الكمية يجب أن تكون أكبر من صفر"

    # Block upgrades during rebellion (stage 3)
    try:
        from modules.city.city_simulation import is_construction_blocked
        if is_construction_blocked(city_id):
            return False, "🔴 المدينة في حالة تمرد كامل! لا يمكن الترقية حتى تستعيد الاستقرار."
    except Exception:
        pass

    asset = get_asset_by_name(asset_name)
    if not asset:
        return False, f"❌ العنصر '{asset_name}' غير موجود"

    max_lvl = asset.get("max_level", MAX_LEVEL)
    if from_level >= max_lvl:
        return False, f"❌ وصلت للمستوى الأقصى ({max_lvl})"

    row = get_city_asset(city_id, asset["id"], from_level)
    if not row or row["quantity"] < quantity:
        owned = row["quantity"] if row else 0
        return False, f"❌ لديك {owned} وحدة فقط من المستوى {from_level}"

    cost = calc_upgrade_cost(asset, from_level, quantity)
    # ─── apply event discount (leaderboard uses base cost) ───
    final_cost, discount = _apply_asset_discount(cost)
    balance = get_user_balance(user_id)
    if balance < final_cost:
        return False, f"❌ رصيدك {balance:.0f} {CURRENCY_ARABIC_NAME} — تحتاج {final_cost:.0f} {CURRENCY_ARABIC_NAME}"

    if not deduct_user_balance(user_id, final_cost):
        return False, "❌ فشل خصم الرصيد"

    upgrade_city_asset(city_id, asset["id"], from_level, quantity)
    # log and track BASE cost so leaderboards are unaffected by event discounts
    log_asset_action(city_id, user_id, asset["id"], "upgrade",
                     quantity, from_level, from_level + 1, cost)
    _record_spending(city_id, cost)

    event_line = f"🎯 خصم الحدث: -{discount*100:.0f}%\n💡 الخصم: -{cost - final_cost:.0f} {CURRENCY_ARABIC_NAME}\n" if discount > 0 else ""
    return True, (
        f"⬆️ تمت ترقية {quantity} × {asset['emoji']} {asset['name_ar']}\n"
        f"المستوى: {from_level} → {from_level + 1}\n"
        f"🪖 السعر الأصلي: {cost:.0f} {CURRENCY_ARABIC_NAME}\n"
        f"{event_line}"
        f"✔ المدفوع الفعلي: {final_cost:.0f} {CURRENCY_ARABIC_NAME}\n"
        f"💰 الرصيد المتبقي: {balance - final_cost:.0f} {CURRENCY_ARABIC_NAME}"
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
