from database.connection import get_db_conn

def create_daily_tasks_pool_table():
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # ───── جدول مهام عامة ─────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_tasks_pool (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,               -- نوع المهمة: upgrade_asset / buy_troops / buy_equipment / upgrade_city_level
        description TEXT NOT NULL UNIQUE, -- وصف المهمة + شرط عدم التكرار
        asset_id INTEGER,                 -- إذا كانت مهمة تتعلق بمؤسسة معينة
        troop_type_id INTEGER,            -- إذا كانت مهمة تتعلق بجنود
        equipment_type_id INTEGER,        -- إذا كانت مهمة تتعلق بمعدات
        required_level INTEGER,           -- مستوى مطلوب للمدينة أو للأصل
        required_quantity INTEGER         -- عدد الجنود أو المعدات المطلوبة
    )
    """)
    
    # ───── جدول مهام كل مستخدم يومية ─────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        city_id INTEGER NOT NULL,
        task_data TEXT NOT NULL,
        assigned_at INTEGER DEFAULT (strftime('%s','now')),
        completed INTEGER DEFAULT 0,
        reward_collected INTEGER DEFAULT 0,
        UNIQUE(user_id, task_data)          -- يمنع تكرار نفس المهمة لنفس المستخدم
    )
    """)
    
    conn.commit()
    _seed_daily_tasks_pool()
# ───── المهام العشوائية ─────
def _seed_daily_tasks_pool():
    conn = get_db_conn()
    cursor = conn.cursor()

    tasks = [
        # ───── الصحة ─────
        ("upgrade_asset", "رفع مستوى مستشفى إلى 2", 1, None, None, 2, None),
        ("upgrade_asset", "رفع مستوى عيادة إلى 2", 2, None, None, 2, None),
        ("upgrade_asset", "رفع مستوى صيدلية إلى 3", 3, None, None, 3, None),
        ("upgrade_asset", "رفع مستوى مختبر طبي إلى 3", 4, None, None, 3, None),
        ("upgrade_asset", "رفع مستوى مركز إسعاف إلى 2", 5, None, None, 2, None),
        ("upgrade_asset", "رفع مستوى مركز أبحاث طبية إلى 3", 6, None, None, 3, None),
        ("upgrade_asset", "رفع مستوى مركز صحي إلى 2", 7, None, None, 2, None),

        # ───── التعليم ─────
        ("upgrade_asset", "رفع مستوى مدرسة إلى 2", 8, None, None, 2, None),
        ("upgrade_asset", "رفع مستوى جامعة إلى 3", 9, None, None, 3, None),
        ("upgrade_asset", "رفع مستوى روضة إلى 2", 10, None, None, 2, None),
        ("upgrade_asset", "رفع مستوى معهد إلى 2", 11, None, None, 2, None),
        ("upgrade_asset", "رفع مستوى مركز أبحاث إلى 3", 12, None, None, 3, None),
        ("upgrade_asset", "رفع مستوى مكتبة إلى 2", 13, None, None, 2, None),
        ("upgrade_asset", "رفع مستوى مركز تدريب إلى 2", 14, None, None, 2, None),

        # ───── الاقتصاد ─────
        ("upgrade_asset", "رفع مستوى مصنع إلى 3", 15, None, None, 3, None),
        ("upgrade_asset", "رفع مستوى بنك محلي إلى 2", 16, None, None, 2, None),
        ("upgrade_asset", "رفع مستوى سوق تجاري إلى 2", 17, None, None, 2, None),
        ("upgrade_asset", "رفع مستوى شركة تقنية إلى 3", 18, None, None, 3, None),
        ("upgrade_asset", "رفع مستوى شركة لوجستية إلى 2", 19, None, None, 2, None),
        ("upgrade_asset", "رفع مستوى شركة تأمين إلى 2", 20, None, None, 2, None),
        ("upgrade_asset", "رفع مستوى مول إلى 3", 21, None, None, 3, None),
        ("upgrade_asset", "رفع مستوى ميناء إلى 3", 22, None, None, 3, None),
        ("upgrade_asset", "رفع مستوى مركز بيانات إلى 3", 23, None, None, 3, None),
        ("upgrade_asset", "رفع مستوى شركة إعلام إلى 2", 24, None, None, 2, None),
        ("upgrade_asset", "رفع مستوى فندق إلى 2", 25, None, None, 2, None),
        ("upgrade_asset", "رفع مستوى شركة سياحة إلى 2", 26, None, None, 2, None),

        # ───── البنية التحتية ─────
        ("upgrade_asset", "رفع مستوى بنية تحتية إلى 2", 27, None, None, 2, None),
        ("upgrade_asset", "رفع مستوى محطة طاقة إلى 2", 28, None, None, 2, None),
        ("upgrade_asset", "رفع مستوى مطار إلى 3", 29, None, None, 3, None),
        ("upgrade_asset", "رفع مستوى سكة حديد إلى 2", 30, None, None, 2, None),
        ("upgrade_asset", "رفع مستوى طاقة شمسية إلى 2", 31, None, None, 2, None),
        ("upgrade_asset", "رفع مستوى طاقة رياح إلى 2", 32, None, None, 2, None),
        ("upgrade_asset", "رفع مستوى محطة مياه إلى 2", 33, None, None, 2, None),
        ("upgrade_asset", "رفع مستوى شركة مقاولات إلى 2", 34, None, None, 2, None),

        # ───── الجنود ─────
        ("buy_troops", "شراء 10 مشاة", None, 1, None, None, 10),
        ("buy_troops", "شراء 5 فرسان", None, 3, None, None, 5),
        ("buy_troops", "شراء 3 قوات خاصة", None, 4, None, None, 3),
        ("buy_troops", "شراء 7 رماة", None, 2, None, None, 7),

        # ───── المعدات ─────
        ("buy_equipment", "شراء 2 دبابة", None, None, 6, None, 2),
        ("buy_equipment", "شراء 1 مدفعية", None, None, 7, None, 1),
        ("buy_equipment", "شراء 3 طائرة بدون طيار", None, None, 8, None, 3),
        ("buy_equipment", "شراء 1 هليكوبتر هجوم", None, None, 9, None, 1),

        # ───── ترقية المدينة ─────
        ("upgrade_city_level", "رفع مستوى المدينة إلى 2", None, None, None, 2, None),
        ("upgrade_city_level", "رفع مستوى المدينة إلى 3", None, None, None, 3, None),
        ("upgrade_city_level", "رفع مستوى المدينة إلى 4", None, None, None, 4, None),
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO daily_tasks_pool
        (type, description, asset_id, troop_type_id, equipment_type_id, required_level, required_quantity)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, tasks)
    
    conn.commit()
