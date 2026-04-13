"""
نظام نقل ملكية الدولة
- كولداون 24 ساعة
- خصم 20% من ميزانية الدولة
- تجميد 24 ساعة بعد النقل
- إمكانية التراجع خلال 24 ساعة (بخصم 20% إضافي)
"""
import time
from database.connection import get_db_conn
from database.db_queries.advanced_war_queries import (
    create_country_transfer, get_active_transfer, complete_transfer,
    rollback_transfer, get_transfer_cooldown, freeze_country,
    unfreeze_country, is_country_frozen,
)
from database.db_queries.countries_queries import get_country_by_owner
from database.db_queries.bank_queries import get_user_balance, deduct_user_balance, update_bank_balance
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

TRANSFER_PENALTY = 0.20   # 20%
FREEZE_DURATION  = 86400  # 24 ساعة


def transfer_country(from_user_id, to_user_id):
    """
    ينقل ملكية الدولة من مستخدم لآخر.
    يرجع (True, msg) أو (False, msg)
    """
    # التحقق من الكولداون
    on_cd, remaining = get_transfer_cooldown(from_user_id)
    if on_cd:
        from utils.helpers import format_remaining_time
        return False, f"⏳ يمكنك النقل مرة واحدة كل 24 ساعة.\nالوقت المتبقي: {format_remaining_time(remaining)}"

    country = get_country_by_owner(from_user_id)
    if not country:
        return False, "❌ لا تملك دولة!"
    country = dict(country)

    # التحقق من التجميد
    frozen, rem = is_country_frozen(country["id"])
    if frozen:
        from utils.helpers import format_remaining_time
        return False, f"🧊 دولتك مجمدة. الوقت المتبقي: {format_remaining_time(rem)}"

    # التحقق من المستلم
    if to_user_id == from_user_id:
        return False, "❌ لا يمكنك نقل الدولة لنفسك!"

    existing = get_country_by_owner(to_user_id)
    if existing:
        return False, "❌ المستلم يملك دولة بالفعل!"

    # حساب الخصم من ميزانية المدن
    from database.db_queries.countries_queries import get_all_cities_of_country_by_country_id
    cities = get_all_cities_of_country_by_country_id(country["id"])
    total_budget = 0.0
    conn = get_db_conn()
    cursor = conn.cursor()
    for city in cities:
        cid = city["id"] if isinstance(city, dict) else city[0]
        cursor.execute("SELECT current_budget FROM city_budget WHERE city_id = ?", (cid,))
        row = cursor.fetchone()
        if row:
            total_budget += row[0]

    penalty = round(total_budget * TRANSFER_PENALTY, 2)

    # تطبيق الخصم على ميزانية المدن
    for city in cities:
        cid = city["id"] if isinstance(city, dict) else city[0]
        cursor.execute("""
            UPDATE city_budget
            SET current_budget = MAX(0, current_budget - ?)
            WHERE city_id = ?
        """, (penalty / max(len(cities), 1), cid))
    conn.commit()

    # نقل الملكية
    cursor.execute("UPDATE countries SET owner_id = ? WHERE id = ?", (to_user_id, country["id"]))
    # نقل المدن
    cursor.execute("UPDATE cities SET owner_id = ? WHERE country_id = ?", (to_user_id, country["id"]))
    conn.commit()

    # تجميد الدولة
    freeze_country(country["id"], FREEZE_DURATION, reason="transfer")

    # تسجيل النقل
    transfer_id = create_country_transfer(country["id"], from_user_id, to_user_id, penalty)

    return True, (
        f"✅ تم نقل دولة <b>{country['name']}</b> بنجاح!\n"
        f"💸 خصم: {penalty:.0f} {CURRENCY_ARABIC_NAME} (20%)\n"
        f"🧊 الدولة مجمدة لمدة 24 ساعة\n"
        f"↩️ يمكنك التراجع خلال 24 ساعة بكتابة: <code>تراجع نقل الدولة</code>"
    )


def rollback_country_transfer(original_owner_id):
    """
    يتراجع عن آخر نقل خلال 24 ساعة.
    """
    country = get_country_by_owner(original_owner_id)
    # المستخدم الأصلي لم يعد مالكاً — نبحث عن نقل نشط
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        SELECT * FROM country_transfers
        WHERE from_user_id = ? AND status = 'active' AND expires_at > ?
        ORDER BY transferred_at DESC LIMIT 1
    """, (original_owner_id, now))
    transfer = cursor.fetchone()
    if not transfer:
        return False, "❌ لا يوجد نقل يمكن التراجع عنه، أو انتهت مدة التراجع."

    transfer = dict(transfer)
    country_id = transfer["country_id"]

    # التحقق من أن المستلم لا يزال المالك
    cursor.execute("SELECT owner_id, name FROM countries WHERE id = ?", (country_id,))
    c = cursor.fetchone()
    if not c or c[0] != transfer["to_user_id"]:
        return False, "❌ تغيرت ملكية الدولة، لا يمكن التراجع."

    # خصم 20% إضافي
    from database.db_queries.countries_queries import get_all_cities_of_country_by_country_id
    cities = get_all_cities_of_country_by_country_id(country_id)
    total_budget = 0.0
    for city in cities:
        cid = city["id"] if isinstance(city, dict) else city[0]
        cursor.execute("SELECT current_budget FROM city_budget WHERE city_id = ?", (cid,))
        row = cursor.fetchone()
        if row:
            total_budget += row[0]

    penalty = round(total_budget * TRANSFER_PENALTY, 2)
    for city in cities:
        cid = city["id"] if isinstance(city, dict) else city[0]
        cursor.execute("""
            UPDATE city_budget SET current_budget = MAX(0, current_budget - ?)
            WHERE city_id = ?
        """, (penalty / max(len(cities), 1), cid))

    # إعادة الملكية
    cursor.execute("UPDATE countries SET owner_id = ? WHERE id = ?", (original_owner_id, country_id))
    cursor.execute("UPDATE cities SET owner_id = ? WHERE country_id = ?", (original_owner_id, country_id))
    conn.commit()

    rollback_transfer(transfer["id"])
    unfreeze_country(country_id)

    return True, (
        f"↩️ تم التراجع عن النقل!\n"
        f"💸 خصم إضافي: {penalty:.0f} {CURRENCY_ARABIC_NAME} (20%)\n"
        f"🧊 تم رفع التجميد عن الدولة."
    )


def get_country_freeze_status(country_id):
    return is_country_frozen(country_id)
