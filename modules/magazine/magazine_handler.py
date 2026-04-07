"""
المجلة اليومية + نظام الهدايا للمطور.

أوامر المستخدم:
  المجلة / مجلة اليوم  → عرض منشورات اليوم

أوامر المطور (عبر لوحة الإدارة):
  إضافة منشور          → يضيف منشوراً للمجلة
  هدية                 → يفتح معالج الهدايا
"""
import time
from core.bot import bot
from core.admin import is_any_dev, is_primary_dev
from utils.pagination import (
    btn, send_ui, edit_ui, register_action,
    set_state, get_state, clear_state, paginate_list
)
from utils.helpers import get_lines
from modules.magazine import magazine_db as db
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

# ── حالات الانتظار المعالجة هنا ──
_STATES = {
    "mag_awaiting_title",
    "mag_awaiting_body",
    "gift_awaiting_amount",
    "gift_awaiting_note",
}


# ══════════════════════════════════════════
# 📰 المجلة اليومية — أوامر المستخدم
# ══════════════════════════════════════════

def handle_magazine_command(message) -> bool:
    text = (message.text or "").strip()
    if text not in ("المجلة", "مجلة اليوم", "الأخبار"):
        return False

    uid   = message.from_user.id
    cid   = message.chat.id
    posts = db.get_today_posts()

    if not posts:
        bot.reply_to(message, "📰 لا توجد أخبار اليوم.\nتابعنا لاحقاً!")
        return True

    _send_magazine(cid, uid, posts, page=0,
                   reply_to=message.message_id)
    return True


def _send_magazine(cid, uid, posts, page=0, reply_to=None, call=None):
    items, total_pages = paginate_list(posts, page, per_page=3)
    owner = (uid, cid)

    text = f"📰 <b>مجلة اليوم</b>  ({page+1}/{total_pages})\n{get_lines()}\n\n"
    for p in items:
        ts = time.strftime("%H:%M", time.localtime(p["created_at"]))
        text += f"🔹 <b>{p['title']}</b>  [{ts}]\n{p['body']}\n\n"

    nav = []
    if page > 0:
        nav.append(btn("◀️", "mag_page", {"p": page-1}, owner=owner))
    if page < total_pages - 1:
        nav.append(btn("▶️", "mag_page", {"p": page+1}, owner=owner))
    nav.append(btn("❌ إغلاق", "mag_close", {}, owner=owner, color="d"))

    layout = [len(nav)] if nav else [1]

    if call:
        edit_ui(call, text=text, buttons=nav, layout=layout)
    else:
        send_ui(cid, text=text, buttons=nav, layout=layout,
                owner_id=uid, reply_to=reply_to)


