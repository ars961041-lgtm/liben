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
    "gift_awaiting_asset_qty",
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

    # Route news commands to the new news handler
    if text == "الأخبار":
        from modules.magazine.news_handler import handle_news_command
        return handle_news_command(message)

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
        btn("⬅️ القائمة الرئيسية", "adm_main_back", {}, owner=owner, color="d"),
    ]
    if call:
        edit_ui(call, text=text, buttons=buttons, layout=[1, 1, 1, 1])
    else:
        send_ui(cid, text=text, buttons=buttons, layout=[1, 1, 1, 1], owner_id=uid)


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

# هدية معلقة في الذاكرة: uid → pending dict
_PENDING_GIFTS: dict[int, dict] = {}

# أنواع الهدايا البسيطة (قيمة واحدة)
SIMPLE_GIFT_TYPES = {
    "money":      f"💰 رصيد {CURRENCY_ARABIC_NAME}",
    "city_level": "🏙 رفع مستوى المدن",
    "troops":     "🪖 جنود (كل الأنواع)",
    "equipment":  "🛡 معدات (كل الأنواع)",
}

# للتوافق مع الكود القديم الذي يستخدم GIFT_TYPES
GIFT_TYPES = SIMPLE_GIFT_TYPES

def _get_sectors():
    from database.db_queries.assets_queries import get_all_sectors
    try:
        return get_all_sectors()
    except Exception:
        return []

def _asset_items_summary(items: list) -> str:
    if not items:
        return "  (لا يوجد)"
    return "\n".join(
        f"  • {i.get('emoji','')} {i['asset_name']}: +{i['qty']}"
        for i in items
    )


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
    from core.admin import is_primary_dev as _is_primary
    uid = message.from_user.id
    cid = message.chat.id
    if not _is_primary(uid):
        bot.reply_to(message, "❌ هذا الأمر للمطور الأساسي فقط.")
        return
    owner = (uid, cid)
    _render_gift_menu(cid, uid, owner, reply_to=message.message_id, from_admin=False)


def _render_gift_menu(cid, uid, owner, call=None, reply_to=None, from_admin=True):
    pending = _PENDING_GIFTS.get(uid)
    pending_line = ""
    has_pending = False
    if pending:
        gt = pending.get("type", "")
        if gt == "asset_gift" and pending.get("items"):
            n = len(pending["items"])
            pending_line = f"\n\n⏳ <b>هدية أصول معلقة:</b> {n} عنصر مختار"
            has_pending = True
        elif gt != "asset_gift" and pending.get("value"):
            label = SIMPLE_GIFT_TYPES.get(gt, gt)
            pending_line = f"\n\n⏳ <b>هدية معلقة:</b> {label} — {pending['value']}"
            has_pending = True

    text = f"🎁 <b>إرسال هدية للاعبين</b>\n{get_lines()}{pending_line}\n\nاختر نوع الهدية:"

    buttons = [btn(label, "gift_select", {"gt": gt}, owner=owner)
               for gt, label in SIMPLE_GIFT_TYPES.items()]

    for s in _get_sectors():
        label = f"{s.get('emoji','')} {s['name']} (أصول)"
        buttons.append(btn(label, "gift_sector",
                           {"sid": s["id"], "sname": s["name"], "semoji": s.get("emoji", "")},
                           owner=owner))

    if has_pending:
        buttons += [
            btn("👁 معاينة وإرسال", "gift_preview", {}, owner=owner, color="su"),
            btn("🗑 إلغاء الهدية",  "gift_cancel",  {}, owner=owner, color="d"),
        ]

    buttons.append(btn("❌ إغلاق", "gift_close", {}, owner=owner, color="d"))
    if from_admin:
        buttons.append(btn("⬅️ القائمة الرئيسية", "adm_main_back", {}, owner=owner, color="d"))
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
        "troops":     "🪖 أرسل عدد الجنود (لكل نوع) لكل مدينة (رقم):",
        "equipment":  "🛡 أرسل عدد المعدات (لكل نوع) لكل مدينة (رقم):",
    }
    set_state(uid, cid, "gift_awaiting_amount",
              data={"gt": gt, "_mid": call.message.message_id})
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(prompts[gt], cid, call.message.message_id, parse_mode="HTML")
    except Exception:
        pass


