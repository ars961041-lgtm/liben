import time

from ..connection import get_db_conn
MAX_BANK_BALANCE = 1_000_000  # الحد الأقصى للرصيد

def check_bank_account(user_id: int) -> tuple[bool, str]:
    try:
            conn = get_db_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM user_accounts WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return True, ""
            else:
                return False, " ليس لديك حساب بنكي بعد. استخدم '<code>إنشاء حساب بنكي</code>' لفتح حساب."
    except Exception as e:
        return False, f"[check_bank_account] خطأ: {e}"


def create_bank_account(user_id, initial_balance=1000.0):
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO user_accounts (user_id, balance) VALUES (?, ?)',
            (user_id, initial_balance)
        )
        conn.commit()
        return True

# def create_bank_account(user_id, initial_balance=1000):
#     conn = get_db_conn()
#     cursor = conn.cursor()
    
#     # تحقق أن المستخدم موجود
#     cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
#     if cursor.fetchone() is None:
#         return False, "المستخدم غير موجود في قاعدة البيانات"
    
#     # إنشاء الحساب البنكي
#     cursor.execute(
#         "INSERT INTO user_accounts (user_id, balance, created_at) VALUES (?, ?, ?)",
#         (user_id, initial_balance, int(time.time()))
#     )
#     conn.commit()
#     return True, "تم إنشاء الحساب بنجاح"
    
def update_bank_balance(user_id, delta):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM user_accounts WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if not row:
        return False
    new_balance = min(MAX_BANK_BALANCE, float(row[0]) + float(delta))
    if new_balance < 0:
        return False
    cursor.execute('UPDATE user_accounts SET balance = ? WHERE user_id = ?', (new_balance, user_id))
    conn.commit()
    return True

def deduct_user_balance(user_id, amount):
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT id, balance FROM user_accounts WHERE user_id = ? ORDER BY balance DESC', (user_id,))
        rows = cursor.fetchall()
        remaining = float(amount)

        if not rows:
            return False

        for account_id, balance in rows:
            if remaining <= 0:
                break

            current = float(balance)
            if current <= 0:
                continue

            deduction = min(current, remaining)
            new_balance = current - deduction
            cursor.execute('UPDATE user_accounts SET balance = ? WHERE id = ?', (new_balance, account_id))
            remaining -= deduction

        if remaining > 0:
            conn.rollback()
            return False

        conn.commit()
        return True

def get_user_balance(user_id):
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT balance FROM user_accounts WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        return float(row[0]) if row else 0.0
 
def set_cooldown(user_id, action):
    now = int(time.time())
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_cooldowns(user_id, action, last_time)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, action)
        DO UPDATE SET last_time = excluded.last_time
    """, (user_id, action, now))
    conn.commit()

def get_cooldown(user_id, action):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT last_time FROM user_cooldowns WHERE user_id=? AND action=?", (user_id, action))
    row = cursor.fetchone()
    return row[0] if row else None

def can_use_cooldown(user_id, action, cooldown_seconds):
    last_time = get_cooldown(user_id, action)
    if not last_time:
        return True, 0
    now = int(time.time())
    remaining = cooldown_seconds - (now - last_time)
    if remaining <= 0:
        return True, 0
    return False, remaining
     
def get_top_bank_balances(limit=30):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ua.user_id, ua.balance, COALESCE(un.name, 'Unknown') as name
        FROM user_accounts ua
        LEFT JOIN users_name un ON ua.user_id = un.user_id
        ORDER BY ua.balance DESC
        LIMIT ?
    ''', (limit,))
    return cursor.fetchall()