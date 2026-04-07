from core.bot import bot
from modules.country.invite_ui import handle_join_command
from modules.country.services.country_service import CountryService
from modules.country.services.city_service import CityService
from modules.country.transfer_service import transfer_country, rollback_country_transfer
from database.db_queries.countries_queries import (
    get_country_by_user, get_country_by_owner, get_country_cities_count,
)
from database.db_queries.advanced_war_queries import is_country_frozen
from utils.pagination import btn, edit_ui, register_action, send_ui
from utils.helpers import send_reply
from utils.helpers import get_lines
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME


def country_commands(message):
    if not message.text:
        return False

    text = message.text.strip()
    user_id = message.from_user.id
    chat_id = message.chat.id

    try:
        # ────────────── إنشاء دولة ──────────────
        if text.startswith("إنشاء دولة") or text.startswith("انشاء دولة"):
            success, result_message = CountryService.create_country_from_text(user_id, text)
            bot.reply_to(message, result_message)
            return True

        # ────────────── عرض دولتي ──────────────
        if text == "دولتي":
            _send_country_overview(message, user_id, chat_id)
            return True

        # ────────────── نقل الدولة ──────────────
        if text.startswith("نقل الدولة"):
            _handle_transfer(message, text, user_id)
            return True

        # ────────────── تراجع نقل الدولة ──────────────
        if text in ["تراجع نقل الدولة", "استرجاع الدولة"]:
            ok, msg = rollback_country_transfer(user_id)
            bot.reply_to(message, msg, parse_mode="HTML")
            return True

        # ────────────── ضم عضو لدولتي ──────────────
        if text.startswith("ضم "):
            handle_join_command(message)
            return True

    except ConnectionError:
        raise
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {str(e)}")
        return True

    return False


def _handle_transfer(message, text, user_id):
    """نقل الدولة لمستخدم آخر — يتطلب الرد على رسالته أو ذكر آيديه"""
    from core.bot import bot as _bot
    parts = text.split()
    # نقل الدولة [user_id]
    if len(parts) >= 3 and parts[2].lstrip("-").isdigit():
        to_user_id = int(parts[2])
    elif message.reply_to_message:
        to_user_id = message.reply_to_message.from_user.id
    else:
        _bot.reply_to(message, "❌ استخدم: <code>نقل الدولة [آيدي المستخدم]</code>\nأو رد على رسالة المستخدم.", parse_mode="HTML")
        return

    ok, msg = transfer_country(user_id, to_user_id)
    _bot.reply_to(message, msg, parse_mode="HTML")

