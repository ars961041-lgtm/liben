# database/reset_db.py
from core.config import DB_NAME
from database.connection import close_db_conn
from database.db_schema import create_all_tables
import os

def reset_database():
    """تعيد إنشاء قاعدة البيانات كاملة"""
    # اغلق الاتصال الحالي
    close_db_conn()

    # احذف الملف القديم إذا موجود
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

    # أنشئ جميع الجداول من جديد
    create_all_tables()