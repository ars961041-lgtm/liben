"""
إدارة المدن المتقدمة:
1. مسح مدينتي     — حذف المدينة مع نقل 50% من مواردها
2. انضمام          — الانتقال لدولة أخرى (نظام الخيانة)
3. تغيير اسم مدينتي / دولتي / تحالفي — إعادة التسمية المدفوعة
"""
import time
from core.bot import bot
from database.connection import get_db_conn
from database.db_queries.bank_queries import (
    get_user_balance, deduct_user_balance, update_bank_balance
)
from database.db_queries.cities_queries import get_user_city, delete_city
from database.db_queries.countries_queries import (
    get_country_by_owner, get_country_by_user,
    get_cities_by_country, get_all_cities_of_country_by_country_id
)
from utils.pagination import btn, send_ui, edit_ui, register_action, set_state, get_state, clear_state
from utils.helpers import get_lines
from utils.logger import log_event
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

# ── تكاليف ──
RENAME_COST        = 500    # Bito لإعادة التسمية
BETRAYAL_PENALTY   = 0.30   # 30% خصم من موارد المدينة
TRANSFER_RATIO     = 0.50   # 50% تُنقل عند مسح المدينة
MAX_CITIES         = 10     # حد أقصى للمدن في الدولة
RENAME_COOLDOWN    = 86400  # 24 ساعة
BETRAYAL_COOLDOWN  = 86400  # 24 ساعة


# ══════════════════════════════════════════
# 🏙 1. مسح مدينتي
# ══════════════════════════════════════════

