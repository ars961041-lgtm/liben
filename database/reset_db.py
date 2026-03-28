from database.connection import get_db_conn
from database.db_schema import create_all_tables

def reset_database():
    conn = get_db_conn()
    cursor = conn.cursor()

    # 🔥 احذف كل الجداول
    cursor.execute("PRAGMA foreign_keys = OFF")

    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table'
    """)

    tables = cursor.fetchall()

    for table in tables:
        table_name = table[0]

        # تجاهل جداول النظام
        if table_name.startswith("sqlite_"):
            continue

        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            print(f"🗑️ تم حذف الجدول: {table_name}")
        except Exception as e:
            print(f"❌ خطأ في حذف {table_name}:", e)

    cursor.execute("PRAGMA foreign_keys = ON")
    conn.commit()

    # 🔥 إعادة إنشاء الجداول
    create_all_tables()

    print("🚀 تم إعادة إنشاء قاعدة البيانات بالكامل")