# ─────────────────────────────────────────
# دالة عرض الدولة مع الأزرار
# ─────────────────────────────────────────
def _send_country_overview(message, user_id, chat_id):
    country = get_country_by_user(user_id)
    if not country:
        # ── فحص: هل المستخدم عضو في دولة شخص آخر؟ ──
        member_country = _get_member_country(user_id)
        if member_country:
            _send_member_country_view(message, user_id, chat_id, member_country)
            return

        # قد يكون نقل الدولة مؤخراً — تحقق من إمكانية التراجع
        from database.connection import get_db_conn
        import time as _t
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM country_transfers
            WHERE from_user_id = ? AND status = 'active' AND expires_at > ?
            ORDER BY transferred_at DESC LIMIT 1
        """, (user_id, int(_t.time())))
        transfer = cursor.fetchone()
        if transfer:
            transfer = dict(transfer)
            remaining = transfer["expires_at"] - int(_t.time())
            h, m = remaining // 3600, (remaining % 3600) // 60
            buttons = [btn("↩️ تراجع عن النقل", "country_rollback_transfer",
                           data={}, owner=(user_id, chat_id), color="d")]
            send_ui(chat_id,
                    text=(f"🌍 <b>دولتك تم نقلها</b>\n\n"
                          f"⏳ يمكنك التراجع خلال: {h}س {m}د\n"
                          f"💸 التراجع يكلف 20% إضافية من الميزانية"),
                    buttons=buttons, layout=[1], owner_id=user_id)
        else:
            send_reply(msg=message, text="❌ أنت غير منضم لأي دولة.\nاستخدم: <code>انشاء دولة </code>[الاسم]", Shape=False)
        return

    country_id = country["id"]
    frozen, rem = is_country_frozen(country_id)
    freeze_line = ""
    if frozen:
        freeze_line = f"\n🧊 <b>الدولة مجمدة</b> — متبقي: {rem // 3600}س {(rem % 3600) // 60}د"

    stats = _compute_country_stats(country_id)
    text = _country_main_text(country, stats) + freeze_line
    buttons = _country_buttons(country_id, user_id, chat_id, frozen)
    send_ui(message.chat.id, text=text, buttons=buttons, layout=[3, 2, 1], owner_id=user_id)


def _get_member_country(user_id: int):
    """يجلب الدولة التي ينتمي إليها المستخدم كعضو (عبر مدينته)."""
    from database.connection import get_db_conn
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.name, c.owner_id
        FROM cities ci
        JOIN countries c ON ci.country_id = c.id
        WHERE ci.owner_id = ?
        LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def _send_member_country_view(message, user_id, chat_id, country):
    """عرض الدولة لعضو (غير المالك)."""
    country_id  = country["id"]
    owner_id    = country["owner_id"]
    city_count  = get_country_cities_count(country_id)
    frozen, rem = is_country_frozen(country_id)

    # اسم المالك
    try:
        from database.db_queries.users_queries import get_user_name
        owner_name = get_user_name(owner_id) or str(owner_id)
    except Exception:
        owner_name = str(owner_id)

    # تاريخ انضمام المستخدم عبر مدينته
    from database.connection import get_db_conn
    import time as _t
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT created_at FROM cities WHERE owner_id = ? AND country_id = ?",
        (user_id, country_id)
    )
    city_row = cursor.fetchone()
    join_line = ""
    if city_row and city_row["created_at"]:
        join_line = f"\n📅 انضممت: {_t.strftime('%Y-%m-%d', _t.localtime(city_row['created_at']))}"

    freeze_line = ""
    if frozen:
        freeze_line = f"\n🧊 <b>الدولة مجمدة</b> — متبقي: {rem // 3600}س {(rem % 3600) // 60}د"

    stats  = _compute_country_stats(country_id)
    text   = _country_main_text(country, stats)
    text  += (
        f"\n{get_lines()}\n"
        f"✨ أنت عضو في هذه الدولة\n"
        f"👑 مالك الدولة: <b>{owner_name}</b>\n"
        f"🏙 عدد المدن: <b>{city_count}</b>"
        f"{join_line}"
        f"{freeze_line}"
    )

    buttons = _country_buttons(country_id, user_id, chat_id, frozen)
    send_ui(message.chat.id, text=text, buttons=buttons, layout=[3, 2, 1], owner_id=user_id)


def _compute_country_stats(country_id: int) -> dict:
    from database.db_queries.cities_queries import get_cities_by_country
    from database.db_queries.assets_queries import calculate_city_effects, get_country_military_power
    totals = {"economy": 0.0, "health": 0.0, "education": 0.0,
              "infra": 0.0, "income": 0.0, "maintenance": 0.0}
    cities = get_cities_by_country(country_id)
    for city in cities:
        fx = calculate_city_effects(city["id"])
        for k in totals:
            totals[k] += fx.get(k, 0)
    totals["military"] = get_country_military_power(country_id)
    return {k: round(v, 2) for k, v in totals.items()}


def _country_main_text(country, stats=None):
    if stats is None:
        stats = {}

    # ─── مكافأة النفوذ ───
    influence_line = ""
    try:
        from modules.progression.influence import get_influence_progress
        p = get_influence_progress(country["id"])
        if p["points"] > 0:
            influence_line = f"🌍 النفوذ: {p['points']} نقطة (+{p['income_bonus']}% دخل / +{p['war_advantage']}% حرب)\n"
    except Exception:
        pass

    return (
        f"🌍 دولة: {country['name']}\n"
        f"{get_lines()}\n"
        f"💰 الاقتصاد:       {stats.get('economy', 0):.1f}\n"
        f"🏥 الصحة:          {stats.get('health', 0):.1f}\n"
        f"📚 التعليم:         {stats.get('education', 0):.1f}\n"
        f"🪖 القوة العسكرية: {stats.get('military', 0):.1f}\n"
        f"🛣 البنية التحتية:  {stats.get('infra', 0):.1f}\n"
        f"{get_lines()}\n"
        f"📈 الدخل: {stats.get('income', 0):.0f} | 🔧 الصيانة: {stats.get('maintenance', 0):.0f}\n"
        f"{influence_line}"
        f"اضغط على زر لمزيد من التفاصيل"
    )


def _country_buttons(country_id, user_id, chat_id, frozen=False):
    owner = (user_id, chat_id)
    buttons = [
        btn("💰 الاقتصاد", "country_detail", {"t": "economy", "cid": country_id}, owner=owner),
        btn("🏥 الصحة", "country_detail", {"t": "health", "cid": country_id}, owner=owner),
        btn("📚 التعليم", "country_detail", {"t": "education", "cid": country_id}, owner=owner),
        btn("🪖 العسكرية", "country_detail", {"t": "military", "cid": country_id}, owner=owner, color="d"),
        btn("🛣 البنية", "country_detail", {"t": "infra", "cid": country_id}, owner=owner, color="d"),
        btn("🏙 مدن الدولة", "country_cities", {"cid": country_id, "p": 0}, owner=owner, color="su"),
    ]
    if frozen:
        buttons.append(btn("🧊 مجمدة", "country_frozen_info", {"cid": country_id}, owner=owner))
    return buttons


@register_action("country_rollback_transfer")
def handle_rollback_btn(call, data):
    user_id = call.from_user.id
    ok, msg = rollback_country_transfer(user_id)
    bot.answer_callback_query(call.id, msg[:200], show_alert=True)
    try:
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode="HTML")
    except Exception:
        pass


@register_action("country_frozen_info")
def handle_frozen_info(call, data):
    country_id = data.get("cid")
    frozen, rem = is_country_frozen(country_id)
    if frozen:
        bot.answer_callback_query(
            call.id,
            f"🧊 الدولة مجمدة\nالوقت المتبقي: {rem // 3600}س {(rem % 3600) // 60}د",
            show_alert=True
        )
    else:
        bot.answer_callback_query(call.id, "✅ الدولة غير مجمدة")


@register_action("country_detail")
def handle_country_detail(call, data):
    topic = data.get("t")
    country_id = data.get("cid")
    if not country_id:
        bot.answer_callback_query(call.id, "❌ بيانات غير صالحة", show_alert=True)
        return

    from database.connection import get_db_conn
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM countries WHERE id=?", (country_id,))
    row = cursor.fetchone()
    if not row:
        bot.answer_callback_query(call.id, "❌ الدولة غير موجودة", show_alert=True)
        return
    country = dict(row)
    stats = _compute_country_stats(country_id)

    DETAIL_TEXTS = {
        "economy": (
            f"💰 تفاصيل الاقتصاد\n{get_lines()}\n"
            f"نقاط الاقتصاد: {stats.get('economy', 0):.1f}\n"
            f"الدخل الكلي:   {stats.get('income', 0):.0f} {CURRENCY_ARABIC_NAME}\n"
            f"الصيانة:       {stats.get('maintenance', 0):.0f} {CURRENCY_ARABIC_NAME}\n"
            f"الصافي:        {stats.get('income', 0) - stats.get('maintenance', 0):.0f} {CURRENCY_ARABIC_NAME}\n\n"
            f"لتحسينه: شراء مصنع أو بنك محلي أو سوق تجاري في مدينتك"
        ),
        "health": (
            f"🏥 تفاصيل الصحة\n{get_lines()}\n"
            f"مستوى الصحة: {stats.get('health', 0):.1f}\n\n"
            f"لتحسينه: شراء مستشفى أو عيادة في مدينتك"
        ),
        "education": (
            f"📚 تفاصيل التعليم\n{get_lines()}\n"
            f"مستوى التعليم: {stats.get('education', 0):.1f}\n\n"
            f"لتحسينه: شراء مدرسة أو جامعة في مدينتك"
        ),
        "military": (
            f"🪖 تفاصيل القوة العسكرية\n{get_lines()}\n"
            f"القوة العسكرية: {stats.get('military', 0):.1f}\n\n"
            f"لتحسينه: شراء قاعدة عسكرية أو ثكنة عسكرية في مدينتك"
        ),
        "infra": (
            f"🛣 تفاصيل البنية التحتية\n{get_lines()}\n"
            f"مستوى البنية: {stats.get('infra', 0):.1f}\n\n"
            f"لتحسينه: شراء بنية تحتية أو محطة طاقة في مدينتك"
        ),
    }

    detail_text = DETAIL_TEXTS.get(topic, "❌ قسم غير معروف")
    back_buttons = [btn("رجوع", "country_back", {"cid": country_id}, color="w", owner=(call.from_user.id, call.message.chat.id))]
    edit_ui(call, text=detail_text, buttons=back_buttons, layout=[1])


@register_action("country_back")
def handle_country_back(call, data):
    country_id = data.get("cid")
    from database.connection import get_db_conn
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM countries WHERE id=?", (country_id,))
    row = cursor.fetchone()
    if not row:
        bot.answer_callback_query(call.id, "❌ الدولة غير موجودة", show_alert=True)
        return
    country = dict(row)
    stats = _compute_country_stats(country_id)
    edit_ui(call, text=_country_main_text(country, stats),
           buttons=_country_buttons(country_id, call.from_user.id, call.message.chat.id), layout=[3, 2, 1])


@register_action("country_cities")
def handle_country_cities(call, data):
    country_id = data.get("cid")
    page = int(data.get("p", 0))

    from database.db_queries.cities_queries import get_cities_by_country

    cities = get_cities_by_country(country_id)

    if not cities:
        edit_ui(call, text="❌ لا توجد مدن في هذه الدولة.",
                buttons=[btn("⬅️ رجوع", "country_back", {"cid": country_id}, color="w",
                             owner=(call.from_user.id, call.message.chat.id))])
        return

    PER_PAGE = 5
    start = page * PER_PAGE
    end = start + PER_PAGE

    page_items = cities[start:end]
    total_pages = (len(cities) + PER_PAGE - 1) // PER_PAGE

    text = f"🏙 مدن الدولة\n"
    text += f"{get_lines()}\n"
    text += f"📄 صفحة {page+1}/{total_pages}\n\n"

    for c in page_items:
        text += f"• {c['name']}\n"

    buttons = []

    if page < total_pages - 1:
        buttons.append(
            btn("التالي ⬅️", "country_cities", {"cid": country_id, "p": page+1},
                owner=(call.from_user.id, call.message.chat.id))
        )
        
    if page > 0:
        buttons.append(
            btn("➡️ السابق", "country_cities", {"cid": country_id, "p": page-1},
                owner=(call.from_user.id, call.message.chat.id))
        )

    buttons.append(btn("⬅️ رجوع", "country_back", {"cid": country_id}, color="w",
                       owner=(call.from_user.id, call.message.chat.id)))

    edit_ui(call, text=text, buttons=buttons, layout=[2, 1])