@register_action("mag_page")
def on_mag_page(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    page  = int(data.get("p", 0))
    posts = db.get_today_posts()
    if not posts:
        bot.answer_callback_query(call.id, "لا توجد منشورات.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    _send_magazine(cid, uid, posts, page=page, call=call)


@register_action("mag_close")
def on_mag_close(call, data):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


# ══════════════════════════════════════════
# 📰 لوحة المطور — إدارة المجلة
# ══════════════════════════════════════════

def open_magazine_admin(cid, uid, call=None):
    posts = db.get_all_posts(limit=5)
    owner = (uid, cid)
    text  = f"📰 <b>إدارة المجلة</b>\n{get_lines()}\n\n"
    if posts:
        for p in posts[:3]:
            ts = time.strftime("%m/%d %H:%M", time.localtime(p["created_at"]))
            text += f"• [{p['id']}] <b>{p['title']}</b> — {ts}\n"
    else:
        text += "لا توجد منشورات بعد.\n"

    buttons = [
        btn("➕ إضافة منشور", "mag_adm_add",  {}, owner=owner, color="su"),
        btn("📋 كل المنشورات","mag_adm_list", {"p": 0}, owner=owner),
        btn("🎁 إرسال هدية",  "gift_menu",    {}, owner=owner, color="p"),
    ]
    if call:
        edit_ui(call, text=text, buttons=buttons, layout=[1, 1, 1])
    else:
        send_ui(cid, text=text, buttons=buttons, layout=[1, 1, 1], owner_id=uid)


@register_action("mag_adm_add")
def on_mag_adm_add(call, data):
    if not is_any_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return
    uid = call.from_user.id
    cid = call.message.chat.id
    set_state(uid, cid, "mag_awaiting_title",
              data={"_mid": call.message.message_id})
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("📰 أرسل <b>عنوان</b> المنشور:",
                              cid, call.message.message_id, parse_mode="HTML")
    except Exception:
        pass


@register_action("mag_adm_list")
def on_mag_adm_list(call, data):
    if not is_any_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return
    uid   = call.from_user.id
    cid   = call.message.chat.id
    page  = int(data.get("p", 0))
    owner = (uid, cid)
    posts = db.get_all_posts(limit=50)
    items, total_pages = paginate_list(posts, page, per_page=5)

    text = f"📋 <b>كل المنشورات</b> ({page+1}/{total_pages})\n{get_lines()}\n\n"
    buttons = []
    for p in items:
        ts = time.strftime("%m/%d", time.localtime(p["created_at"]))
        text += f"• [{p['id']}] {p['title']} — {ts}\n"
        buttons.append(btn(f"🗑 {p['id']}", "mag_adm_delete",
                           {"id": p["id"], "p": page}, owner=owner, color="d"))

    nav = []
    if page > 0:
        nav.append(btn("◀️", "mag_adm_list", {"p": page-1}, owner=owner))
    if page < total_pages - 1:
        nav.append(btn("▶️", "mag_adm_list", {"p": page+1}, owner=owner))
    nav.append(btn("🔙 رجوع", "mag_adm_back", {}, owner=owner))

    layout = [1] * len(buttons) + ([len(nav)] if nav else [1])
    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons + nav, layout=layout)


@register_action("mag_adm_delete")
def on_mag_adm_delete(call, data):
    if not is_primary_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط", show_alert=True)
        return
    db.delete_post(int(data["id"]))
    bot.answer_callback_query(call.id, "✅ تم الحذف", show_alert=True)
    on_mag_adm_list(call, {"p": data.get("p", 0)})


@register_action("mag_adm_back")
def on_mag_adm_back(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    bot.answer_callback_query(call.id)
    open_magazine_admin(cid, uid, call=call)


# ══════════════════════════════════════════
# 🎁 نظام الهدايا
# ══════════════════════════════════════════

# هدية معلقة في الذاكرة: uid → {type, value, note}
_PENDING_GIFTS: dict[int, dict] = {}

GIFT_TYPES = {
    "money":      f"💰 رصيد {CURRENCY_ARABIC_NAME}",
    "city_level": "🏙 رفع مستوى المدن",
    "troops":     "🪖 جنود للمدن",
}


@register_action("gift_menu")
def on_gift_menu(call, data):
    if not is_primary_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط", show_alert=True)
        return
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)
    bot.answer_callback_query(call.id)
    _render_gift_menu(cid, uid, owner, call=call)


def open_gift_from_message(message):
    """يفتح قائمة الهدايا من رسالة نصية (/developer_gift أو هدية)."""
    from core.admin import is_primary_dev as _is_primary
    uid = message.from_user.id
    cid = message.chat.id
    if not _is_primary(uid):
        bot.reply_to(message, "❌ هذا الأمر للمطور الأساسي فقط.")
        return
    owner = (uid, cid)
    _render_gift_menu(cid, uid, owner, reply_to=message.message_id)


def _render_gift_menu(cid, uid, owner, call=None, reply_to=None):
    """يبني ويرسل/يعدّل قائمة الهدايا."""
    pending = _PENDING_GIFTS.get(uid)
    pending_line = ""
    if pending and pending.get("value"):
        pending_line = (
            f"\n\n⏳ <b>هدية معلقة:</b> {GIFT_TYPES.get(pending['type'],'')} "
            f"— {pending['value']}"
        )

    text = f"🎁 <b>إرسال هدية للاعبين</b>\n{get_lines()}{pending_line}\n\nاختر نوع الهدية:"
    buttons = [
        btn(label, "gift_select", {"gt": gt}, owner=owner)
        for gt, label in GIFT_TYPES.items()
    ]
    if pending and pending.get("value"):
        buttons += [
            btn("👁 معاينة وإرسال", "gift_preview", {}, owner=owner, color="su"),
            btn("🗑 إلغاء الهدية",  "gift_cancel",  {}, owner=owner, color="d"),
        ]
    buttons.append(btn("❌ إغلاق", "gift_close", {}, owner=owner, color="d"))
    layout = [1] * len(buttons)

    if call:
        edit_ui(call, text=text, buttons=buttons, layout=layout)
    else:
        send_ui(cid, text=text, buttons=buttons, layout=layout,
                owner_id=uid, reply_to=reply_to)


@register_action("gift_select")
def on_gift_select(call, data):
    if not is_primary_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط", show_alert=True)
        return
    uid = call.from_user.id
    cid = call.message.chat.id
    gt  = data["gt"]
    _PENDING_GIFTS[uid] = {"type": gt, "value": None, "note": ""}

    prompts = {
        "money":      f"💰 أرسل مبلغ {CURRENCY_ARABIC_NAME} لكل لاعب (رقم):",
        "city_level": "🏙 أرسل عدد مستويات الرفع لكل مدينة (رقم):",
        "troops":     "🪖 أرسل عدد الجنود لكل مدينة (رقم):",
    }
    set_state(uid, cid, "gift_awaiting_amount",
              data={"gt": gt, "_mid": call.message.message_id})
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(prompts[gt], cid, call.message.message_id,
                              parse_mode="HTML")
    except Exception:
        pass


@register_action("gift_preview")
def on_gift_preview(call, data):
    if not is_primary_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط", show_alert=True)
        return
    uid     = call.from_user.id
    cid     = call.message.chat.id
    owner   = (uid, cid)
    pending = _PENDING_GIFTS.get(uid)
    if not pending:
        bot.answer_callback_query(call.id, "❌ لا توجد هدية معلقة", show_alert=True)
        return

    users  = db.get_all_user_ids()
    cities = db.get_all_city_ids_with_owner()
    gt     = pending["type"]
    val    = pending["value"]
    note   = pending["note"] or "—"

    if gt == "money":
        recipients = len(users)
        total      = recipients * float(val)
        detail     = f"💰 {val} {CURRENCY_ARABIC_NAME} × {recipients} لاعب = {total:.0f} {CURRENCY_ARABIC_NAME} إجمالاً"
    elif gt == "city_level":
        recipients = len(cities)
        detail     = f"🏙 رفع {val} مستوى × {recipients} مدينة"
    else:
        recipients = len(cities)
        detail     = f"🪖 {val} جندي × {recipients} مدينة"

    text = (
        f"🎁 <b>معاينة الهدية</b>\n{get_lines()}\n\n"
        f"النوع: {GIFT_TYPES[gt]}\n"
        f"القيمة: {val}\n"
        f"الملاحظة: {note}\n"
        f"المستفيدون: {recipients}\n\n"
        f"{detail}\n\n"
        f"⚠️ هل تريد الإرسال الآن؟"
    )
    buttons = [
        btn("✅ إرسال الآن", "gift_send",   {}, owner=owner, color="su"),
        btn("✏️ تعديل الملاحظة", "gift_edit_note", {}, owner=owner),
        btn("❌ إلغاء",     "gift_cancel",  {}, owner=owner, color="d"),
    ]
    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons, layout=[1, 1, 1])


