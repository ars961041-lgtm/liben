from ..connection import get_db_conn

def create_economy_tables():
    conn = get_db_conn()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS economy_stats (
        name TEXT PRIMARY KEY,
        value TEXT DEFAULT '0.0',
        last_updated INTEGER
    );
    ''')
    
    conn.commit()