@register_action("gift_sector")
def on_gift_sector(call, data):
    if not is_primary_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط", show_alert=True)
        return
    uid    = call.from_user.id
    cid    = call.message.chat.id
    owner  = (uid, cid)
    sid    = int(data["sid"])
    sname  = data.get("sname", "")
    semoji = data.get("semoji", "")

    pending = _PENDING_GIFTS.get(uid)
    if not pending or pending.get("type") != "asset_gift":
        _PENDING_GIFTS[uid] = {"type": "asset_gift", "items": [], "note": "",
                                "sector_label": f"{semoji} {sname}"}

    from database.db_queries.assets_queries import get_assets_by_sector
    assets = get_assets_by_sector(sid)

    bot.answer_callback_query(call.id)
    text = (f"🏗 <b>اختر أصلاً — {semoji} {sname}</b>\n{get_lines()}\n\n"
            f"اضغط على الأصل الذي تريد إهداءه:")
    buttons = [
        btn(f"{a.get('emoji','')} {a['name_ar']}", "gift_asset_pick",
            {"aid": a["id"], "aname": a["name_ar"], "aemoji": a.get("emoji", ""),
             "sid": sid, "sname": sname, "semoji": semoji},
            owner=owner)
        for a in assets
    ]
    buttons.append(btn("🔙 رجوع", "gift_menu", {}, owner=owner, color="d"))
    edit_ui(call, text=text, buttons=buttons, layout=[1] * len(buttons))


