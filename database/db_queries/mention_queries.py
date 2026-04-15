# database/db_queries/mention_queries.py

from ..connection import get_db_conn, db_write
from .groups_queries import get_internal_group_id
import sqlite3


def add_updated_at_column():
    """Add updated_at column to group_members table if it doesn't exist."""
    def _write():
        conn = get_db_conn()
        cursor = conn.cursor()
        
        # Check if column exists first
        cursor.execute("PRAGMA table_info(group_members)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'updated_at' not in columns:
            try:
                # Add column with NULL default first
                cursor.execute("ALTER TABLE group_members ADD COLUMN updated_at INTEGER")
                
                # Update existing rows to have current timestamp
                cursor.execute("UPDATE group_members SET updated_at = strftime('%s','now') WHERE updated_at IS NULL")
                
                print("✅ Added updated_at column to group_members table")
            except Exception as e:
                print(f"❌ Failed to add updated_at column: {e}")
        else:
            print("✅ updated_at column already exists in group_members table")
        
        conn.commit()
    
    db_write(_write)


def update_member_activity(tg_group_id: int, user_id: int):
    """Update the updated_at timestamp for a member's activity."""
    internal_id = get_internal_group_id(tg_group_id)
    if not internal_id:
        return
    
    def _write():
        conn = get_db_conn()
        cursor = conn.cursor()
        
        # First ensure the member exists and has updated_at column
        cursor.execute(
            """
            UPDATE group_members 
            SET updated_at = strftime('%s','now') 
            WHERE user_id = ? AND group_id = ?
            """,
            (user_id, internal_id)
        )
        
        # If no rows were updated, the member might not exist yet
        if cursor.rowcount == 0:
            # Try to insert/update the member with current timestamp
            cursor.execute(
                """
                INSERT INTO group_members (user_id, group_id, messages_count, is_active, updated_at)
                VALUES (?, ?, 1, 1, strftime('%s','now'))
                ON CONFLICT(user_id, group_id) DO UPDATE SET
                    updated_at = strftime('%s','now'),
                    is_active = 1
                """,
                (user_id, internal_id)
            )
        
        conn.commit()
    
    db_write(_write)


def get_active_members(tg_group_id: int, limit: int = None) -> list:
    """
    Get active members from a group, ordered by latest activity first.
    Returns list of dicts with user info.
    """
    internal_id = get_internal_group_id(tg_group_id)
    if not internal_id:
        return []
    
    conn = get_db_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = """
    SELECT u.user_id, u.name, u.username, gm.updated_at
    FROM group_members gm
    JOIN users u ON gm.user_id = u.user_id
    WHERE gm.group_id = ? AND gm.is_active = 1
    ORDER BY gm.updated_at DESC
    """
    
    params = [internal_id]
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    return [dict(row) for row in rows]