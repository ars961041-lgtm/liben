# modules/country/services/city_service.py

from database.connection import get_db_conn
from database.db_queries.bank_queries import deduct_user_balance, get_user_balance


class CityService:

    # =====================================
    # 🏗 شراء أصل (asset system)
    # =====================================
    @staticmethod
    def buy_building(user_id: int, city_id: int, asset_name: str, quantity: int = 1):
        from modules.city.asset_service import buy_asset
        return buy_asset(user_id, city_id, asset_name, quantity)

    # =====================================
    # ⬆️ ترقية أصل (asset system)
    # =====================================
    @staticmethod
    def upgrade_building(user_id: int, city_id: int, asset_name: str):
        from modules.city.asset_service import upgrade_asset
        return upgrade_asset(user_id, city_id, asset_name, 1, from_level=1)

    # =====================================
    # 📊 إحصائيات المدينة — محسوبة من الأصول
    # =====================================
    @staticmethod
    def get_city_stats(city_id: int) -> dict:
        from database.db_queries.assets_queries import calculate_city_effects
        return calculate_city_effects(city_id)

    # =====================================
    # 💰 اقتصاد المدينة — محسوب من الأصول
    # =====================================
    @staticmethod
    def get_city_economy(city_id: int) -> dict:
        from database.db_queries.assets_queries import calculate_city_effects
        effects = calculate_city_effects(city_id)
        return {
            "income":      effects.get("income", 0),
            "maintenance": effects.get("maintenance", 0),
        }

    # =====================================
    # 🧹 إعادة تعيين المدينة
    # =====================================
    @staticmethod
    def reset_city(city_id: int) -> bool:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM city_assets  WHERE city_id = ?", (city_id,))
        cursor.execute("DELETE FROM city_aspects WHERE city_id = ?", (city_id,))
        cursor.execute(
            "UPDATE city_budget SET current_budget=0, income_per_hour=0, expense_per_hour=0 "
            "WHERE city_id = ?", (city_id,)
        )
        cursor.execute(
            "UPDATE city_spending SET total_spent=0 WHERE city_id = ?", (city_id,)
        )
        conn.commit()
        return True

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
        from database.db_queries.assets_queries import calculate_city_effects
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, owner_id, country_id FROM cities WHERE id = ?", (city_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        effects = calculate_city_effects(city_id)
        return {
            "id":         row["id"],
            "name":       row["name"],
            "owner_id":   row["owner_id"],
            "country_id": row["country_id"],
            "stats":      effects,  # economy, health, education, military, infrastructure, income, maintenance
            "economy":    effects,  # backward compat
        }
