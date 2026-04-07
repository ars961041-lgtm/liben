import sqlite3
import time
from ..connection import get_db_conn
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME
# ================================
# ⚡️ الحسابات البنكية
# ================================
def check_bank_account(user_id):
    """تتحقق إذا كان لدى المستخدم حساب بنكي — ترجع True/False"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM user_accounts WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

def create_bank_account(user_id, initial_balance=None):
    """إنشاء حساب بنكي جديد — الرصيد الافتراضي من bot_constants"""
    if initial_balance is None:
        try:
            from core.admin import get_const_int
            initial_balance = get_const_int("initial_balance", 10000)
        except Exception:
            initial_balance = 10000
    conn = get_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO user_accounts (user_id, balance, last_daily_claim, created_at) VALUES (?, ?, 0, ?)",
            (user_id, initial_balance, int(time.time()))
        )
        conn.commit()
        return True
    except Exception:
        return False

def get_user_balance(user_id):
    """ترجع رصيد المستخدم"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM user_accounts WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0

def update_bank_balance(user_id, amount):
    """تحديث رصيد المستخدم — ينشئ الحساب تلقائياً إذا لم يكن موجوداً"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_accounts (user_id, balance, last_daily_claim, created_at)
        VALUES (?, MAX(0, ?), 0, ?)
        ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?
    """, (user_id, amount, int(time.time()), amount))
    conn.commit()

def deduct_user_balance(user_id, amount):
    """خصم مبلغ من رصيد المستخدم"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM user_accounts WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row or row[0] < amount:
        return False
    new_balance = row[0] - amount
    cursor.execute("UPDATE user_accounts SET balance = ? WHERE user_id = ?", (new_balance, user_id))
    conn.commit()
    return True

# ================================
# ⏱️ نظام الكولداون
# ================================
def can_use_cooldown(user_id, action, cooldown_sec):
    """تتحقق إذا يمكن استخدام أمر ما بعد الكولداون"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT last_used FROM bank_cooldowns WHERE user_id=? AND type=?", (user_id, action))
    row = cursor.fetchone()
    now = int(time.time())
    if row:
        last = row[0]
        if now - last < cooldown_sec:
            return False, cooldown_sec - (now - last)
    return True, 0

def set_cooldown(user_id, action):
    """تعيين وقت استخدام أمر ما"""
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        INSERT INTO bank_cooldowns (user_id, type, last_used)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, type) DO UPDATE SET last_used=excluded.last_used
    """, (user_id, action, now))
    conn.commit()

# ================================
# 💵 القروض
# ================================
LATE_PENALTY_RATE = 0.05  # 5% غرامة تأخير لمرة واحدة فقط

def create_loan(user_id, amount, due_seconds=86400*7):
    """منح قرض للمستخدم بدون فوائد"""
    from core.admin import get_const_int
    max_loan = get_const_int("max_loan_amount", 10000)
    if amount > max_loan:
        return False, f"❌ الحد الأقصى للقرض هو {max_loan} {CURRENCY_ARABIC_NAME}"
    conn = get_db_conn()
    cursor = conn.cursor()
    due_date = int(time.time()) + due_seconds
    cursor.execute("""
        INSERT INTO loans (user_id, amount, due_date, repaid, status)
        VALUES (?, ?, ?, 0, 'active')
    """, (user_id, amount, due_date))
    update_bank_balance(user_id, amount)
    conn.commit()
    return True, f"💵 تم منحك قرضًا بقيمة {amount} {CURRENCY_ARABIC_NAME}\n📅 موعد السداد: {time.strftime('%Y-%m-%d', time.localtime(due_date))}"

def repay_loan(user_id, loan_id, amount):
    """سداد قرض"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT amount, repaid, due_date, status FROM loans WHERE id=? AND user_id=?", (loan_id, user_id))
    loan = cursor.fetchone()
    if not loan:
        return False, "❌ لا يوجد قرض بهذا الرقم"

    loan_amount, repaid, due_date, status = loan
    now = int(time.time())

    # تحديث الحالة إلى overdue إذا تأخر
    if now > due_date and status == 'active':
        cursor.execute("UPDATE loans SET status='overdue' WHERE id=?", (loan_id,))
        status = 'overdue'

    # حساب المبلغ المستحق (مع غرامة التأخير إن وجدت — مرة واحدة فقط)
    penalty = round(loan_amount * LATE_PENALTY_RATE, 2) if status == 'overdue' else 0
    total_due = round(loan_amount + penalty - repaid, 2)

    if amount > get_user_balance(user_id):
        return False, "❌ رصيدك غير كافٍ"

    repay_amount = min(amount, total_due)
    update_bank_balance(user_id, -repay_amount)
    cursor.execute("UPDATE loans SET repaid=repaid+? WHERE id=?", (repay_amount, loan_id))
    if repay_amount >= total_due:
        cursor.execute("UPDATE loans SET status='repaid' WHERE id=?", (loan_id,))
    conn.commit()
    return True, f"✅ دفعت {repay_amount:.2f} {CURRENCY_ARABIC_NAME} من القرض"

