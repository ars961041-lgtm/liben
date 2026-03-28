# database/update_db.py
from core.config import DB_NAME
from database.connection import get_db_conn

def update_database():
    """
    هنا ضع أي تحديثات للقاعدة (ALTER TABLE, INSERT, UPDATE, إلخ)
    مثال بسيط لإضافة عمود إذا لم يكن موجود:
    """
    conn = get_db_conn()
    cursor = conn.cursor()

    try:
        # # مثال: إضافة عمود جديد إذا لم يكن موجود
        # cursor.execute(f"""
        #     ALTER TABLE IF EXISTS users
        #     ADD COLUMN last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        # """)
        print('update_database')
    except Exception:
        pass  # يتجاهل إذا العمود موجود

    conn.commit()
