"""
Developer Control Panel — لوحة تحكم المطور
Complete management for Content Hub and Quran System
"""
from core.bot import bot
from core.admin import is_any_dev
from core.state_manager import StateManager
from utils.pagination import (
    btn, send_ui, edit_ui, register_action,
    paginate_list, set_state, get_state, clear_state,
)
from utils.pagination.buttons import build_keyboard
from utils.helpers import get_lines

# Content Hub imports
from modules.content_hub.hub_db import CONTENT_TYPES, TYPE_LABELS, count_rows

# Quran imports
from modules.quran import quran_db as qr_db
from modules.quran import quran_service as qr_svc

_B = "p"   # أزرق
_G = "su"  # أخضر
_R = "d"   # أحمر
_PER_PAGE = 5


# ══════════════════════════════════════════
# MAIN DEVELOPER PANEL
# ══════════════════════════════════════════

def open_developer_panel(message):
    """لوحة المطور — Main entry point"""
    if not is_any_dev(message.from_user.id):
        bot.reply_to(message, "❌ للمطورين فقط.")
        return

    uid = message.from_user.id
    cid = message.chat.id
    owner = (uid, cid)

    text = (
        "🛠️ <b>لوحة تحكم المطور</b>\n"
        f"{get_lines()}\n\n"
        "اختر النظام المراد إدارته:"
    )

    buttons = [
        btn("📚 إدارة المحتوى", "dev_content_hub", {}, color=_B, owner=owner),
        btn("📖 إدارة القرآن",   "dev_quran",       {}, color=_B, owner=owner),
        btn("❌ إغلاق",          "dev_close",       {}, color=_R, owner=owner),
    ]

    send_ui(cid, text=text, buttons=buttons, layout=[1, 1, 1],
            owner_id=uid, reply_to=message.message_id)


@register_action("dev_content_hub")
def on_dev_content_hub(call, data):
    _show_content_hub_panel(call)


@register_action("dev_quran")
def on_dev_quran(call, data):
    _show_quran_dev_panel(call)


@register_action("dev_close")
def on_dev_close(call, data):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


# ══════════════════════════════════════════
# CONTENT HUB DEV PANEL
# ══════════════════════════════════════════

def _show_content_hub_panel(call_or_message):
    """عرض لوحة إدارة المحتوى"""
    uid = call_or_message.from_user.id
    cid = call_or_message.message.chat.id if hasattr(call_or_message, 'message') else call_or_message.chat.id
    owner = (uid, cid)

    text = (
        "📚 <b>إدارة المحتوى</b>\n"
        f"{get_lines()}\n\n"
        "اختر نوع المحتوى:"
    )

    buttons = [
        btn("📜 اقتباسات", "hub_dev_type", {"type": "quotes"},    color=_B, owner=owner),
        btn("😂 نوادر",     "hub_dev_type", {"type": "anecdotes"}, color=_B, owner=owner),
        btn("📖 قصص",      "hub_dev_type", {"type": "stories"},   color=_B, owner=owner),
        btn("🧠 حكم",      "hub_dev_type", {"type": "wisdom"},    color=_B, owner=owner),
        btn("⬅️ رجوع",     "dev_back_main", {},                   color=_R, owner=owner),
    ]

    if hasattr(call_or_message, 'message'):
        edit_ui(call_or_message, text=text, buttons=buttons, layout=[2, 2, 1])
    else:
        send_ui(cid, text=text, buttons=buttons, layout=[2, 2, 1], owner_id=uid)


@register_action("dev_back_main")
def on_dev_back_main(call, data):
    """العودة للوحة الرئيسية"""
    uid = call.from_user.id
    cid = call.message.chat.id
    owner = (uid, cid)

    text = (
        "🛠️ <b>لوحة تحكم المطور</b>\n"
        f"{get_lines()}\n\n"
        "اختر النظام المراد إدارته:"
    )

    buttons = [
        btn("📚 إدارة المحتوى", "dev_content_hub", {}, color=_B, owner=owner),
        btn("📖 إدارة القرآن",   "dev_quran",       {}, color=_B, owner=owner),
        btn("❌ إغلاق",          "dev_close",       {}, color=_R, owner=owner),
    ]

    edit_ui(call, text=text, buttons=buttons, layout=[1, 1, 1])


