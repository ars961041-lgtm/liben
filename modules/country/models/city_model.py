# models/city_models.py

from database.connection import get_db_conn
from modules.country.services.building_config import get_building_info
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

# -----------------------------
# ⚡️ تمثيل المدينة
# -----------------------------
class City:
    def init(self, city_id, name, owner_id, country_id=None):
        self.id = city_id
        self.name = name
        self.owner_id = owner_id
        self.country_id = country_id

    # -----------------------------
    # جلب المباني التابعة للمدينة
    # -----------------------------
    def get_buildings(self):
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, building_type, quantity, level FROM buildings WHERE city_id=?',
            (self.id,)
        )
        return cursor.fetchall()

    # -----------------------------
    # التحقق قبل شراء مبنى
    # -----------------------------
    def can_purchase_building(self, building_type, quantity, user_balance):
        config = get_building_info(building_type)
        if not config:
            return False, "❌ هذا المبنى غير موجود"
        total_cost = config.get("price", 0) * quantity
        if user_balance < total_cost:
            return False, f"❌ رصيدك غير كافي ({total_cost} {CURRENCY_ARABIC_NAME} مطلوب)"
        return True, total_cost

    # -----------------------------
    # شراء مبنى جديد أو إضافة كمية
    # -----------------------------
    def add_building(self, building_type, quantity=1):
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, quantity, level FROM buildings WHERE city_id=? AND building_type=?',
            (self.id, building_type)
        )
        row = cursor.fetchone()

        config = get_building_info(building_type)
        if not config:
            return False, "❌ هذا المبنى غير موجود"

        if row:
            new_qty = row['quantity'] + quantity
            cursor.execute(
                'UPDATE buildings SET quantity=? WHERE id=?',
                (new_qty, row['id'])
            )
        else:
            cursor.execute(
                'INSERT INTO buildings (city_id, building_type, quantity, level) VALUES (?, ?, ?, 1)',
                (self.id, building_type, quantity)
            )
        conn.commit()
        return True, f"✅ تم شراء {quantity} {config['emoji']} {config['name_ar']}"

    # -----------------------------
    # التحقق قبل ترقية مبنى
    # -----------------------------
    def can_upgrade_building(self, building_type):
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, quantity, level FROM buildings WHERE city_id=? AND building_type=?',
            (self.id, building_type)
        )
        row = cursor.fetchone()
        if not row:
            return False, "❌ لا يوجد هذا المبنى في المدينة"

        config = get_building_info(building_type)
        if not config:
            return False, "❌ بيانات المبنى غير موجودة"

        # مثال: التحقق من رصيد المستخدم قبل الترقية يمكن إضافته هنا
        # total_cost = config.get("upgrade_price", 100)
        # if user_balance < total_cost:
        #     return False, f"❌ رصيدك غير كافي لترقية المبنى ({total_cost} {CURRENCY_ARABIC_NAME} مطلوب)"

        return True, row['level']

    # -----------------------------
    # ترقية مبنى موجود
    # -----------------------------
    def upgrade_building(self, building_type):
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, quantity, level FROM buildings WHERE city_id=? AND building_type=?',
            (self.id, building_type)
        )
        row = cursor.fetchone()
        if not row:
            return False, "❌ لا يوجد هذا المبنى في المدينة"

        new_level = row['level'] + 1
        cursor.execute(
            'UPDATE buildings SET level=? WHERE id=?',
            (new_level, row['id'])
        )
        conn.commit()

        config = get_building_info(building_type)
        return True, f"⬆️ تم تطوير {config['name_ar']} إلى مستوى {new_level}"
    
# -----------------------------
    # حساب إحصائيات المدينة
    # -----------------------------
    def calculate_stats(self):
        buildings = self.get_buildings()
        stats = {
            "economy_score": 0,
            "health_level": 0,
            "education_level": 0,
            "military_power": 0,
            "infrastructure_level": 0
        }

        for b in buildings:
            config = get_building_info(b['building_type'])
            if not config:
                continue
            for stat, value in config["stat_impact"].items():
                effect = (b['quantity'] * b['level']) ** 0.8
                stats[stat] += effect * value

        return stats

    # -----------------------------
    # حساب الدخل والصيانة للمدينة
    # -----------------------------
    def calculate_economy(self):
        buildings = self.get_buildings()
        total_income = 0
        total_maintenance = 0
        for b in buildings:
            config = get_building_info(b['building_type'])
            if not config:
                continue
            total_income += config.get("income", 0) * b['quantity']
            total_maintenance += config.get("maintenance_cost", 0) * b['quantity'] * b['level']
        return {
            "income": total_income,
            "maintenance": total_maintenance
        }