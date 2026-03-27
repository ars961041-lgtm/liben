from ..connection import get_db_conn

def get_country_buildings(country_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM buildings WHERE country_id = ?', (country_id,))
    return cursor.fetchall()

def add_or_update_building(user_id, country_id, building_type, quantity_change, level_change=0):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT id, quantity, level FROM buildings WHERE country_id = ? AND building_type = ?',
                    (country_id, building_type))
    row = cursor.fetchone()
    if row:
        new_qty = row[1] + quantity_change
        new_lvl = row[2] + level_change
        cursor.execute('UPDATE buildings SET quantity = ?, level = ? WHERE id = ?', (new_qty, new_lvl, row[0]))
    else:
        cursor.execute('INSERT INTO buildings (user_id, country_id, building_type, quantity, level) VALUES (?, ?, ?, ?, ?)',
                        (user_id, country_id, building_type, quantity_change, 1 + level_change))
    conn.commit()