@register_action("hub_dev_type")
def on_hub_dev_type(call, data):
    """عرض لوحة التحكم لنوع محتوى محدد"""
    # data["type"] يحمل اسم الجدول مباشرة (quotes, anecdotes, stories, wisdom)
    table = data.get("type")

    # التحقق أن الجدول صالح
    valid_tables = set(CONTENT_TYPES.values())
    if table not in valid_tables:
        bot.answer_callback_query(call.id, "❌ نوع محتوى غير صحيح.", show_alert=True)
        return

    uid = call.from_user.id
    cid = call.message.chat.id
    owner = (uid, cid)

    label = TYPE_LABELS.get(table, table)
    text = (
        f"{label}\n"
        f"{get_lines()}\n\n"
        f"اختر العملية:"
    )

    buttons = [
        btn("🔍 بحث",        "hub_dev_search",  {"table": table}, color=_B, owner=owner),
        btn("➕ إضافة",       "hub_dev_add",     {"table": table}, color=_G, owner=owner),
        btn("📋 عرض عشوائي", "hub_dev_random",  {"table": table}, color=_B, owner=owner),
        btn("⬅️ رجوع",       "dev_content_hub", {},               color=_R, owner=owner),
    ]

    edit_ui(call, text=text, buttons=buttons, layout=[2, 2])


# ══════════════════════════════════════════
# CONTENT HUB — SEARCH
# ══════════════════════════════════════════

