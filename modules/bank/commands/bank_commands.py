# modules/bank/commands/bank_commands.py

from modules.bank.services.bank_service import (
    salary, small_task, daily_reward, light_risk, invest,
    take_loan, list_loans, repay_user_loan,
    purchase_in_city, can_purchase, can_risk, can_invest, can_take_loan
)
from database.db_queries.bank_queries import check_bank_account, create_bank_account
from core.bot import bot
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

# أوامر تحتاج حساب بنكي
_NEEDS_ACCOUNT = {"راتب", "مهمة", "يومي", "مخاطرة", "استثمر", "استثمار",
                  "اقرضني", "قروضي", "تسديد القرض", "حول", "تحويل"}

def _requires_account(text):
    first = text.split()[0] if text.split() else text
    return first in _NEEDS_ACCOUNT or text in _NEEDS_ACCOUNT

def bank_commands(message):
    text = message.text.strip().lower()
    user_id = message.from_user.id

    # 💰 عرض الرصيد
    if text == "فلوسي":
        from database.db_queries.bank_queries import get_user_balance
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