def handle_delete_city_cmd(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    city = get_user_city(user_id)
    if not city:
        bot.reply_to(message, "❌ ليس لديك مدينة.")
        return

    city = dict(city)
    owner = (user_id, chat_id)

    send_ui(chat_id,
        text=(
            f"⚠️ <b>تأكيد مسح المدينة</b>\n{get_lines()}\n\n"
            f"🏙 المدينة: <b>{city['name']}</b>\n\n"
            f"• سيتم نقل <b>50%</b> من موارد مدينتك للمدينة الرئيسية في دولتك\n"
            f"• سيتم حذف المدينة وجميع مبانيها نهائياً\n\n"
            f"⚠️ هذا الإجراء لا يمكن التراجع عنه!"
        ),
        buttons=[
            btn("✅ تأكيد المسح", "city_delete_confirm",
                data={"city_id": city["id"]}, owner=owner, color="d"),
            btn("❌ إلغاء", "city_delete_cancel", data={}, owner=owner),
        ],
        layout=[2], owner_id=user_id,
        reply_to=message.message_id
    )


@register_action("city_delete_confirm")
def _on_delete_confirm(call, data):
    user_id = call.from_user.id
    city_id = int(data["city_id"])

    # تحقق من الملكية
    city = get_user_city(user_id)
    if not city or dict(city)["id"] != city_id:
        bot.answer_callback_query(call.id, "❌ لا تملك هذه المدينة.", show_alert=True)
        return

    city = dict(city)
    ok, msg = _delete_city_with_transfer(user_id, city_id, city)
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(msg, call.message.chat.id,
                              call.message.message_id, parse_mode="HTML")
    except Exception:
        bot.send_message(call.message.chat.id, msg, parse_mode="HTML")

    log_event("city_deleted", user=user_id, city_id=city_id, city_name=city["name"])


@register_action("city_delete_cancel")
def _on_delete_cancel(call, data):
    bot.answer_callback_query(call.id, "✅ تم الإلغاء")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


def _delete_city_with_transfer(user_id: int, city_id: int, city: dict) -> tuple[bool, str]:
    """
    ينقل 50% من ميزانية المدينة للمدينة الرئيسية ثم يحذفها.
    """
    conn = get_db_conn()
    cursor = conn.cursor()

    try:
        # جلب ميزانية المدينة
        cursor.execute("SELECT current_budget FROM city_budget WHERE city_id = ?", (city_id,))
        row = cursor.fetchone()
        budget = float(row[0]) if row and row[0] else 0.0
        transfer_amount = round(budget * TRANSFER_RATIO, 2)

        # جلب المدينة الرئيسية للدولة (أول مدينة غير هذه)
        country_id = city.get("country_id")
        if country_id and transfer_amount > 0:
            cursor.execute(
                "SELECT id FROM cities WHERE country_id = ? AND id != ? LIMIT 1",
                (country_id, city_id)
            )
            capital = cursor.fetchone()
            if capital:
                cursor.execute(
                    "UPDATE city_budget SET current_budget = current_budget + ? WHERE city_id = ?",
                    (transfer_amount, capital[0])
                )

        # حذف كل البيانات المرتبطة بالمدينة
        for table in ("buildings", "city_budget", "city_aspects",
                      "injured_troops", "damaged_equipment",
                      "city_troops", "city_equipment"):
            try:
                cursor.execute(f"DELETE FROM {table} WHERE city_id = ?", (city_id,))
            except Exception:
                pass  # الجدول قد لا يوجد

        cursor.execute("DELETE FROM cities WHERE id = ?", (city_id,))
        conn.commit()

        msg = (
            f"✅ <b>تم مسح المدينة بنجاح</b>\n{get_lines()}\n\n"
            f"🏙 المدينة: <b>{city['name']}</b>\n"
            f"💰 تم نقل <b>{transfer_amount:.0f} {CURRENCY_ARABIC_NAME}</b> للمدينة الرئيسية"
        )
        return True, msg

    except Exception as e:
        conn.rollback()
        return False, f"❌ حدث خطأ أثناء مسح المدينة: {e}"


# ══════════════════════════════════════════
# 🔁 2. الانضمام لدولة أخرى (الخيانة)
# ══════════════════════════════════════════

def handle_join_country_cmd(message):
    """
    يُفعَّل بالرد على رسالة مالك الدولة المستهدفة بـ "انضمام"
    """
    user_id = message.from_user.id
    chat_id = message.chat.id

    # يجب أن يكون رداً
    if not message.reply_to_message:
        bot.reply_to(message,
                     "❌ استخدم هذا الأمر بالرد على رسالة مالك الدولة التي تريد الانضمام إليها.")
        return

    target_owner_id = message.reply_to_message.from_user.id
    if target_owner_id == user_id:
        bot.reply_to(message, "❌ لا يمكنك الانضمام لدولتك الخاصة.")
        return

    # فحص كولداون الخيانة
    if not _can_betray(user_id):
        bot.reply_to(message, "⏳ يمكنك محاولة الانضمام مرة واحدة كل 24 ساعة.")
        return

    # فحص: المستخدم يملك مدينة
    city = get_user_city(user_id)
    if not city:
        bot.reply_to(message, "❌ ليس لديك مدينة للانضمام بها.")
        return
    city = dict(city)

    # فحص: الهدف يملك دولة
    target_country = get_country_by_owner(target_owner_id)
    if not target_country:
        bot.reply_to(message, "❌ هذا المستخدم لا يملك دولة.")
        return
    target_country = dict(target_country)

    # فحص: سعة الدولة
    cities = get_all_cities_of_country_by_country_id(target_country["id"])
    if len(cities) >= MAX_CITIES:
        bot.reply_to(message,
                     f"❌ دولة <b>{target_country['name']}</b> وصلت للحد الأقصى ({MAX_CITIES} مدن).",
                     parse_mode="HTML")
        return

    # فحص: تكرار اسم المدينة داخل الدولة المستهدفة
    city_names = [dict(c)["name"].lower() for c in cities]
    if city["name"].lower() in city_names:
        bot.reply_to(message,
                     f"❌ يوجد مدينة باسم <b>{city['name']}</b> في دولة <b>{target_country['name']}</b> مسبقاً.",
                     parse_mode="HTML")
        return

    # تطبيق عقوبة الخيانة (30%) فوراً — بغض النظر عن القبول
    _apply_betrayal_penalty(user_id, city["id"])
    _set_betrayal_cooldown(user_id)

    # إرسال طلب الموافقة للمالك المستهدف
    _send_join_request(
        requester_id=user_id,
        requester_city=city,
        target_owner_id=target_owner_id,
        target_country=target_country,
        group_chat_id=chat_id
    )

    bot.reply_to(message,
                 f"📨 تم إرسال طلب الانضمام لـ <b>{target_country['name']}</b>\n"
                 f"⚠️ تم خصم <b>30%</b> من موارد مدينتك كغرامة انتقال.",
                 parse_mode="HTML")


def _send_join_request(requester_id, requester_city, target_owner_id, target_country, group_chat_id):
    owner = (target_owner_id, None)
    text = (
        f"🔔 <b>طلب انضمام جديد!</b>\n{get_lines()}\n\n"
        f"👤 المستخدم: <a href='tg://user?id={requester_id}'>{requester_id}</a>\n"
        f"🏙 مدينته: <b>{requester_city['name']}</b>\n"
        f"🌍 يريد الانضمام لدولتك: <b>{target_country['name']}</b>\n\n"
        f"هل توافق على ضم مدينته؟"
    )
    buttons = [
        btn("✅ قبول", "city_join_accept",
            data={"uid": requester_id, "city_id": requester_city["id"],
                  "country_id": target_country["id"]},
            owner=owner, color="su"),
        btn("❌ رفض", "city_join_reject",
            data={"uid": requester_id, "city_id": requester_city["id"]},
            owner=owner, color="d"),
    ]
    try:
        send_ui(target_owner_id, text=text, buttons=buttons, layout=[2],
                owner_id=target_owner_id)
    except Exception:
        # البوت لا يستطيع مراسلة المالك — أبلغ في المجموعة
        try:
            bot.send_message(group_chat_id,
                             f"⚠️ لا يمكن إرسال طلب الانضمام لمالك الدولة في الخاص.\n"
                             f"يرجى فتح محادثة مع البوت أولاً.",
                             parse_mode="HTML")
        except Exception:
            pass


@register_action("city_join_accept")
def _on_join_accept(call, data):
    target_owner_id = call.from_user.id
    requester_id    = int(data["uid"])
    city_id         = int(data["city_id"])
    country_id      = int(data["country_id"])

    # تحقق من الملكية
    country = get_country_by_owner(target_owner_id)
    if not country or dict(country)["id"] != country_id:
        bot.answer_callback_query(call.id, "❌ لا تملك هذه الدولة.", show_alert=True)
        return

    # فحص السعة مجدداً
    cities = get_all_cities_of_country_by_country_id(country_id)
    if len(cities) >= MAX_CITIES:
        bot.answer_callback_query(call.id, "❌ الدولة وصلت للحد الأقصى.", show_alert=True)
        return

    # نقل المدينة للدولة الجديدة
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE cities SET country_id = ? WHERE id = ? AND owner_id = ?",
                   (country_id, city_id, requester_id))
    conn.commit()

    country = dict(country)
    bot.answer_callback_query(call.id, "✅ تم قبول الانضمام")
    try:
        bot.edit_message_text(
            f"✅ <b>تم قبول انضمام المدينة لدولة {country['name']}</b>",
            call.message.chat.id, call.message.message_id, parse_mode="HTML"
        )
    except Exception:
        pass

    # إبلاغ الطالب
    try:
        bot.send_message(requester_id,
                         f"✅ تم قبول انضمامك لدولة <b>{country['name']}</b>!",
                         parse_mode="HTML")
    except Exception:
        pass

    log_event("city_joined", user=requester_id, city_id=city_id, country_id=country_id)