@register_action("gift_edit_note")
def on_gift_edit_note(call, data):
    if not is_primary_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌", show_alert=True)
        return
    uid = call.from_user.id
    cid = call.message.chat.id
    set_state(uid, cid, "gift_awaiting_note",
              data={"_mid": call.message.message_id})
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("✏️ أرسل ملاحظة الهدية (تظهر في المجلة):",
                              cid, call.message.message_id, parse_mode="HTML")
    except Exception:
        pass


@register_action("gift_send")
def on_gift_send(call, data):
    if not is_primary_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط", show_alert=True)
        return
    uid     = call.from_user.id
    cid     = call.message.chat.id
    pending = _PENDING_GIFTS.pop(uid, None)
    if not pending:
        bot.answer_callback_query(call.id, "❌ لا توجد هدية معلقة", show_alert=True)
        return

    bot.answer_callback_query(call.id, "⏳ جاري التوزيع...")
    ok, summary = _distribute_gift(pending, uid)

    # أضف للمجلة تلقائياً
    note = pending.get("note") or ""
    title = f"🎁 هدية من المطور — {GIFT_TYPES[pending['type']]}"
    body  = f"{summary}\n{note}"
    db.add_post(title, body, uid)

    try:
        bot.edit_message_text(
            f"{'✅' if ok else '⚠️'} <b>نتيجة التوزيع</b>\n{get_lines()}\n\n{summary}",
            cid, call.message.message_id, parse_mode="HTML"
        )
    except Exception:
        pass


@register_action("gift_cancel")
def on_gift_cancel(call, data):
    uid = call.from_user.id
    _PENDING_GIFTS.pop(uid, None)
    bot.answer_callback_query(call.id, "✅ تم الإلغاء")
    owner = (uid, call.message.chat.id)
    _render_gift_menu(call.message.chat.id, uid, owner, call=call)


@register_action("gift_close")
def on_gift_close(call, data):
    _PENDING_GIFTS.pop(call.from_user.id, None)
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


# ══════════════════════════════════════════
# توزيع الهدية
# ══════════════════════════════════════════

