# modules/country/services/country_service.py

import sqlite3
from database.connection import get_db_conn
from database.db_queries.countries_queries import (
    country_exists,
    create_country,
    get_country_by_user,
    get_country_stats,
    update_country_stats
)
from database.db_queries.bank_queries import get_user_balance, deduct_user_balance
from database.db_queries.cities_queries import get_cities_by_country
from modules.country.models.country_model import Country
from modules.country.services.city_service import CityService

COUNTRY_CREATION_COST = 100.0


class CountryService:

    # =====================================
    # 🌍 إنشاء دولة جديدة من نص
    # =====================================
    @staticmethod
    def create_country_from_text(user_id: int, text: str):
        if not isinstance(text, str):
            return False, "❌ تنسيق الأمر غير صالح"

        normalized = text.strip()

        # استخراج اسم الدولة
        if normalized.startswith(("إنشاء دولة", "انشاء دولة")):
            country_name = normalized.replace("إنشاء دولة", "").replace("انشاء دولة", "").strip()
        elif normalized.lower().startswith("create country"):
            country_name = normalized[len("create country"):].strip()
        else:
            return False, "❌ الأمر غير مدعوم"

        if not country_name:
            return False, "❌ يرجى كتابة اسم الدولة"

        if country_exists(country_name):
            return False, "❌ اسم الدولة مستخدم"

        existing_country = get_country_by_user(user_id)
        if existing_country:
            return False, f"❌ لديك دولة بالفعل: {existing_country['name']}"

        user_balance = get_user_balance(user_id)
        if user_balance < COUNTRY_CREATION_COST:
            return False, "❌ رصيدك غير كافٍ لإنشاء الدولة"

        if not deduct_user_balance(user_id, COUNTRY_CREATION_COST):
            return False, "❌ فشل خصم الرصيد"

        country_id = create_country(country_name, user_id)
        if not country_id:
            return False, "❌ فشل إنشاء الدولة"

        # إنشاء مدينة تلقائية بنفس اسم الدولة
        from database.db_queries.cities_queries import create_city
        create_city(country_name, user_id, country_id)

        return True, f"🌍 تم إنشاء دولة {country_name} بنجاح\n🏙 وتم إنشاء مدينة {country_name} تلقائياً"

    # =====================================
    # ⬆️ تحديث إحصائيات الدولة بناءً على المدن
    # =====================================
    @staticmethod
    def update_country_stats(country_id: int):
        stats = {
            "economy_score": 0,
            "health_level": 0,
            "education_level": 0,
            "military_power": 0,
            "infrastructure_level": 0
        }

        cities = get_cities_by_country(country_id)
        for city in cities:
            city_stats = CityService.get_city_stats(city['id'])
            for key in stats:
                stats[key] += city_stats.get(key, 0)

        update_country_stats(country_id, **stats)
        return True

    # =====================================
    # 💰 حساب اقتصاد الدولة (دخل وصيانة)
    # =====================================
    @staticmethod
    def calculate_economy(country_id: int):
        total_income = 0
        total_maintenance = 0

        cities = get_cities_by_country(country_id)
        for city in cities:
            econ = CityService.get_city_economy(city['id'])
            total_income += econ.get("income", 0)
            total_maintenance += econ.get("maintenance", 0)

        return {"income": total_income, "maintenance": total_maintenance}

    # =====================================
    # 💵 تحديث ميزانية الدولة بناءً على المدن
    # =====================================
    @staticmethod
    def update_budget(country_id: int):
        conn = get_db_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cities = get_cities_by_country(country_id)
        total_budget = 0
        for city in cities:
            cursor.execute('SELECT current_budget FROM city_budget WHERE city_id=?', (city['id'],))
            row = cursor.fetchone()
            if row:
                total_budget += row['current_budget']
        return total_budget

    # =====================================
    # 📦 جلب بيانات الدولة مع المدن التابعة
    # =====================================
    @staticmethod
    def get_country_details(country_id: int):
        country = Country.get_by_id(country_id)
        if not country:
            return None

        stats = get_country_stats(country_id)
        economy = CountryService.calculate_economy(country_id)

        cities = get_cities_by_country(country_id)

        return {
            "id": country.id,
            "name": country.name,
            "owner_id": country.owner_id,
            "stats": stats,
            "economy": economy,
            "cities": [{"id": c['id'], "name": c['name']} for c in cities]
        }

    # =====================================
    # 👤 جلب بيانات الدولة الخاصة بالمستخدم
    # =====================================
    @staticmethod
    def get_user_country_info(user_id: int):
        country = get_country_by_user(user_id)
        if not country:
            return None
        return {
            "id": country["id"],
            "name": country["name"],
            "economy_score": country.get("economy_score", 0),
            "health_level": country.get("health_level", 0),
            "education_level": country.get("education_level", 0),
            "military_power": country.get("military_power", 0),
            "infrastructure_level": country.get("infrastructure_level", 0)
        }

    # =====================================
    # 🏙 جلب المدن التابعة للدولة
    # =====================================
    @staticmethod
    def get_country_cities(country_id: int):
        return get_cities_by_country(country_id)