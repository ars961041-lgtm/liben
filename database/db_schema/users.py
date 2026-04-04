from ..connection import get_db_conn

def create_users_table():
    conn = get_db_conn()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL UNIQUE,
        city_id    INTEGER DEFAULT NULL,
        country_id INTEGER DEFAULT NULL
    );
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users_name (
        user_id INTEGER NOT NULL UNIQUE,
        name    TEXT    NOT NULL
    );
    ''')
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_users_name_user
    ON users_name(user_id);
    """)
    
    conn.commit()