@register_action("hub_dev_search")
def on_hub_dev_search(call, data):
    """بدء البحث عن محتوى بمعرف"""
    table = data.get("table")
    uid = call.from_user.id
    cid = call.message.chat.id
    owner = (uid, cid)

    set_state(uid, cid, "hub_dev_awaiting_search", data={
        "table": table,
        "_mid": call.message.message_id,
    })

    bot.answer_callback_query(call.id)
    cancel_btn = btn("🚫 إلغاء", "hub_dev_cancel", {}, color=_R, owner=owner)

    try:
        bot.edit_message_text(
            f"🔍 <b>البحث في {TYPE_LABELS.get(table, table)}</b>\n\n"
            f"أرسل رقم (ID) المحتوى:",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=build_keyboard([cancel_btn], [1], uid),
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# CONTENT HUB — ADD
# ══════════════════════════════════════════

@register_action("hub_dev_add")
def on_hub_dev_add(call, data):
    """بدء إضافة محتوى جديد"""
    table = data.get("table")
    uid = call.from_user.id
    cid = call.message.chat.id
    owner = (uid, cid)

    set_state(uid, cid, "hub_dev_awaiting_add", data={
        "table": table,
        "_mid": call.message.message_id,
    })

    bot.answer_callback_query(call.id)
    cancel_btn = btn("🚫 إلغاء", "hub_dev_cancel", {}, color=_R, owner=owner)

    label = TYPE_LABELS.get(table, table)
    try:
        bot.edit_message_text(
            f"✍️ <b>إضافة محتوى إلى {label}</b>\n\n"
            f"أرسل المحتوى.\n"
            f"لإضافة عدة عناصر دفعة واحدة، افصل بينها بـ:\n"
            f"<code>---</code>",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=build_keyboard([cancel_btn], [1], uid),
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# CONTENT HUB — RANDOM VIEW
# ══════════════════════════════════════════

@register_action("hub_dev_random")
def on_hub_dev_random(call, data):
    """عرض محتوى عشوائي للمطور"""
    from modules.content_hub.hub_db import get_random, count_rows

    table = data.get("table")
    uid = call.from_user.id
    cid = call.message.chat.id

    row = get_random(table)
    if not row:
        bot.answer_callback_query(call.id, "❌ لا يوجد محتوى في هذا النوع.", show_alert=True)
        return

    label = TYPE_LABELS.get(table, table)
    total = count_rows(table)
    text = (
        f"{label} — معاينة المطور\n"
        f"{get_lines()}\n\n"
        f"{row['content']}\n\n"
        f"<i>#{row['id']} من {total}</i>"
    )

    # أزرار خاصة بالمطور
    owner = (uid, cid)
    buttons = [
        btn("🔄 تغيير",   "hub_dev_random", {"table": table},                    color=_B, owner=owner),
        btn("✏️ تعديل",   "hub_dev_edit",   {"table": table, "row_id": row["id"]}, color=_B, owner=owner),
        btn("🗑 حذف",     "hub_dev_delete_confirm", {"table": table, "row_id": row["id"]}, color=_R, owner=owner),
        btn("📤 مشاركة", "hub_dev_share",  {"table": table, "row_id": row["id"]}, color=_G, owner=owner),
        btn("⬅️ رجوع",   "hub_dev_type",   {"type": list(CONTENT_TYPES.keys())[list(CONTENT_TYPES.values()).index(table)]}, color=_R, owner=owner),
    ]

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons, layout=[2, 2, 1])


@register_action("hub_dev_edit")
def on_hub_dev_edit(call, data):
    """تعديل محتوى محدد"""
    table = data.get("table")
    row_id = data.get("row_id")
    uid = call.from_user.id
    cid = call.message.chat.id
    owner = (uid, cid)

    set_state(uid, cid, "hub_dev_awaiting_edit", data={
        "table": table,
        "row_id": row_id,
        "_mid": call.message.message_id,
    })

    bot.answer_callback_query(call.id)
    cancel_btn = btn("🚫 إلغاء", "hub_dev_cancel", {}, color=_R, owner=owner)

    try:
        bot.edit_message_text(
            f"✏️ <b>تعديل المحتوى #{row_id}</b>\n\n"
            f"أرسل النص الجديد:",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=build_keyboard([cancel_btn], [1], uid),
        )
    except Exception:
        pass


@register_action("hub_dev_delete_confirm")
def on_hub_dev_delete_confirm(call, data):
    """تأكيد حذف المحتوى"""
    table = data.get("table")
    row_id = data.get("row_id")
    uid = call.from_user.id
    cid = call.message.chat.id
    owner = (uid, cid)

    text = (
        f"🗑️ <b>تأكيد الحذف</b>\n\n"
        f"هل تريد حذف المحتوى #{row_id}؟\n"
        f"⚠️ لا يمكن التراجع عن هذا الإجراء."
    )

    buttons = [
        btn("✅ نعم، احذف", "hub_dev_delete_final", {"table": table, "row_id": row_id}, color=_R, owner=owner),
        btn("❌ إلغاء",      "hub_dev_cancel",       {},                                color=_B, owner=owner),
    ]

    edit_ui(call, text=text, buttons=buttons, layout=[2])


@register_action("hub_dev_delete_final")
def on_hub_dev_delete_final(call, data):
    """تنفيذ حذف المحتوى"""
    from modules.content_hub.hub_db import delete_content

    table = data.get("table")
    row_id = data.get("row_id")

    ok = delete_content(table, row_id)
    msg = "✅ تم الحذف بنجاح." if ok else "❌ فشل في الحذف."

    bot.answer_callback_query(call.id, msg, show_alert=True)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


@register_action("hub_dev_share")
def on_hub_dev_share(call, data):
    """مشاركة المحتوى من لوحة المطور"""
    from modules.content_hub.hub_handler import on_share
    on_share(call, data)


@register_action("hub_dev_cancel")
def on_hub_dev_cancel(call, data):
    """إلغاء العملية الحالية"""
    uid = call.from_user.id
    cid = call.message.chat.id
    clear_state(uid, cid)
    bot.answer_callback_query(call.id, "تم الإلغاء.")
    try:
        bot.delete_message(cid, call.message.message_id)
    except Exception:
        pass


# ══════════════════════════════════════════
# QURAN DEV PANEL
# ══════════════════════════════════════════

def _show_quran_dev_panel(call):
    """عرض لوحة إدارة القرآن"""
    uid = call.from_user.id
    cid = call.message.chat.id
    owner = (uid, cid)

    text = (
        "📖 <b>إدارة القرآن</b>\n"
        f"{get_lines()}\n\n"
        "اختر العملية:"
    )

    buttons = [
        btn("🔍 بحث آية",     "qr_dev_search",     {}, color=_B, owner=owner),
        btn("✏️ تعديل آية",   "qr_dev_edit_ayah",  {}, color=_B, owner=owner),
        btn("📖 تعديل تفسير", "qr_dev_edit_tafseer", {}, color=_B, owner=owner),
        btn("➕ إضافة آيات",   "qr_dev_add_ayat",   {}, color=_B, owner=owner),
        btn("📊 إحصائيات",    "qr_dev_stats",      {}, color=_G, owner=owner),
        btn("⬅️ رجوع",        "dev_back_main",     {}, color=_R, owner=owner),
    ]

    edit_ui(call, text=text, buttons=buttons, layout=[2, 2, 2])


# ══════════════════════════════════════════
# QURAN — SEARCH AYAH
# ══════════════════════════════════════════

@register_action("qr_dev_search")
def on_qr_dev_search(call, data):
    """بدء البحث عن آية"""
    uid = call.from_user.id
    cid = call.message.chat.id
    owner = (uid, cid)

    set_state(uid, cid, "qr_dev_awaiting_search", data={
        "_mid": call.message.message_id,
    })

    bot.answer_callback_query(call.id)
    cancel_btn = btn("🚫 إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner)

    try:
        bot.edit_message_text(
            f"🔍 <b>البحث في القرآن</b>\n\n"
            f"أرسل كلمة أو جزء من الآية أو رقم الآية:",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=build_keyboard([cancel_btn], [1], uid),
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# QURAN — EDIT AYAH
# ══════════════════════════════════════════

@register_action("qr_dev_edit_ayah")
def on_qr_dev_edit_ayah(call, data):
    """بدء تعديل آية"""
    uid = call.from_user.id
    cid = call.message.chat.id
    owner = (uid, cid)

    set_state(uid, cid, "qr_dev_awaiting_edit_ayah", data={
        "_mid": call.message.message_id,
    })

    bot.answer_callback_query(call.id)
    cancel_btn = btn("🚫 إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner)

    try:
        bot.edit_message_text(
            f"✏️ <b>تعديل آية</b>\n\n"
            f"أرسل:\n"
            f"اسم السورة + رقم الآية\n"
            f"أو رقم الآية مباشرة\n\n"
            f"مثال: البقرة 255\n"
            f"أو: 255",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=build_keyboard([cancel_btn], [1], uid),
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# QURAN — EDIT TAFSEER
# ══════════════════════════════════════════

@register_action("qr_dev_edit_tafseer")
def on_qr_dev_edit_tafseer(call, data):
    """بدء تعديل تفسير"""
    uid = call.from_user.id
    cid = call.message.chat.id
    owner = (uid, cid)

    set_state(uid, cid, "qr_dev_awaiting_edit_tafseer", data={
        "_mid": call.message.message_id,
    })

    bot.answer_callback_query(call.id)
    cancel_btn = btn("🚫 إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner)

    try:
        bot.edit_message_text(
            f"📖 <b>تعديل تفسير</b>\n\n"
            f"أرسل رقم الآية:",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=build_keyboard([cancel_btn], [1], uid),
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# QURAN — ADD AYAT
# ══════════════════════════════════════════

@register_action("qr_dev_add_ayat")
def on_qr_dev_add_ayat(call, data):
    """بدء إضافة آيات — يستخدم تدفق qr_dev_add"""
    uid = call.from_user.id
    cid = call.message.chat.id
    owner = (uid, cid)

    StateManager.set(uid, cid, {
        "type":  "qr_dev_add",
        "step":  "await_sura",
        "mid":   call.message.message_id,
        "extra": {},
    }, ttl=300)

    bot.answer_callback_query(call.id)
    cancel_btn = btn("🚫 إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner)

    try:
        bot.edit_message_text(
            "➕ <b>إضافة آيات</b>\n\nأرسل اسم السورة:",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=build_keyboard([cancel_btn], [1], uid),
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# QURAN — STATISTICS
# ══════════════════════════════════════════

@register_action("qr_dev_stats")
def on_qr_dev_stats(call, data):
    """عرض إحصائيات القرآن"""
    total_ayat = qr_db.get_total_ayat()
    total_favs = len(qr_db.get_favorites(call.from_user.id))

    # عد تفاسير كل نوع
    tafseer_counts = {}
    for name, col in qr_db.TAFSEER_TYPES.items():
        cur = qr_db._get_conn().cursor()
        cur.execute(f"SELECT COUNT(*) FROM ayat WHERE {col} IS NOT NULL AND {col} != ''")
        tafseer_counts[name] = cur.fetchone()[0]

    uid = call.from_user.id
    cid = call.message.chat.id
    owner = (uid, cid)

    text = (
        f"📊 <b>إحصائيات القرآن</b>\n"
        f"{get_lines()}\n\n"
        f"📖 إجمالي الآيات: <b>{total_ayat}</b>\n\n"
        f"📚 التفاسير المتاحة:\n"
    )

    for name, count in tafseer_counts.items():
        text += f"• {name}: <b>{count}</b> آية\n"

    text += f"\n⭐️ مفضلتك: <b>{total_favs}</b> آية"

    buttons = [
        btn("⬅️ رجوع", "dev_quran", {}, color=_R, owner=owner),
    ]

    edit_ui(call, text=text, buttons=buttons, layout=[1])


@register_action("qr_dev_cancel")
def on_qr_dev_cancel(call, data):
    """إلغاء العملية الحالية في القرآن"""
    uid = call.from_user.id
    cid = call.message.chat.id
    clear_state(uid, cid)
    bot.answer_callback_query(call.id, "تم الإلغاء.")
    try:
        bot.delete_message(cid, call.message.message_id)
    except Exception:
        pass


# ══════════════════════════════════════════
# INPUT HANDLERS
# ══════════════════════════════════════════

def handle_developer_input(message) -> bool:
    """
    معالج الإدخال النصي للوحة المطور.
    يُفوَّض للمحرك في dev_flows.py.
    """
    from handlers.group_admin.developer.dev_flows import dispatch
    return dispatch(message, message.from_user.id, message.chat.id)


def _show_quran_search_results(message_or_call, uid, cid, query, results, page, mid):
    """عرض نتائج البحث في القرآن مع pagination"""
    items, total_pages = paginate_list(results, page, per_page=_PER_PAGE)
    text = f"🔍 <b>نتائج البحث: {query}</b> ({page+1}/{total_pages})\n{get_lines()}\n\n"
    for r in items:
        text += (
            f"📖 <b>{r['sura_name']}</b> — آية {r['ayah_number']}\n"
            f"{r['text_with_tashkeel']}\n\n"
        )

    owner = (uid, cid)
    buttons = []

    # زر لكل نتيجة
    for r in items:
        buttons.append(btn(
            f"📖 {r['sura_name']} {r['ayah_number']}",
            "qr_dev_select_ayah",
            {"aid": r["id"]},
            color=_B, owner=owner,
        ))

    # أزرار التنقل
    nav = []
    if page > 0:
        nav.append(btn("◀️", "qr_dev_search_page", {"q": query, "p": page - 1}, owner=owner))
    if page < total_pages - 1:
        nav.append(btn("▶️", "qr_dev_search_page", {"q": query, "p": page + 1}, owner=owner))
    nav.append(btn("❌ إغلاق", "qr_dev_cancel", {}, color=_R, owner=owner))

    buttons += nav
    layout = [1] * len(items) + ([len(nav)] if nav else [1])

    if mid:
        try:
            from utils.pagination.buttons import build_keyboard
            bot.edit_message_text(
                text, cid, mid,
                parse_mode="HTML",
                reply_markup=build_keyboard(buttons, layout, uid),
            )
        except Exception:
            pass


@register_action("qr_dev_search_page")
def on_qr_dev_search_page(call, data):
    """التنقل في صفحات نتائج البحث"""
    uid = call.from_user.id
    cid = call.message.chat.id
    query = data.get("q", "")
    page = int(data.get("p", 0))

    results = qr_svc.search(query)
    bot.answer_callback_query(call.id)
    _show_quran_search_results(None, uid, cid, query, results, page, call.message.message_id)


@register_action("qr_dev_select_ayah")
def on_qr_dev_select_ayah(call, data):
    """عرض آية محددة للمطور مع أزرار التحكم"""
    aid = data.get("aid")
    ayah = qr_db.get_ayah(aid)
    if not ayah:
        bot.answer_callback_query(call.id, "❌ الآية غير موجودة.", show_alert=True)
        return

    uid = call.from_user.id
    cid = call.message.chat.id
    owner = (uid, cid)

    text = (
        f"📖 <b>{ayah['sura_name']}</b> — آية {ayah['ayah_number']}\n"
        f"{get_lines()}\n\n"
        f"{ayah['text_with_tashkeel']}\n\n"
        f"{get_lines()}\n"
        f"<i>آية #{ayah['id']}</i>"
    )

    buttons = [
        btn("✏️ تعديل",       "qr_dev_edit_ayah_selected", {"aid": ayah["id"]}, color=_B, owner=owner),
        btn("📖 تعديل تفسير", "qr_dev_edit_tafseer_selected", {"aid": ayah["id"]}, color=_B, owner=owner),
        btn("⬅️ رجوع",        "qr_dev_search", {}, color=_R, owner=owner),
    ]

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons, layout=[2, 1])


@register_action("qr_dev_edit_ayah_selected")
def on_qr_dev_edit_ayah_selected(call, data):
    """تعديل نص الآية المحددة"""
    aid = data.get("aid")
    ayah = qr_db.get_ayah(aid)
    if not ayah:
        bot.answer_callback_query(call.id, "❌ الآية غير موجودة.", show_alert=True)
        return

    uid = call.from_user.id
    cid = call.message.chat.id
    owner = (uid, cid)

    set_state(uid, cid, "qr_dev_edit_ayah_text", data={
        "aid": aid,
        "_mid": call.message.message_id,
    })

    bot.answer_callback_query(call.id)
    cancel_btn = btn("🚫 إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner)

    try:
        bot.edit_message_text(
            f"✏️ <b>تعديل آية #{aid}</b>\n"
            f"<b>{ayah['sura_name']}</b> — آية {ayah['ayah_number']}\n\n"
            f"النص الحالي:\n<code>{ayah['text_with_tashkeel']}</code>\n\n"
            f"أرسل النص الجديد:",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=build_keyboard([cancel_btn], [1], uid),
        )
    except Exception:
        pass


@register_action("qr_dev_edit_tafseer_selected")
def on_qr_dev_edit_tafseer_selected(call, data):
    """اختيار نوع التفسير للتعديل"""
    aid = data.get("aid")
    ayah = qr_db.get_ayah(aid)
    if not ayah:
        bot.answer_callback_query(call.id, "❌ الآية غير موجودة.", show_alert=True)
        return

    _show_tafseer_selection(None, call.from_user.id, call.message.chat.id, ayah, call.message.message_id)


def _show_ayah_for_edit(message, uid, cid, ayah, mid):
    """عرض الآية مع زر التعديل"""
    text = (
        f"📖 <b>{ayah['sura_name']}</b> — آية {ayah['ayah_number']}\n"
        f"{get_lines()}\n\n"
        f"{ayah['text_with_tashkeel']}\n\n"
        f"{get_lines()}\n"
        f"<i>آية #{ayah['id']}</i>"
    )

    owner = (uid, cid)
    buttons = [
        btn("✏️ تعديل النص", "qr_dev_edit_ayah_selected", {"aid": ayah["id"]}, color=_B, owner=owner),
        btn("⬅️ رجوع",       "qr_dev_edit_ayah", {}, color=_R, owner=owner),
    ]

    if mid:
        try:
            from utils.pagination.buttons import build_keyboard
            bot.edit_message_text(
                text, cid, mid,
                parse_mode="HTML",
                reply_markup=build_keyboard(buttons, [2], uid),
            )
        except Exception:
            pass


def _show_tafseer_selection(message, uid, cid, ayah, mid):
    """عرض أزرار اختيار التفسير"""
    text = (
        f"📖 <b>تعديل تفسير</b>\n"
        f"<b>{ayah['sura_name']}</b> — آية {ayah['ayah_number']}\n"
        f"{get_lines()}\n\n"
        f"اختر نوع التفسير:"
    )

    owner = (uid, cid)
    buttons = [
        btn(name_ar, "qr_dev_choose_tafseer", {"aid": ayah["id"], "col": col}, color=_B, owner=owner)
        for name_ar, col in qr_db.TAFSEER_TYPES.items()
    ]
    buttons.append(btn("❌ إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner))

    if mid:
        try:
            from utils.pagination.buttons import build_keyboard
            bot.edit_message_text(
                text, cid, mid,
                parse_mode="HTML",
                reply_markup=build_keyboard(buttons, [2, 2, 1], uid),
            )
        except Exception:
            pass


@register_action("qr_dev_choose_tafseer")
def on_qr_dev_choose_tafseer(call, data):
    """اختيار نوع التفسير وبدء التعديل"""
    aid = data.get("aid")
    col = data.get("col")
    ayah = qr_db.get_ayah(aid)
    if not ayah:
        bot.answer_callback_query(call.id, "❌ الآية غير موجودة.", show_alert=True)
        return

    uid = call.from_user.id
    cid = call.message.chat.id
    owner = (uid, cid)

    name_ar = next((k for k, v in qr_db.TAFSEER_TYPES.items() if v == col), col)
    current = ayah.get(col) or "(لا يوجد تفسير)"

    set_state(uid, cid, "qr_dev_edit_tafseer_text", data={
        "aid": aid,
        "col": col,
        "_mid": call.message.message_id,
    })

    bot.answer_callback_query(call.id)
    cancel_btn = btn("🚫 إلغاء", "qr_dev_cancel", {}, color=_R, owner=owner)

    try:
        bot.edit_message_text(
            f"📖 <b>تعديل تفسير {name_ar}</b>\n"
            f"<b>{ayah['sura_name']}</b> — آية {ayah['ayah_number']}\n\n"
            f"التفسير الحالي:\n<i>{current[:200]}</i>\n\n"
            f"أرسل التفسير الجديد:",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=build_keyboard([cancel_btn], [1], uid),
        )
    except Exception:
        pass
