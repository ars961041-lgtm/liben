# modules/bank/commands/bank_commands.py

from modules.bank.services.bank_service import (
    salary, small_task, daily_reward, light_risk, invest,
    take_loan, list_loans, repay_user_loan,
    purchase_in_city, can_purchase, can_risk, can_invest, can_take_loan
)
from database.db_queries.bank_queries import (
    check_bank_account, create_bank_account,
    get_user_balance, get_active_loans
)
from core.bot import bot
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME
from utils.helpers import get_lines

# أوامر تحتاج حساب بنكي
_NEEDS_ACCOUNT = {"راتب", "مهمة", "يومي", "مخاطرة", "استثمر", "استثمار",
                  "اقرضني", "قروضي", "تسديد القرض", "حول", "تحويل"}

def _requires_account(text):
    first = text.split()[0] if text.split() else text
    return first in _NEEDS_ACCOUNT or text in _NEEDS_ACCOUNT


def _build_account_info(target_user_id: int, display_name: str) -> str:
    """
    Builds the bank account info card for a given user.
    Returns a formatted string ready to send.
    """
    if not check_bank_account(target_user_id):
        return (
            f"👤 <b>{display_name}</b>\n"
            f"❌ لا يملك حساباً بنكياً بعد."
        )

    balance = get_user_balance(target_user_id)
    loans   = get_active_loans(target_user_id)

    total_loan_debt = 0.0
    for loan in loans:
        # loan row: (id, amount, due_date, repaid, status)
        amount = loan[1] if not isinstance(loan, dict) else loan["amount"]
        repaid = loan[3] if not isinstance(loan, dict) else loan["repaid"]
        total_loan_debt += max(0.0, amount - repaid)

    loan_line = (
        f"💳 القروض النشطة: {len(loans)} قرض "
        f"(متبقي: {total_loan_debt:,.2f} {CURRENCY_ARABIC_NAME})"
        if loans else
        "💳 القروض: لا توجد قروض نشطة"
    )

    return (
        f"🏦 <b>معلومات الحساب البنكي</b>\n"
        f"{get_lines()}\n"
        f"👤 الاسم: <b>{display_name}</b>\n"
        f"🆔 رقم الحساب: <code>{target_user_id}</code>\n"
        f"💰 الرصيد: <b>{balance:,.2f} {CURRENCY_ARABIC_NAME}</b>\n"
        f"{loan_line}"
    )