@register_action("city_join_reject")
def _on_join_reject(call, data):
    requester_id = int(data["uid"])
    bot.answer_callback_query(call.id, "❌ تم رفض الطلب")
    try:
        bot.edit_message_text(
            "❌ <b>تم رفض طلب الانضمام</b>",
            call.message.chat.id, call.message.message_id, parse_mode="HTML"
        )
    except Exception:
        pass

    try:
        bot.send_message(requester_id,
                         "❌ تم رفض طلب انضمامك.\n"
                         "⚠️ غرامة الانتقال (30%) لن تُسترد.")
    except Exception:
        pass

    log_event("city_join_rejected", user=requester_id)


def _apply_betrayal_penalty(user_id: int, city_id: int):
    """يخصم 30% من ميزانية المدينة كغرامة انتقال"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT current_budget FROM city_budget WHERE city_id = ?", (city_id,))
    row = cursor.fetchone()
    if row and row[0]:
        penalty = round(float(row[0]) * BETRAYAL_PENALTY, 2)
        cursor.execute(
            "UPDATE city_budget SET current_budget = MAX(0, current_budget - ?) WHERE city_id = ?",
            (penalty, city_id)
        )
        conn.commit()


def _can_betray(user_id: int) -> bool:
    conn = get_db_conn()
    cursor = conn.cursor()
    day_ago = int(time.time()) - BETRAYAL_COOLDOWN
    cursor.execute(
        "SELECT id FROM action_cooldowns WHERE user_id = ? AND action = 'betray' AND last_time > ?",
        (user_id, day_ago)
    )
    return cursor.fetchone() is None


def _set_betrayal_cooldown(user_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        INSERT INTO action_cooldowns (user_id, action, last_time)
        VALUES (?, 'betray', ?)
        ON CONFLICT(user_id, action) DO UPDATE SET last_time = excluded.last_time
    """, (user_id, now))
    conn.commit()