@register_action("gift_asset_pick")
def on_gift_asset_pick(call, data):
    if not is_primary_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط", show_alert=True)
        return
    uid    = call.from_user.id
    cid    = call.message.chat.id
    aname  = data.get("aname", "")
    aemoji = data.get("aemoji", "")

    set_state(uid, cid, "gift_awaiting_asset_qty",
              data={"aid": int(data["aid"]), "aname": aname, "aemoji": aemoji,
                    "sid": data.get("sid"), "sname": data.get("sname"),
                    "semoji": data.get("semoji", ""),
                    "_mid": call.message.message_id})
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(
            f"🔢 أرسل <b>الكمية</b> لـ {aemoji} {aname} لكل مدينة (رقم):",
            cid, call.message.message_id, parse_mode="HTML"
        )
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

    cities = db.get_all_city_ids_with_owner()
    users  = db.get_all_user_ids()
    gt     = pending["type"]
    note   = pending.get("note") or "—"

    if gt == "asset_gift":
        items = pending.get("items", [])
        if not items:
            bot.answer_callback_query(call.id, "❌ لم تختر أي أصل بعد", show_alert=True)
            return
        detail     = f"📦 الأصول:\n{_asset_items_summary(items)}\n\n🏙 عدد المدن: {len(cities)}"
        type_label = f"🏗 هدية أصول — {pending.get('sector_label','')}"
    elif gt == "money":
        val        = pending["value"]
        total      = len(users) * float(val)
        detail     = f"💰 {val} {CURRENCY_ARABIC_NAME} × {len(users)} لاعب = {total:.0f} إجمالاً"
        type_label = SIMPLE_GIFT_TYPES["money"]
    elif gt == "city_level":
        detail     = f"🏙 رفع {pending['value']} مستوى × {len(cities)} مدينة"
        type_label = SIMPLE_GIFT_TYPES["city_level"]
    elif gt == "troops":
        detail     = f"🪖 {pending['value']} جندي (لكل نوع) × {len(cities)} مدينة"
        type_label = SIMPLE_GIFT_TYPES["troops"]
    else:
        detail     = f"🛡 {pending['value']} معدة (لكل نوع) × {len(cities)} مدينة"
        type_label = SIMPLE_GIFT_TYPES.get(gt, gt)

    text = (
        f"🎁 <b>معاينة الهدية</b>\n{get_lines()}\n\n"
        f"النوع: {type_label}\n"
        f"الملاحظة: {note}\n\n"
        f"{detail}\n\n"
        f"⚠️ هل تريد الإرسال الآن؟"
    )
    buttons = [
        btn("✅ إرسال الآن",      "gift_send",      {}, owner=owner, color="su"),
        btn("✏️ تعديل الملاحظة", "gift_edit_note",  {}, owner=owner),
        btn("❌ إلغاء",           "gift_cancel",     {}, owner=owner, color="d"),
    ]
    if gt == "asset_gift":
        buttons.insert(1, btn("➕ إضافة أصل آخر", "gift_menu", {}, owner=owner))
    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons, layout=[1] * len(buttons))


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

    gt    = pending.get("type", "")
    label = ("🏗 هدية أصول" if gt == "asset_gift"
             else SIMPLE_GIFT_TYPES.get(gt, gt))
    note  = pending.get("note") or ""
    db.add_post(f"🎁 هدية من المطور — {label}", f"{summary}\n{note}", uid)

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
    _render_gift_menu(call.message.chat.id, uid, owner, call=call, from_admin=True)


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
    import logging
    from database.db_queries.bank_queries import update_bank_balance
    from database.db_queries.cities_queries import update_city
    from database.connection import get_db_conn

    log  = logging.getLogger(__name__)
    gt   = pending["type"]
    note = pending.get("note", "")

    try:
        # ── 💰 رصيد ──────────────────────────────────────────
        if gt == "money":
            amount = float(pending["value"])
            users  = db.get_all_user_ids()
            if not users:
                return False, "❌ لا يوجد لاعبون مسجلون."
            applied = 0
            for uid in users:
                try:
                    update_bank_balance(uid, amount)
                    applied += 1
                except Exception as e:
                    log.warning("[GIFT] money uid=%s: %s", uid, e)
            db.log_gift(gt, str(amount), note, sent_by, applied)
            return True, f"💰 تم إضافة {amount:.0f} {CURRENCY_ARABIC_NAME} لـ {applied} لاعب."

        # ── 🏙 رفع مستوى المدن ───────────────────────────────
        elif gt == "city_level":
            levels  = int(float(pending["value"]))
            cities  = db.get_all_city_ids_with_owner()
            if not cities:
                return False, "❌ لا توجد مدن مسجلة."
            conn    = get_db_conn()
            cur     = conn.cursor()
            applied = 0
            for c in cities:
                city_id = c["city_id"]
                try:
                    cur.execute("SELECT level, population FROM cities WHERE id=?", (city_id,))
                    row = cur.fetchone()
                    if not row:
                        continue
                    new_level = (row[0] or 1) + levels
                    new_pop   = int((row[1] or 1000) * (1.1 ** levels))
                    update_city(city_id, level=new_level, population=new_pop)
                    try:
                        cur.execute("""
                            INSERT INTO city_xp (city_id, level, xp, updated_at)
                            VALUES (?, ?, 0, strftime('%s','now'))
                            ON CONFLICT(city_id) DO UPDATE SET
                                level = MAX(level, ?),
                                updated_at = strftime('%s','now')
                        """, (city_id, new_level, new_level))
                        conn.commit()
                    except Exception:
                        pass
                    applied += 1
                except Exception as e:
                    log.warning("[GIFT] city_level city=%s: %s", city_id, e)
            db.log_gift(gt, str(levels), note, sent_by, applied)
            return True, f"🏙 تم رفع مستوى {applied} مدينة بـ {levels} مستوى (مع تحديث السكان)."

        # ── 🪖 جنود (كل الأنواع) ─────────────────────────────
        elif gt == "troops":
            qty    = int(float(pending["value"]))
            cities = db.get_all_city_ids_with_owner()
            if not cities:
                return False, "❌ لا توجد مدن مسجلة."
            from database.db_queries.war_queries import add_city_troops, get_all_troop_types
            troop_types = get_all_troop_types()
            if not troop_types:
                return False, "❌ لا توجد أنواع جنود في قاعدة البيانات."
            applied = 0
            for c in cities:
                for tt in troop_types:
                    try:
                        add_city_troops(c["city_id"], tt["id"], qty)
                    except Exception as e:
                        log.warning("[GIFT] troops city=%s troop=%s: %s", c["city_id"], tt["id"], e)
                applied += 1
            db.log_gift(gt, str(qty), note, sent_by, applied)
            return True, f"🪖 تم إضافة {qty} جندي (لكل نوع) لـ {applied} مدينة."

        # ── 🛡 معدات (كل الأنواع) ────────────────────────────
        elif gt == "equipment":
            qty    = int(float(pending["value"]))
            cities = db.get_all_city_ids_with_owner()
            if not cities:
                return False, "❌ لا توجد مدن مسجلة."
            from database.db_queries.war_queries import add_city_equipment, get_all_equipment_types
            eq_types = get_all_equipment_types()
            if not eq_types:
                return False, "❌ لا توجد أنواع معدات في قاعدة البيانات."
            applied = 0
            for c in cities:
                for et in eq_types:
                    try:
                        add_city_equipment(c["city_id"], et["id"], qty)
                    except Exception as e:
                        log.warning("[GIFT] equipment city=%s eq=%s: %s", c["city_id"], et["id"], e)
                applied += 1
            db.log_gift(gt, str(qty), note, sent_by, applied)
            return True, f"🛡 تم إضافة {qty} معدة (لكل نوع) لـ {applied} مدينة."

        # ── 🏗 هدية أصول محددة ───────────────────────────────
        elif gt == "asset_gift":
            items  = pending.get("items", [])
            cities = db.get_all_city_ids_with_owner()
            if not items:
                return False, "❌ لم يتم تحديد أي أصول."
            if not cities:
                return False, "❌ لا توجد مدن مسجلة."
            from database.db_queries.assets_queries import upsert_city_asset
            applied = 0
            for c in cities:
                city_id = c["city_id"]
                for item in items:
                    try:
                        upsert_city_asset(city_id, item["asset_id"],
                                          level=1, quantity_delta=item["qty"])
                    except Exception as e:
                        log.warning("[GIFT] asset city=%s asset=%s: %s",
                                    city_id, item["asset_id"], e)
                applied += 1
            lines = "\n".join(
                f"  • {i.get('emoji','')} {i['asset_name']}: +{i['qty']}"
                for i in items
            )
            db.log_gift(gt, str(len(items)), note, sent_by, applied)
            log.info("[GIFT] asset_gift %d assets → %d cities", len(items), applied)
            return True, (
                f"✅ تم توزيع الهدية:\n"
                f"{pending.get('sector_label','📦 أصول')}\n"
                f"{lines}\n\n"
                f"🏙 طُبِّق على {applied} مدينة."
            )

    except Exception as e:
        log.exception("[GIFT] unexpected error gt=%s", gt)
        return False, f"❌ خطأ غير متوقع: {e}"

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

    # ── هدية: المبلغ/القيمة (هدايا بسيطة) ──
    if s == "gift_awaiting_amount":
        if not text.replace(".", "").isdigit() or float(text) <= 0:
            _edit("❌ أرسل رقماً صحيحاً أكبر من صفر.")
            return True
        gt = sdata.get("gt")
        if uid in _PENDING_GIFTS:
            _PENDING_GIFTS[uid]["value"] = text
        else:
            _PENDING_GIFTS[uid] = {"type": gt, "value": text, "note": ""}
        set_state(uid, cid, "gift_awaiting_note", data={"_mid": mid})
        _edit(f"✅ القيمة: <b>{text}</b>\n\nأرسل ملاحظة للهدية (أو أرسل <code>-</code> لتخطي):")
        return True

    # ── هدية أصول: الكمية ──
    if s == "gift_awaiting_asset_qty":
        if not text.replace(".", "").isdigit() or float(text) <= 0:
            _edit("❌ أرسل رقماً صحيحاً أكبر من صفر.")
            return True
        qty    = int(float(text))
        aid    = sdata.get("aid")
        aname  = sdata.get("aname", "")
        aemoji = sdata.get("aemoji", "")
        sid    = sdata.get("sid")
        sname  = sdata.get("sname", "")
        semoji = sdata.get("semoji", "")

        pending = _PENDING_GIFTS.get(uid)
        if not pending or pending.get("type") != "asset_gift":
            _PENDING_GIFTS[uid] = {"type": "asset_gift", "items": [], "note": "",
                                    "sector_label": f"{semoji} {sname}"}
            pending = _PENDING_GIFTS[uid]

        # Replace if same asset already added, otherwise append
        items = pending["items"]
        for item in items:
            if item["asset_id"] == aid:
                item["qty"] = qty
                break
        else:
            items.append({"asset_id": aid, "asset_name": aname, "emoji": aemoji, "qty": qty})

        owner = (uid, cid)
        summary = _asset_items_summary(items)
        preview_text = (
            f"✅ <b>تمت إضافة الأصل</b>\n\n"
            f"{aemoji} {aname}: +{qty}\n\n"
            f"<b>الأصول المختارة حتى الآن:</b>\n{summary}\n\n"
            f"اضغط لإضافة المزيد أو للمعاينة والإرسال:"
        )
        buttons = [
            btn("➕ إضافة أصل آخر",  "gift_sector",
                {"sid": sid, "sname": sname, "semoji": semoji}, owner=owner),
            btn("👁 معاينة وإرسال",  "gift_preview", {}, owner=owner, color="su"),
            btn("🗑 إلغاء",          "gift_cancel",  {}, owner=owner, color="d"),
        ]
        if mid:
            try:
                bot.delete_message(cid, mid)
            except Exception:
                pass
        send_ui(cid, text=preview_text, buttons=buttons, layout=[1, 1, 1], owner_id=uid)
        return True

    # ── هدية: الملاحظة ──
    if s == "gift_awaiting_note":
        note = "" if text == "-" else text
        if uid in _PENDING_GIFTS:
            _PENDING_GIFTS[uid]["note"] = note
        owner   = (uid, cid)
        pending = _PENDING_GIFTS.get(uid, {})
        gt      = pending.get("type", "")
        val     = pending.get("value", "")
        label   = SIMPLE_GIFT_TYPES.get(gt, gt)
        preview_text = (
            f"✅ <b>الهدية جاهزة!</b>\n\n"
            f"النوع: {label}\n"
            f"القيمة: {val}\n"
            f"الملاحظة: {note or '—'}\n\n"
            f"اضغط الزر أدناه للمعاينة والإرسال:"
        )
        buttons = [
            btn("👁 معاينة وإرسال", "gift_preview", {}, owner=owner, color="su"),
            btn("🗑 إلغاء",         "gift_cancel",  {}, owner=owner, color="d"),
        ]
        if mid:
            try:
                bot.delete_message(cid, mid)
            except Exception:
                pass
        send_ui(cid, text=preview_text, buttons=buttons, layout=[1, 1], owner_id=uid)
        return True

    return False
