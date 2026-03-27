from .users import create_users_table
from .groups import create_groups_tables
from .countries import create_countries_tables
from .facilities import create_facilities_tables
from .cities import create_cities_tables
from .buildings import create_buildings_table
from .economy import create_economy_tables
from .banks import create_banks_table

def create_all_tables():
    # 1️⃣ المستخدمين والحسابات
    create_users_table()
    create_banks_table()

    # 2️⃣ المجموعات
    create_groups_tables()

    # 3️⃣ القطاعات وأنواع المنشآت
    create_facilities_tables()

    # 4️⃣ الدول
    create_countries_tables()

    # 5️⃣ المدن والمرافق والميزانية والوحدات العسكرية
    create_cities_tables()

    # 6️⃣ المباني
    create_buildings_table()

    # 7️⃣ الاقتصاد العام
    create_economy_tables()

    print("✅ تم إنشاء جميع جداول قاعدة البيانات بنجاح.")