# ══════════════════════════════════════════
# ✏️ 3. إعادة التسمية
# ══════════════════════════════════════════

def handle_rename_cmd(message, entity: str):
    """
    entity: 'city' | 'country' | 'alliance'
    """
    user_id = message.from_user.id
    chat_id = message.chat.id

    # فحص الكولداون
    action_key = f"rename_{entity}"
    if not _can_rename(user_id, action_key):
        bot.reply_to(message,
                     f"⏳ يمكنك إعادة التسمية مرة واحدة كل 24 ساعة.")
        return

    # فحص الرصيد
    balance = get_user_balance(user_id)
    if balance < RENAME_COST:
        bot.reply_to(message,
                     f"❌ تحتاج <b>{RENAME_COST} {CURRENCY_ARABIC_NAME}</b> لإعادة التسمية (رصيدك: {balance:.0f}).",
                     parse_mode="HTML")
        return

    labels = {"city": "مدينتك", "country": "دولتك", "alliance": "تحالفك"}
    label  = labels.get(entity, "الكيان")

    set_state(user_id, chat_id, f"awaiting_rename_{entity}",
              data={"_mid": message.message_id})
    bot.reply_to(message,
                 f"✏️ أرسل الاسم الجديد لـ <b>{label}</b>\n"
                 f"💰 التكلفة: <b>{RENAME_COST} {CURRENCY_ARABIC_NAME}</b>",
                 parse_mode="HTML")


