from ..connection import get_db_conn
import time

def get_economy_stat(name, default=0.0):
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM economy_stats WHERE name = ?', (name,))
        row = cursor.fetchone()
        if row:
            try:
                return float(row[0])
            except ValueError:
                return row[0]
        return default

def set_economy_stat(name, value):
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO economy_stats (name, value, last_updated)
            VALUES (?, ?, ?)
            ON CONFLICT(name)
            DO UPDATE SET
            value=excluded.value,
            last_updated=excluded.last_updated
            ''',
            (name, str(value), int(time.time()))
        )
        conn.commit()