def _distribute_gift(pending: dict, sent_by: int) -> tuple[bool, str]:
    from database.db_queries.bank_queries import update_bank_balance
    from database.db_queries.cities_queries import update_city

    gt  = pending["type"]
    val = pending["value"]
    note = pending.get("note", "")

    try:
        if gt == "money":
            amount = float(val)
            users  = db.get_all_user_ids()
            for uid in users:
                try:
                    update_bank_balance(uid, amount)
                except Exception:
                    pass
            db.log_gift(gt, str(val), note, sent_by, len(users))
            return True, f"💰 تم إضافة {amount:.0f} {CURRENCY_ARABIC_NAME} لـ {len(users)} لاعب."

        elif gt == "city_level":
            levels = int(val)
            cities = db.get_all_city_ids_with_owner()
            for c in cities:
                try:
                    from database.db_queries.cities_queries import get_user_city_details
                    from database.connection import get_db_conn
                    conn = get_db_conn()
                    cur  = conn.cursor()
                    cur.execute("SELECT level FROM cities WHERE id=?", (c["city_id"],))
                    row = cur.fetchone()
                    current = row[0] if row else 1
                    update_city(c["city_id"], level=current + levels)
                except Exception:
                    pass
            db.log_gift(gt, str(val), note, sent_by, len(cities))
            return True, f"🏙 تم رفع مستوى {len(cities)} مدينة بـ {levels} مستوى."

        elif gt == "troops":
            qty    = int(val)
            cities = db.get_all_city_ids_with_owner()
            from database.db_queries.war_queries import add_city_troops
            from database.connection import get_db_conn
            conn = get_db_conn()
            cur  = conn.cursor()
            cur.execute("SELECT id FROM troop_types LIMIT 1")
            troop_row = cur.fetchone()
            if not troop_row:
                return False, "❌ لا توجد أنواع جنود محددة."
            troop_id = troop_row[0]
            for c in cities:
                try:
                    add_city_troops(c["city_id"], troop_id, qty)
                except Exception:
                    pass
            db.log_gift(gt, str(val), note, sent_by, len(cities))
            return True, f"🪖 تم إضافة {qty} جندي لـ {len(cities)} مدينة."

    except Exception as e:
        return False, f"❌ خطأ: {e}"

    return False, "❌ نوع هدية غير معروف."


# ══════════════════════════════════════════
# معالج الإدخال النصي
# ══════════════════════════════════════════

def handle_magazine_input(message) -> bool:
    uid   = message.from_user.id
    cid   = message.chat.id
    state = get_state(uid, cid)
    if not state or state.get("state") not in _STATES:
        return False

    s     = state["state"]
    sdata = state.get("data", {})
    text  = (message.text or "").strip()
    mid   = sdata.get("_mid")
    clear_state(uid, cid)

    try:
        bot.delete_message(cid, message.message_id)
    except Exception:
        pass

    def _edit(msg):
        if mid:
            try:
                bot.edit_message_text(msg, cid, mid, parse_mode="HTML")
            except Exception:
                pass

    # ── إضافة منشور: عنوان ──
    if s == "mag_awaiting_title":
        if not text:
            _edit("❌ العنوان لا يمكن أن يكون فارغاً.")
            return True
        set_state(uid, cid, "mag_awaiting_body",
                  data={"title": text, "_mid": mid})
        _edit(f"📰 العنوان: <b>{text}</b>\n\nأرسل الآن <b>نص</b> المنشور:")
        return True

    # ── إضافة منشور: النص ──
    if s == "mag_awaiting_body":
        title = sdata.get("title", "")
        if not text:
            _edit("❌ النص لا يمكن أن يكون فارغاً.")
            return True
        post_id = db.add_post(title, text, uid)
        _edit(f"✅ تمت إضافة المنشور #{post_id}\n\n<b>{title}</b>\n{text}")
        return True

    # ── هدية: المبلغ/القيمة ──
    if s == "gift_awaiting_amount":
        if not text.replace(".", "").isdigit() or float(text) <= 0:
            _edit("❌ أرسل رقماً صحيحاً أكبر من صفر.")
            return True
        gt = sdata.get("gt")
        if uid in _PENDING_GIFTS:
            _PENDING_GIFTS[uid]["value"] = text
        else:
            _PENDING_GIFTS[uid] = {"type": gt, "value": text, "note": ""}
        # اطلب الملاحظة
        set_state(uid, cid, "gift_awaiting_note", data={"_mid": mid})
        _edit(f"✅ القيمة: <b>{text}</b>\n\nأرسل ملاحظة للهدية (أو أرسل <code>-</code> لتخطي):")
        return True

    # ── هدية: الملاحظة ──
    if s == "gift_awaiting_note":
        note = "" if text == "-" else text
        if uid in _PENDING_GIFTS:
            _PENDING_GIFTS[uid]["note"] = note
        owner = (uid, cid)
        pending = _PENDING_GIFTS.get(uid, {})
        gt  = pending.get("type", "")
        val = pending.get("value", "")
        _edit(
            f"✅ الهدية جاهزة!\n\n"
            f"النوع: {GIFT_TYPES.get(gt,'')}\n"
            f"القيمة: {val}\n"
            f"الملاحظة: {note or '—'}\n\n"
            f"افتح لوحة الإدارة واضغط <b>معاينة وإرسال</b>."
        )
        return True

    return False
