import os
from core.config import DB_NAME, IS_TEST
from database.db_schema import create_all_tables

def reset_database():
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"🗑️ قاعدة البيانات {'التجريبية' if IS_TEST else 'الأساسية'} تم حذفها: {DB_NAME}")
    else:
        print(f"⚠️ لم يتم العثور على قاعدة بيانات {'التجريبية' if IS_TEST else 'الأساسية'}: {DB_NAME}")

    create_all_tables()
    print(f"🚀 تم إنشاء جميع الجداول من جديد في قاعدة البيانات {'التجريبية' if IS_TEST else 'الأساسية'}!")

if __name__ == "__main__":
    reset_database()