def get_active_loans(user_id):
    """إرجاع القروض النشطة والمتأخرة للمستخدم"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, amount, due_date, repaid, status FROM loans WHERE user_id=? AND status IN ('active','overdue')",
        (user_id,)
    )
    return cursor.fetchall()

def get_last_daily_claim(user_id: int) -> int:
    """Returns the last_daily_claim timestamp for the user."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT last_daily_claim FROM user_accounts WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0

def set_last_daily_claim(user_id: int):
    """Updates last_daily_claim to now."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE user_accounts SET last_daily_claim=? WHERE user_id=?",
        (int(time.time()), user_id)
    )
    conn.commit()


# ================================
# 💸 التحويل البنكي
# ================================

def transfer_funds(from_user_id: int, to_user_id: int, amount: float) -> tuple[bool, str]:
    """
    يحوّل مبلغاً من حساب لآخر مع خصم رسوم التحويل.
    يرجع (True, msg) أو (False, msg)
    """
    try:
        from core.admin import get_const_float, get_const_int
        fee_pct     = get_const_float("transfer_fee_pct",    0.05)
        min_amount  = get_const_int("transfer_min_amount",   10)
        max_amount  = get_const_int("transfer_max_amount",   100000)
    except Exception:
        fee_pct, min_amount, max_amount = 0.05, 10, 100000

    if amount < min_amount:
        return False, f"❌ الحد الأدنى للتحويل هو {min_amount} {CURRENCY_ARABIC_NAME}"
    if amount > max_amount:
        return False, f"❌ الحد الأقصى للتحويل هو {max_amount} {CURRENCY_ARABIC_NAME}"
    if from_user_id == to_user_id:
        return False, "❌ لا يمكنك التحويل لنفسك"

    if not check_bank_account(from_user_id):
        return False, "❌ ليس لديك حساب بنكي"
    if not check_bank_account(to_user_id):
        return False, "❌ المستخدم المستهدف لا يملك حساباً بنكياً"

    # ─── تطبيق حدث خصم رسوم التحويل ───
    try:
        from modules.progression.global_events import get_event_effect
        fee_discount = get_event_effect("transfer_fee_discount")
        if fee_discount > 0:
            fee_pct = max(0.0, fee_pct * (1 - fee_discount))
    except Exception:
        pass

    fee   = round(amount * fee_pct, 2)
    total = amount + fee

    conn   = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM user_accounts WHERE user_id = ?", (from_user_id,))
    row = cursor.fetchone()
    if not row or row[0] < total:
        return False, f"❌ رصيدك غير كافٍ\nالمطلوب: {total:.2f} {CURRENCY_ARABIC_NAME} (شامل رسوم {fee:.2f})"

    # خصم من المرسل
    cursor.execute(
        "UPDATE user_accounts SET balance = balance - ? WHERE user_id = ?",
        (total, from_user_id)
    )
    # إضافة للمستقبل
    cursor.execute(
        "UPDATE user_accounts SET balance = balance + ? WHERE user_id = ?",
        (amount, to_user_id)
    )
    # تسجيل العملية
    cursor.execute(
        "INSERT INTO bank_transfers (from_user_id, to_user_id, amount, fee) VALUES (?,?,?,?)",
        (from_user_id, to_user_id, amount, fee)
    )
    conn.commit()
    return True, (
        f"✅ <b>تم التحويل بنجاح!</b>\n"
        f"💸 المبلغ: {amount:.2f} {CURRENCY_ARABIC_NAME}\n"
        f"💳 الرسوم: {fee:.2f} {CURRENCY_ARABIC_NAME}\n"
        f"📤 المجموع المخصوم: {total:.2f} {CURRENCY_ARABIC_NAME}"
    )