def handle_rename_input(message) -> bool:
    """يُستدعى من receive_responses لمعالجة الاسم الجديد"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    state   = get_state(user_id, chat_id)

    if not state:
        return False

    s = state.get("state", "")
    if not s.startswith("awaiting_rename_"):
        return False

    entity   = s.replace("awaiting_rename_", "")
    new_name = (message.text or "").strip()
    clear_state(user_id, chat_id)

    if not new_name or len(new_name) < 2 or len(new_name) > 30:
        bot.reply_to(message, "❌ الاسم يجب أن يكون بين 2 و30 حرفاً.")
        return True

    ok, msg = _apply_rename(user_id, entity, new_name)
    bot.reply_to(message, msg, parse_mode="HTML")
    return True


def _apply_rename(user_id: int, entity: str, new_name: str) -> tuple[bool, str]:
    conn = get_db_conn()
    cursor = conn.cursor()

    try:
        if entity == "city":
            city = get_user_city(user_id)
            if not city:
                return False, "❌ ليس لديك مدينة."
            city = dict(city)
            # تحقق من التكرار داخل نفس الدولة فقط
            if city.get("country_id"):
                cursor.execute(
                    "SELECT id FROM cities WHERE country_id = ? AND LOWER(name) = LOWER(?) AND id != ?",
                    (city["country_id"], new_name, city["id"])
                )
                if cursor.fetchone():
                    return False, f"❌ يوجد مدينة باسم <b>{new_name}</b> في دولتك مسبقاً."
            cursor.execute("UPDATE cities SET name = ? WHERE id = ?", (new_name, city["id"]))
            old_name = city["name"]

        elif entity == "country":
            country = get_country_by_owner(user_id)
            if not country:
                return False, "❌ ليس لديك دولة."
            country = dict(country)
            cursor.execute("SELECT id FROM countries WHERE LOWER(name) = LOWER(?) AND id != ?",
                           (new_name, country["id"]))
            if cursor.fetchone():
                return False, f"❌ اسم الدولة <b>{new_name}</b> مستخدم مسبقاً."
            cursor.execute("UPDATE countries SET name = ? WHERE id = ?",
                           (new_name, country["id"]))
            old_name = country["name"]

        elif entity == "alliance":
            from database.db_queries.alliances_queries import get_alliance_by_user
            alliance = get_alliance_by_user(user_id)
            if not alliance:
                return False, "❌ لست في أي تحالف."
            alliance = dict(alliance)
            if alliance.get("leader_id") != user_id:
                return False, "❌ فقط قائد التحالف يمكنه تغيير الاسم."
            cursor.execute("SELECT id FROM alliances WHERE LOWER(name) = LOWER(?) AND id != ?",
                           (new_name, alliance["id"]))
            if cursor.fetchone():
                return False, f"❌ اسم التحالف <b>{new_name}</b> مستخدم مسبقاً."
            cursor.execute("UPDATE alliances SET name = ? WHERE id = ?",
                           (new_name, alliance["id"]))
            old_name = alliance["name"]
        else:
            return False, "❌ كيان غير معروف."

        # خصم التكلفة وتسجيل الكولداون
        if not deduct_user_balance(user_id, RENAME_COST):
            conn.rollback()
            return False, "❌ رصيدك غير كافٍ."

        conn.commit()
        _set_rename_cooldown(user_id, f"rename_{entity}")
        log_event("renamed", user=user_id, entity=entity,
                  old_name=old_name, new_name=new_name)

        labels = {"city": "المدينة", "country": "الدولة", "alliance": "التحالف"}
        return True, (
            f"✅ تم تغيير اسم {labels.get(entity, '')} بنجاح!\n"
            f"📝 الاسم القديم: <b>{old_name}</b>\n"
            f"✨ الاسم الجديد: <b>{new_name}</b>\n"
            f"💰 خُصم: <b>{RENAME_COST} {CURRENCY_ARABIC_NAME}</b>"
        )

    except Exception as e:
        conn.rollback()
        return False, f"❌ خطأ: {e}"


def _can_rename(user_id: int, action_key: str) -> bool:
    conn = get_db_conn()
    cursor = conn.cursor()
    day_ago = int(time.time()) - RENAME_COOLDOWN
    cursor.execute(
        "SELECT id FROM action_cooldowns WHERE user_id = ? AND action = ? AND last_time > ?",
        (user_id, action_key, day_ago)
    )
    return cursor.fetchone() is None


def _set_rename_cooldown(user_id: int, action_key: str):
    conn = get_db_conn()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        INSERT INTO action_cooldowns (user_id, action, last_time)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, action) DO UPDATE SET last_time = excluded.last_time
    """, (user_id, action_key, now))
    conn.commit()
