from database.connection import get_db_conn
from core.config import developers_id
from database.db_queries.bank_queries import deduct_user_balance, get_user_balance

# Service for managing buildings and economic systems
from database.db_queries.countries_queries import (
    country_exists,
    create_country,
    get_country_stats,
    get_user_country_name,
    update_country_stats,
    get_country_budget,
)

from modules.country.services.building_config import get_building_info, calculate_upgrade_cost

COUNTRY_CREATION_COST = 100.0

class CountryService:

    @staticmethod
    def buy_building(user_id, country_id, building_type, quantity, cost_per_unit):
        total_cost = quantity * cost_per_unit
        if not deduct_user_balance(user_id, total_cost):
            return False, "Insufficient balance."

        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT id, quantity FROM buildings WHERE user_id = ? AND country_id = ? AND building_type = ?',
                        (user_id, country_id, building_type))
        row = cursor.fetchone()

        if row:
            new_quantity = row['quantity'] + quantity
            cursor.execute('UPDATE buildings SET quantity = ? WHERE id = ?', (new_quantity, row['id']))
        else:
            cursor.execute('INSERT INTO buildings (user_id, country_id, building_type, quantity) VALUES (?, ?, ?, ?)',
                            (user_id, country_id, building_type, quantity))
        conn.commit()
        return True, "Building purchased successfully."

    @staticmethod
    def upgrade_building(user_id, country_id, building_type, quantity, upgrade_cost_per_level):
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT id, quantity, level FROM buildings WHERE user_id = ? AND country_id = ? AND building_type = ?',
                        (user_id, country_id, building_type))
        row = cursor.fetchone()

        if not row or row['quantity'] < quantity:
            return False, "Not enough buildings to upgrade."

        total_cost = quantity * upgrade_cost_per_level
        if not deduct_user_balance(user_id, total_cost):
            return False, "Insufficient balance."

        new_level = row['level'] + 1
        cursor.execute('UPDATE buildings SET level = ? WHERE id = ?', (new_level, row['id']))
        conn.commit()
        
        return True, "Buildings upgraded successfully."

    @staticmethod
    def calculate_maintenance_cost(country_id):
            conn = get_db_conn()
            cursor = conn.cursor()
            cursor.execute('SELECT building_type, quantity, level FROM buildings WHERE country_id = ?', (country_id,))
            buildings = cursor.fetchall()

            total_cost = 0
            for building in buildings:
                base_cost = 100  # Example base cost per building
                scaling_factor = 1.2  # Example scaling factor per level
                total_cost += building['quantity'] * base_cost * (scaling_factor ** (building['level'] - 1))

            return total_cost

    @staticmethod
    def update_country_stats(country_id):
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT building_type, quantity, level FROM buildings WHERE country_id = ?', (country_id,))
        buildings = cursor.fetchall()

        stats = {
            'economy_score': 0,
            'health_level': 0,
            'education_level': 0,
            'military_power': 0,
            'infrastructure_level': 0
        }

        for building in buildings:
            if building['building_type'] == 'hospital':
                stats['health_level'] += building['quantity'] * building['level']
            elif building['building_type'] == 'school':
                stats['education_level'] += building['quantity'] * building['level']
            elif building['building_type'] == 'factory':
                stats['economy_score'] += building['quantity'] * building['level']
            elif building['building_type'] == 'military':
                stats['military_power'] += building['quantity'] * building['level']
            elif building['building_type'] == 'infrastructure':
                stats['infrastructure_level'] += building['quantity'] * building['level']

        update_country_stats(country_id, **stats)
        return True
    
    ### ------------------------------------------------------------------------------------------------------

    # 🏗️ شراء مبنى
    @staticmethod
    def buy_building(user_id, country_id, building_type, quantity):
        config = get_building_info(building_type)
        if not config:
            return False, "❌ مبنى غير معروف"

        total_cost = config["base_cost"] * quantity

        if not deduct_user_balance(user_id, total_cost):
            return False, "❌ رصيدك لا يكفي"

        conn = get_db_conn()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT id, quantity, level FROM buildings WHERE user_id=? AND country_id=? AND building_type=?',
            (user_id, country_id, building_type)
        )
        row = cursor.fetchone()

        if row:
            new_qty = row['quantity'] + quantity
            cursor.execute(
                'UPDATE buildings SET quantity=? WHERE id=?',
                (new_qty, row['id'])
            )
        else:
            cursor.execute(
                'INSERT INTO buildings (user_id, country_id, building_type, quantity, level) VALUES (?, ?, ?, ?, 1)',
                (user_id, country_id, building_type, quantity)
            )

        conn.commit()

        CountryService.update_country_stats(country_id)

        return True, f"✅ اشتريت {quantity} {config['emoji']} {config['name_ar']}"

    # ⬆️ تطوير
    @staticmethod
    def upgrade_building(user_id, country_id, building_type, quantity):

        config = get_building_info(building_type)

        conn = get_db_conn()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT id, quantity, level FROM buildings WHERE user_id=? AND country_id=? AND building_type=?',
            (user_id, country_id, building_type)
        )
        row = cursor.fetchone()

        if not row:
            return False, "❌ لا تملك هذا المبنى"

        current_level = row['level']

        if current_level >= 10:
            return False, "❌ وصلت لأقصى مستوى"

        cost = calculate_upgrade_cost(
            config["base_cost"],
            current_level,
            config["cost_scale"],
            current_level + 1
        ) * quantity

        if not deduct_user_balance(user_id, cost):
            return False, "❌ رصيدك لا يكفي"

        cursor.execute(
            'UPDATE buildings SET level=? WHERE id=?',
            (current_level + 1, row['id'])
        )

        conn.commit()

        CountryService.update_country_stats(country_id)

        return True, f"⬆️ تم تطوير {config['name_ar']} إلى مستوى {current_level+1}"

    # 📊 تحديث الإحصائيات (ذكي)
    @staticmethod
    def update_country_stats(country_id):

        conn = get_db_conn()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT building_type, quantity, level FROM buildings WHERE country_id=?',
            (country_id,)
        )
        buildings = cursor.fetchall()

        stats = {
            'economy_score': 0,
            'health_level': 0,
            'education_level': 0,
            'military_power': 0,
            'infrastructure_level': 0
        }

        for b in buildings:
            config = get_building_info(b['building_type'])
            if not config:
                continue

            for stat, value in config["stat_impact"].items():

                # 🔥 diminishing return
                effect = (b['quantity'] * b['level']) ** 0.8

                stats[stat] += effect * value

        update_country_stats(country_id, **stats)
        return True

    # 💰 حساب الدخل والصيانة
    @staticmethod
    def calculate_economy(country_id):

        conn = get_db_conn()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT building_type, quantity, level FROM buildings WHERE country_id=?',
            (country_id,)
        )
        buildings = cursor.fetchall()

        income = 0
        maintenance = 0

        for b in buildings:
            config = get_building_info(b['building_type'])

            if not config:
                continue

            income += config["income"] * b['quantity']
            maintenance += config["maintenance_cost"] * b['quantity'] * b['level']

        return income, maintenance

    # 🔄 تحديث الميزانية
    @staticmethod
    def update_budget(country_id):
        pass
    
    @staticmethod
    def create_country_from_text(user_id, text):


        if not isinstance(text, str):
            return False, "تنسيق الأمر غير صالح"

        normalized = text.strip()

        if normalized.startswith("إنشاء دولة") or normalized.startswith("انشاء دولة"):
            country_name = normalized.replace("إنشاء دولة", "").replace("انشاء دولة", "").strip()

        elif normalized.lower().startswith("create country"):
            country_name = normalized[len("create country"):].strip()

        else:
            return False, "الأمر غير مدعوم"

        if not country_name:
            return False, "يرجى كتابة اسم الدولة"

        # تحقق الاسم
        if country_exists(country_name):
            return False, "اسم الدولة مستخدم"

        # هل يملك دولة
        existing_country = get_user_country_name(user_id)

        if existing_country:
            return False, f"لديك دولة بالفعل: {existing_country}"

        # تحقق الرصيد
        user_balance = get_user_balance(user_id)

        if user_balance < COUNTRY_CREATION_COST:
            return False, "رصيد غير كافٍ لإنشاء الدولة"

        # خصم المال
        success = deduct_user_balance(user_id, COUNTRY_CREATION_COST)

        if not success:
            return False, "فشل خصم الرصيد"

        # إنشاء الدولة
        country_id = create_country(country_name, user_id)

        if not country_id:
            return False, "فشل إنشاء الدولة"

        return True, f"🌍 تم إنشاء دولة {country_name} بنجاح"