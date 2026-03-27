from ..connection import get_db_conn

def create_groups_tables():
    conn = get_db_conn()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL
    );
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS group_members (
        user_id INTEGER NOT NULL,
        group_id INTEGER NOT NULL,
        message_count INTEGER DEFAULT 0,
        is_muted INTEGER DEFAULT 0,
        is_restricted INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, group_id),
        FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
    );
    ''')
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_group_members_group_msg
    ON group_members(group_id, message_count DESC);
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_group_members_user_group
    ON group_members(user_id, group_id);
    """)
    
    conn.commit()