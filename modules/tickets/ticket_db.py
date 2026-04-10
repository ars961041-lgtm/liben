"""
قاعدة بيانات نظام التذاكر
"""
import time
from database.connection import get_db_conn


# ══════════════════════════════════════════
# 🏗️ إنشاء الجداول
# ══════════════════════════════════════════

def create_ticket_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        chat_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        status TEXT DEFAULT 'open',
        dev_group_msg_id INTEGER,
        created_at INTEGER DEFAULT (strftime('%s','now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ticket_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER NOT NULL,
        sender TEXT NOT NULL,
        message_id INTEGER,
        message_type TEXT DEFAULT 'text',
        content TEXT,
        created_at INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (ticket_id) REFERENCES tickets(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ticket_limits (
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        count INTEGER DEFAULT 0,
        last_used INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, date)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_user ON tickets(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticket_msgs ON ticket_messages(ticket_id)")

    conn.commit()


# ══════════════════════════════════════════
# 🎫 التذاكر
# ══════════════════════════════════════════

def create_ticket(user_id, chat_id, category):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tickets (user_id, chat_id, category)
        VALUES (?, ?, ?)
    """, (user_id, chat_id, category))
    conn.commit()
    return cursor.lastrowid


def get_ticket(ticket_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_user_tickets(user_id, page=0, per_page=5):
    """يرجع تذاكر مستخدم محدد مرتبة من الأحدث."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM tickets
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """, (user_id, per_page, page * per_page))
    return [dict(r) for r in cursor.fetchall()]


def count_user_tickets(user_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE user_id = ?", (user_id,))
    return cursor.fetchone()[0]


def get_open_ticket_for_user(user_id):
    """يرجع آخر تذكرة مفتوحة للمستخدم"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM tickets
        WHERE user_id = ? AND status = 'open'
        ORDER BY created_at DESC LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_tickets_paginated(status=None, page=0, per_page=10):
    conn = get_db_conn()
    cursor = conn.cursor()
    if status:
        cursor.execute("""
            SELECT t.*, COUNT(tm.id) as msg_count
            FROM tickets t
            LEFT JOIN ticket_messages tm ON t.id = tm.ticket_id
            WHERE t.status = ?
            GROUP BY t.id
            ORDER BY t.created_at DESC
            LIMIT ? OFFSET ?
        """, (status, per_page, page * per_page))
    else:
        cursor.execute("""
            SELECT t.*, COUNT(tm.id) as msg_count
            FROM tickets t
            LEFT JOIN ticket_messages tm ON t.id = tm.ticket_id
            GROUP BY t.id
            ORDER BY t.created_at DESC
            LIMIT ? OFFSET ?
        """, (per_page, page * per_page))
    return [dict(r) for r in cursor.fetchall()]


def count_tickets(status=None):
    conn = get_db_conn()
    cursor = conn.cursor()
    if status:
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = ?", (status,))
    else:
        cursor.execute("SELECT COUNT(*) FROM tickets")
    return cursor.fetchone()[0]


def close_ticket(ticket_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE tickets SET status = 'closed' WHERE id = ?", (ticket_id,))
    conn.commit()


def set_ticket_group_msg(ticket_id, msg_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE tickets SET dev_group_msg_id = ? WHERE id = ?", (msg_id, ticket_id))
    conn.commit()


def get_ticket_by_group_msg(msg_id):
    """يجد التذكرة عبر رقم رسالة المجموعة"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE dev_group_msg_id = ?", (msg_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


# ══════════════════════════════════════════
# 💬 رسائل التذاكر
# ══════════════════════════════════════════

def add_ticket_message(ticket_id, sender, message_id=None,
                       message_type="text", content=None):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ticket_messages
        (ticket_id, sender, message_id, message_type, content)
        VALUES (?, ?, ?, ?, ?)
    """, (ticket_id, sender, message_id, message_type, content))
    conn.commit()
    return cursor.lastrowid


def get_ticket_messages(ticket_id, limit=20):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM ticket_messages
        WHERE ticket_id = ?
        ORDER BY created_at ASC
        LIMIT ?
    """, (ticket_id, limit))
    return [dict(r) for r in cursor.fetchall()]


# ══════════════════════════════════════════
# ⏱️ الحدود اليومية والكولداون
# ══════════════════════════════════════════

DAILY_LIMIT  = 2
COOLDOWN_SEC = 10


def check_limits(user_id):
    """
    يتحقق من الحد اليومي والكولداون.
    يرجع (True, None) إذا مسموح، أو (False, رسالة_خطأ)
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    today = time.strftime("%Y-%m-%d")
    now   = int(time.time())

    cursor.execute("""
        SELECT count, last_used FROM ticket_limits
        WHERE user_id = ? AND date = ?
    """, (user_id, today))
    row = cursor.fetchone()

    if row:
        count, last_used = row[0], row[1]
        # كولداون
        elapsed = now - last_used
        if elapsed < COOLDOWN_SEC:
            return False, f"⏳ انتظر {COOLDOWN_SEC - elapsed} ثانية قبل إرسال تذكرة جديدة."
        # حد يومي
        if count >= DAILY_LIMIT:
            return False, f"❌ وصلت للحد اليومي ({DAILY_LIMIT} تذاكر). حاول غداً."

    return True, None


def record_ticket_usage(user_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    today = time.strftime("%Y-%m-%d")
    now   = int(time.time())
    cursor.execute("""
        INSERT INTO ticket_limits (user_id, date, count, last_used)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(user_id, date) DO UPDATE
        SET count = count + 1, last_used = ?
    """, (user_id, today, now, now))
    conn.commit()


# ══════════════════════════════════════════
# 📊 الإحصائيات
# ══════════════════════════════════════════

def get_stats():
    conn = get_db_conn()
    cursor = conn.cursor()
    today = time.strftime("%Y-%m-%d")

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE date(created_at, 'unixepoch') = ?", (today,))
    today_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'open'")
    open_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'closed'")
    closed_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tickets")
    total_count = cursor.fetchone()[0]

    return {
        "today":  today_count,
        "open":   open_count,
        "closed": closed_count,
        "total":  total_count,
    }