def bank_commands(message):
    text    = message.text.strip().lower()
    user_id = message.from_user.id

    # ─── حسابي / حسابه ───────────────────────────────────────────
    if text in ("حسابي", "حسابه"):
        if text == "حسابه" and message.reply_to_message:
            # target = the user whose message was replied to
            target    = message.reply_to_message.from_user
            target_id = target.id
            name      = target.first_name or "مجهول"
        else:
            # target = the sender
            target_id = user_id
            name      = message.from_user.first_name or "مجهول"

        reply = _build_account_info(target_id, name)
        bot.reply_to(message, reply, parse_mode="HTML")
        return True

    # 💰 عرض الرصيد
    if text == "فلوسي":
        if not check_bank_account(user_id):
            bot.reply_to(message, "❌ ليس لديك حساب بنكي.\nاكتب '<code>انشاء حساب بنكي</code>' أولاً.", parse_mode='HTML')
            return True
        balance = get_user_balance(user_id)
        bot.reply_to(message, f"💰 رصيدك الحالي: {balance:.2f} {CURRENCY_ARABIC_NAME}")
        return True

    # إنشاء حساب بنكي
    if text == "انشاء حساب بنكي" or text == "إنشاء حساب بنكي":
        if check_bank_account(user_id):
            bot.reply_to(message, "✅ لديك حساب بالفعل")
        else:
            create_bank_account(user_id)
            from core.admin import get_const_int
            bal = get_const_int("initial_balance", 10000)
            bot.reply_to(message, f"✅ تم إنشاء حسابك البنكي برصيد {bal:,} {CURRENCY_ARABIC_NAME}")
        return True

    # تحقق من وجود حساب قبل أي أمر مالي
    if _requires_account(text):
        if not check_bank_account(user_id):
            bot.reply_to(message, "❌ ليس لديك حساب بنكي.\nاكتب '<code>انشاء حساب بنكي</code>' أولاً.", parse_mode='HTML')
            return True

    # 🏦 الراتب اليومي
    if text == "راتب":
        success, reply = salary(user_id, message.from_user.username)
        bot.reply_to(message, reply)
        return True

    # 📝 مهمة صغيرة
    elif text == "مهمة":
        success, reply = small_task(user_id)
        bot.reply_to(message, reply)
        return True

    # 🎁 المكافأة اليومية
    elif text == "يومي":
        success, reply = daily_reward(user_id)
        bot.reply_to(message, reply)
        return True

    # 🎲 المخاطرة
    elif text.startswith("مخاطرة"):
        ok, msg = can_risk(user_id)
        if not ok:
            bot.reply_to(message, msg)
            return True
        success, reply = light_risk(user_id)
        bot.reply_to(message, reply)
        return True

    # 📈 الاستثمار
    elif text.startswith("استثمر") or text.startswith("استثمار"):
        # دعم الاستثمار بمبلغ معين: "استثمر 500"
        parts = text.split()
        amount = None
        if len(parts) > 1 and parts[1].isdigit():
            amount = int(parts[1])
        ok, msg = can_invest(user_id, amount)
        if not ok:
            bot.reply_to(message, msg)
            return True
        success, reply = invest(user_id, amount)
        bot.reply_to(message, reply)
        return True

    # 💵 قرض
    elif text.startswith("اقرضني"):
        parts = text.split()
        amount = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 100
        ok, msg = can_take_loan(user_id, amount)
        if not ok:
            bot.reply_to(message, msg)
            return True
        success, reply = take_loan(user_id, amount)
        bot.reply_to(message, reply)
        return True

    # 💳 القروض النشطة
    elif text == "قروضي":
        reply = list_loans(user_id)
        bot.reply_to(message, reply)
        return True

    # 💸 تسديد قرض: تسديد القرض [id] [مبلغ]
    elif text.startswith("تسديد القرض"):
        parts = text.split()
        if len(parts) < 4 or not parts[2].isdigit() or not parts[3].isdigit():
            bot.reply_to(message, "❌ الصيغة الصحيحة:\nتسديد القرض [رقم القرض] [المبلغ]\n\nمثال: تسديد القرض 1 500\n\nاستخدم قروضي لعرض أرقام قروضك.")
            return True
        loan_id = int(parts[2])
        amount = int(parts[3])
        success, reply = repay_user_loan(user_id, loan_id, amount)
        bot.reply_to(message, reply)
        return True

    # 💸 تحويل: حول [ID] [مبلغ]
    elif text.startswith("حول ") or text.startswith("تحويل "):
        parts = text.split()
        if len(parts) < 3:
            bot.reply_to(message,
                "❌ الصيغة الصحيحة:\n<code>حول [آيدي المستخدم] [المبلغ]</code>\n"
                "مثال: <code>حول 123456789 500</code>", parse_mode="HTML")
            return True
        if not check_bank_account(user_id):
            bot.reply_to(message, "❌ ليس لديك حساب بنكي.\nاكتب '<code>انشاء حساب بنكي</code>' أولاً.",
                         parse_mode="HTML")
            return True
        uid_str = parts[1]
        amt_str = parts[2]
        if not uid_str.lstrip("-").isdigit() or not amt_str.replace(".", "").isdigit():
            bot.reply_to(message, "❌ آيدي أو مبلغ غير صالح")
            return True
        to_uid = int(uid_str)
        amount = float(amt_str)
        from database.db_queries.bank_queries import transfer_funds
        ok, msg = transfer_funds(user_id, to_uid, amount)
        bot.reply_to(message, msg, parse_mode="HTML")
        if ok:
            try:
                from modules.progression.achievements import trigger_achievement_check
                trigger_achievement_check(user_id, "balance_updated")
            except Exception:
                pass
        return True

    # 🏗 مشتريات داخل المدينة
    elif text.startswith("اشتري"):
        parts = text.split()
        if len(parts) < 3 or not parts[-1].isdigit():
            bot.reply_to(message, "❌ صيغة الأمر: اشتري <اسم الشيء> <السعر>")
            return True
        building_name = " ".join(parts[1:-1])
        price = int(parts[-1])
        ok, msg = can_purchase(user_id, price)
        if not ok:
            bot.reply_to(message, msg)
            return True
        success, reply = purchase_in_city(user_id, building_name, price)
        bot.reply_to(message, reply)
        return True

    return False