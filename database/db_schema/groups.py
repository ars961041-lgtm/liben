from ..connection import get_db_conn

# ── أسماء الميزات وقيمها الافتراضية ──
FEATURES = {
    "feat_games":       1,   # 🎮 الألعاب (بنك، دول، حرب، تحالفات، ألعاب ترفيهية)
    "feat_admin":       1,   # 🛠 أدوات الإدارة (كتم، حظر، ترقية)
    "feat_replies":     1,   # 💬 الردود التلقائية
    "feat_media":       1,   # 🎨 الوسائط والملصقات (أوامر الوسائط)
    "feat_welcome":     1,   # 👋 رسائل الترحيب
    "feat_profile":     1,   # 👤 الملف الشخصي (عني/عنه)
    "feat_media_lock":  0,   # 🔒 تعطيل الوسائط — 1=يحذف وسائط غير المشرفين
}

def create_groups_tables():
    conn = get_db_conn()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        feat_games   INTEGER NOT NULL DEFAULT 1,
        feat_admin   INTEGER NOT NULL DEFAULT 1,
        feat_replies INTEGER NOT NULL DEFAULT 1,
        feat_media   INTEGER NOT NULL DEFAULT 1,
        feat_welcome INTEGER NOT NULL DEFAULT 1,
        feat_profile INTEGER NOT NULL DEFAULT 1,
        feat_media_lock INTEGER NOT NULL DEFAULT 0
    );
    ''')

    # إضافة الأعمدة لقواعد البيانات الموجودة (migration آمن)
    for col, default in FEATURES.items():
        try:
            cursor.execute(
                f"ALTER TABLE groups ADD COLUMN {col} INTEGER NOT NULL DEFAULT {default}"
            )
        except Exception:
            pass  # العمود موجود مسبقاً
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS group_members (
        user_id INTEGER NOT NULL,
        group_id INTEGER NOT NULL,
        messages_count INTEGER DEFAULT 0,
        is_muted INTEGER DEFAULT 0,
        is_restricted INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, group_id),
        FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
    );
    ''')
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_group_members_group_msg
    ON group_members(group_id, messages_count DESC);
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_group_members_user_group
    ON group_members(user_id, group_id);
    """)
    
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS group_punishment_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        action_type TINYINT NOT NULL, -- 0=حظر, 1=كتم, 2=تقييد, ... 
        executor_id INTEGER NOT NULL, -- الشخص الذي نفذ العقوبة
        timestamp INTEGER NOT NULL DEFAULT (strftime('%s','now')));
    """)
    
    conn.commit()