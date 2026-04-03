
from database.connection import get_db_conn
from modules.country.models.city_model import City

# -----------------------------
# ⚡️ تمثيل الدولة
# -----------------------------
class Country:
    def init(self, country_id, name, owner_id):
        self.id = country_id
        self.name = name
        self.owner_id = owner_id

    # -----------------------------
    # جلب المدن التابعة للدولة
    # -----------------------------
    def get_cities(self):
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, name, owner_id, country_id FROM cities WHERE country_id=?',
            (self.id,)
        )
        rows = cursor.fetchall()
        return [City(row['id'], row['name'], row['owner_id'], row['country_id']) for row in rows]

    # -----------------------------
    # حساب إحصائيات الدولة بناءً على المدن
    # -----------------------------
    def calculate_stats(self):
        stats = {
            "economy_score": 0,
            "health_level": 0,
            "education_level": 0,
            "military_power": 0,
            "infrastructure_level": 0
        }
        for city in self.get_cities():
            city_stats = city.calculate_stats()
            for key in stats:
                stats[key] += city_stats.get(key, 0)
        return stats

    # -----------------------------
    # حساب الدخل والصيانة بناءً على المدن
    # -----------------------------
    def calculate_economy(self):
        total_income = 0
        total_maintenance = 0
        for city in self.get_cities():
            econ = city.calculate_economy()
            total_income += econ.get("income", 0)
            total_maintenance += econ.get("maintenance", 0)
        return {
            "income": total_income,
            "maintenance": total_maintenance
        }

    # -----------------------------
    # تحديث ميزانية الدولة عبر المدن
    # -----------------------------
    def update_budget(self):
        conn = get_db_conn()
        cursor = conn.cursor()
        for city in self.get_cities():
            econ = city.calculate_economy()
            budget = econ['income'] - econ['maintenance']

            cursor.execute('SELECT id FROM city_budget WHERE city_id = ?', (city.id,))
            existing = cursor.fetchone()

            if existing:
                cursor.execute(
                    '''
                    UPDATE city_budget
                    SET current_budget = ?,
                        income_per_hour = ?,
                        expense_per_hour = ?,
                        last_update_time = strftime('%s','now')
                    WHERE city_id = ?
                    ''',
                    (budget, econ['income'], econ['maintenance'], city.id)
                )
            else:
                cursor.execute(
                    '''
                    INSERT INTO city_budget (city_id, current_budget, income_per_hour, expense_per_hour, last_update_time)
                    VALUES (?, ?, ?, ?, strftime('%s','now'))
                    ''',
                    (city.id, budget, econ['income'], econ['maintenance'])
                )
        conn.commit()
        return True