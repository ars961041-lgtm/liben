# modules/country/services/city_service.py

from database.connection import get_db_conn
from database.db_queries.bank_queries import deduct_user_balance, get_user_balance
from database.db_queries.building_queries import (
    buy_building as db_buy_building,
    upgrade_building as db_upgrade_building,
    calculate_city_stats,
    calculate_city_economy,
    delete_all_buildings
)
from modules.country.models.city_model import City
from modules.country.services.building_config import get_building_info, calculate_upgrade_cost


class CityService:

    # =====================================
    # 🏗 شراء مبنى
    # =====================================
    @staticmethod
    def buy_building(user_id: int, city_id: int, building_type: str, quantity: int = 1):
        config = get_building_info(building_type)
        if not config:
            return False, "❌ هذا المبنى غير معروف."

        total_cost = config['base_cost'] * quantity
        user_balance = get_user_balance(user_id)
        if user_balance < total_cost:
            return False, f"❌ تحتاج {total_cost} 💰 ورصيدك {user_balance}"

        # خصم الرصيد
        if not deduct_user_balance(user_id, total_cost):
            return False, "❌ فشل خصم الرصيد."

        # تنفيذ الشراء في قاعدة البيانات
        success, msg = db_buy_building(city_id, building_type, quantity)
        return success, msg

    # =====================================
    # ⬆️ تطوير مبنى
    # =====================================
    @staticmethod
    def upgrade_building(user_id: int, city_id: int, building_type: str):
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, level, quantity FROM buildings WHERE city_id=? AND building_type=?',
            (city_id, building_type)
        )
        row = cursor.fetchone()

        if not row:
            return False, "❌ لا تمتلك هذا المبنى."

        current_level = row['level']
        quantity = row['quantity']

        if current_level >= 10:
            return False, "❌ وصلت لأقصى مستوى."

        config = get_building_info(building_type)
        if not config:
            return False, "❌ مبنى غير معروف."

        # حساب تكلفة الترقية للمستوى التالي
        upgrade_cost_per_building = calculate_upgrade_cost(
            config['base_cost'],
            current_level,
            config['cost_scale'],
            current_level + 1
        )

        total_cost = upgrade_cost_per_building * quantity
        user_balance = get_user_balance(user_id)
        if user_balance < total_cost:
            return False, f"❌ تحتاج {total_cost} 💰 ورصيدك {user_balance}"

        # خصم الرصيد
        if not deduct_user_balance(user_id, total_cost):
            return False, "❌ فشل خصم الرصيد."

        # تنفيذ الترقية
        success, msg = db_upgrade_building(city_id, building_type)
        return success, msg

    # =====================================
    # 📊 إحصائيات المدينة
    # =====================================
    @staticmethod
    def get_city_stats(city_id: int):
        return calculate_city_stats(city_id)

    # =====================================
    # 💰 اقتصاد المدينة
    # =====================================
    @staticmethod
    def get_city_economy(city_id: int):
        return calculate_city_economy(city_id)

    # =====================================
    # 🧹 إعادة تعيين المباني (للاختبار)
    # =====================================
    @staticmethod
    def reset_city(city_id: int):
        return delete_all_buildings(city_id)

    # =====================================
    # 📦 بيانات المدينة الكاملة
    # =====================================
    @staticmethod
    def get_user_city_id(user_id: int):
        from database.db_queries.cities_queries import get_user_city
        city = get_user_city(user_id)
        return city['id'] if city else None

    @staticmethod
    def get_city_details(city_id: int):
        from database.connection import get_db_conn
        from database.db_queries.assets_queries import calculate_city_effects
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, owner_id, country_id FROM cities WHERE id=?", (city_id,))
        row = cursor.fetchone()
        if not row:
            return None
        effects = calculate_city_effects(city_id)
        return {
            "id":         row["id"],
            "name":       row["name"],
            "owner_id":   row["owner_id"],
            "country_id": row["country_id"],
            "stats":      effects,   # keys: economy, health, education, military, infrastructure, income, maintenance
            "economy":    effects,   # kept for backward compat
        }