"""
متجر المطورين — إدارة شاملة وتفاعلية لكل أنظمة البوت
"""
from core.bot import bot
from core.admin import is_any_dev, is_primary_dev, set_const
from database.connection import get_db_conn
from utils.pagination import (
    btn, send_ui, edit_ui, register_action,
    paginate_list, set_state, get_state, clear_state,
)
from utils.helpers import get_lines
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME, CURRENCY_ENGLISH_NAME

# ── ألوان الأزرار ──
_B = "p"   # أزرق
_G = "su"  # أخضر
_R = "d"   # أحمر

PER_PAGE = 6   # عناصر لكل صفحة


# ══════════════════════════════════════════
# 🔧 مساعدات مشتركة
# ══════════════════════════════════════════

def _grid(n: int, cols: int = 2) -> list:
    layout, rem = [], n
    while rem > 0:
        layout.append(min(cols, rem))
        rem -= cols
    return layout or [1]


def _back_main(owner):
    return btn("🔙 القائمة الرئيسية", "dev_store_main", {}, color=_R, owner=owner)


def _nav_buttons(page, total_pages, action, extra_data, owner):
    """أزرار التنقل بين الصفحات"""
    nav = []
    if page > 0:
        nav.append(btn("◀️", action, {**extra_data, "p": page - 1}, owner=owner))
    if page < total_pages - 1:
        nav.append(btn("▶️", action, {**extra_data, "p": page + 1}, owner=owner))
    return nav


def _safe_query(sql: str, params: tuple = ()) -> list:
    """تنفيذ استعلام بأمان — يرجع قائمة فارغة عند الخطأ"""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return [dict(r) for r in cursor.fetchall()]
    except Exception as e:
        print(f"[DevStore] query error: {e}")
        return []


def _safe_update(sql: str, params: tuple) -> bool:
    """تنفيذ UPDATE بأمان"""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"[DevStore] update error: {e}")
        return False


def _validate_value(value: str) -> tuple[bool, str]:
    """
    يتحقق من صحة القيمة المُدخلة.
    يرجع (True, cleaned_value) أو (False, error_msg)
    """
    v = value.strip()
    if not v:
        return False, "❌ القيمة لا يمكن أن تكون فارغة."
    # إذا كانت رقمية — تحقق من صحتها
    try:
        float(v)
        return True, v
    except ValueError:
        pass
    # نص عادي — مقبول
    if len(v) > 500:
        return False, "❌ النص طويل جداً (الحد 500 حرف)."
    return True, v


# ══════════════════════════════════════════
# 🏠 القائمة الرئيسية
# ══════════════════════════════════════════

def open_dev_store(message):
    if not is_any_dev(message.from_user.id):
        bot.reply_to(message, "❌ للمطورين فقط.")
        return
    _render_main(message.chat.id, message.from_user.id)


def _render_main(chat_id: int, user_id: int):
    owner = (user_id, chat_id)
    buttons = [
        btn("💰 الاقتصاد والبنك",    "dstore_constants", {"cat": "economy",   "p": 0}, color=_B, owner=owner),
        btn("⚔️ الحرب والمعارك",     "dstore_constants", {"cat": "war",       "p": 0}, color=_R, owner=owner),
        btn("🕵️ الجواسيس",           "dstore_constants", {"cat": "spy",       "p": 0}, color=_B, owner=owner),
        btn("🌍 النفوذ والمواسم",    "dstore_constants", {"cat": "influence", "p": 0}, color=_B, owner=owner),
        btn("🏰 ترقيات التحالفات",   "dstore_alliances", {"p": 0},                    color=_B, owner=owner),
        btn("🪖 القوات والمعدات",    "dstore_troops",    {"tab": "troops",    "p": 0}, color=_R, owner=owner),
        btn("🃏 البطاقات",           "dstore_cards",     {"p": 0},                    color=_B, owner=owner),
        btn("🕵️ عملاء التجسس",      "dstore_spy_agents",{"p": 0},                    color=_B, owner=owner),
    ]
    send_ui(
        chat_id,
        text=f"🛒 <b>متجر المطورين</b>\n{get_lines()}\nاختر النظام الذي تريد إدارته:",
        buttons=buttons,
        layout=_grid(len(buttons), 2),
        owner_id=user_id,
    )


@register_action("dev_store_main")
def back_to_main(call, data):
    if not is_any_dev(call.from_user.id):
        return
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)
    buttons = [
        btn("💰 الاقتصاد والبنك",    "dstore_constants", {"cat": "economy",   "p": 0}, color=_B, owner=owner),
        btn("⚔️ الحرب والمعارك",     "dstore_constants", {"cat": "war",       "p": 0}, color=_R, owner=owner),
        btn("🕵️ الجواسيس",           "dstore_constants", {"cat": "spy",       "p": 0}, color=_B, owner=owner),
        btn("🌍 النفوذ والمواسم",    "dstore_constants", {"cat": "influence", "p": 0}, color=_B, owner=owner),
        btn("🏰 ترقيات التحالفات",   "dstore_alliances", {"p": 0},                    color=_B, owner=owner),
        btn("🪖 القوات والمعدات",    "dstore_troops",    {"tab": "troops",    "p": 0}, color=_R, owner=owner),
        btn("🃏 البطاقات",           "dstore_cards",     {"p": 0},                    color=_B, owner=owner),
        btn("🕵️ عملاء التجسس",      "dstore_spy_agents",{"p": 0},                    color=_B, owner=owner),
    ]
    edit_ui(
        call,
        text=f"🛒 <b>متجر المطورين</b>\n{get_lines()}\nاختر النظام الذي تريد إدارته:",
        buttons=buttons,
        layout=_grid(len(buttons), 2),
    )


# ══════════════════════════════════════════
# ⚙️ ثوابت البوت — مصنفة
# ══════════════════════════════════════════

_CAT_KEYWORDS = {
    "economy":   ["balance", f"{CURRENCY_ENGLISH_NAME}", "salary", "invest", "loan", "transfer",
                  "fee", "reward", "daily", "income", "budget", "sink", "late_game"],
    "war":       ["attack", "defense", "battle", "travel", "sudden", "recovery",
                  "fatigue", "loot", "loss", "repair", "heal", "maintenance",
                  "card_use", "support", "max_level_diff", "ticket"],
    "spy":       ["spy", "scout", "saboteur", "assassin", "exploration",
                  "camouflage", "counter", "intel", "xp"],
    "influence": ["influence", "season", "event", "check_interval",
                  "reputation", "alliance_creation", "country_creation"],
}

_CAT_NAMES = {
    "all":      "كل الثوابت",
    "economy":  "الاقتصاد والبنك",
    "war":      "الحرب والمعارك",
    "spy":      "الجواسيس",
    "influence":"النفوذ والمواسم",
}


def _filter_constants(cat: str) -> list:
    from core.admin import get_all_constants
    all_c = get_all_constants()
    if cat == "all":
        return all_c
    kws = _CAT_KEYWORDS.get(cat, [])
    return [c for c in all_c if any(k in c["name"].lower() for k in kws)]


@register_action("dstore_constants")
def show_constants(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_any_dev(uid):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return

    cat   = data.get("cat", "all")
    page  = int(data.get("p", 0))
    owner = (uid, cid)

    all_items = _filter_constants(cat)
    if not all_items:
        edit_ui(call,
                text=f"⚙️ <b>{_CAT_NAMES.get(cat, cat)}</b>\n\nلا توجد ثوابت في هذه الفئة.",
                buttons=[_back_main(owner)], layout=[1])
        return

    items, total_pages = paginate_list(all_items, page, per_page=PER_PAGE)
    text = (f"⚙️ <b>{_CAT_NAMES.get(cat, cat)}</b> "
            f"({page+1}/{max(1, total_pages)})\n{get_lines()}\n\n")

    buttons = []
    for c in items:
        text += f"🔹 <b>{c['name']}</b> = <code>{c['value']}</code>\n   {c['description']}\n\n"
        if is_primary_dev(uid):
            buttons.append(btn(
                f"✏️ {c['name']}", "dstore_edit_const",
                {"name": c["name"], "cat": cat, "p": page},
                color=_B, owner=owner,
            ))

    nav = _nav_buttons(page, total_pages, "dstore_constants", {"cat": cat}, owner)
    nav.append(_back_main(owner))
    layout = [1] * len(buttons) + ([len(nav)] if nav else [1])
    edit_ui(call, text=text, buttons=buttons + nav, layout=layout)


@register_action("dstore_edit_const")
def prompt_edit_const(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_primary_dev(uid):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط", show_alert=True)
        return

    name  = data["name"]
    cat   = data.get("cat", "all")
    page  = data.get("p", 0)
    owner = (uid, cid)

    # جلب القيمة الحالية
    from core.admin import get_const
    current = get_const(name, "—")

    set_state(uid, cid, "dstore_await_const", data={
        "name": name, "cat": cat, "p": page,
        "_mid": call.message.message_id,
    })
    bot.answer_callback_query(call.id)

    cancel_btn = btn("🚫 إلغاء", "dstore_cancel_edit",
                     {"cat": cat, "p": page, "back": "constants"},
                     color=_R, owner=owner)
    try:
        bot.edit_message_text(
            f"✏️ <b>تعديل الثابت</b>\n\n"
            f"الاسم: <code>{name}</code>\n"
            f"القيمة الحالية: <code>{current}</code>\n\n"
            f"أرسل القيمة الجديدة لـ <b>{name}</b> أو اضغط إلغاء:",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=_single_btn_markup(cancel_btn, uid),
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# 🏰 ترقيات التحالفات
# ══════════════════════════════════════════

@register_action("dstore_alliances")
def show_alliances(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_any_dev(uid):
        return

    page  = int(data.get("p", 0))
    owner = (uid, cid)

    all_items = _safe_query(
        "SELECT * FROM alliance_upgrade_types ORDER BY category, name"
    )

    if not all_items:
        edit_ui(call,
                text="🏰 <b>ترقيات التحالفات</b>\n\nلا توجد ترقيات مسجلة.",
                buttons=[_back_main(owner)], layout=[1])
        return

    items, total_pages = paginate_list(all_items, page, per_page=PER_PAGE)
    text = (f"🏰 <b>ترقيات التحالفات</b> "
            f"({page+1}/{max(1, total_pages)})\n{get_lines()}\n\n")

    buttons = []
    for u in items:
        text += (
            f"{u['emoji']} <b>{u['name_ar']}</b>\n"
            f"   💵 {u['price']:.0f} {CURRENCY_ARABIC_NAME} | مستوى أقصى: {u['max_level']}\n"
            f"   تأثير: +{u['effect_value']} ({u['effect_type']})\n\n"
        )
        if is_primary_dev(uid):
            buttons.append(btn(
                f"✏️ {u['name_ar']}", "dstore_edit_alliance",
                {"uid": u["id"], "p": page},
                color=_B, owner=owner,
            ))

    nav = _nav_buttons(page, total_pages, "dstore_alliances", {}, owner)
    nav.append(_back_main(owner))
    layout = [1] * len(buttons) + ([len(nav)] if nav else [1])
    edit_ui(call, text=text, buttons=buttons + nav, layout=layout)


@register_action("dstore_edit_alliance")
def prompt_edit_alliance(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_primary_dev(uid):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط", show_alert=True)
        return

    uid_item = data["uid"]
    page     = data.get("p", 0)
    owner    = (uid, cid)

    rows = _safe_query("SELECT * FROM alliance_upgrade_types WHERE id=?", (uid_item,))
    if not rows:
        bot.answer_callback_query(call.id, "❌ العنصر غير موجود", show_alert=True)
        return
    row = rows[0]

    set_state(uid, cid, "dstore_await_alliance", data={
        "uid": uid_item, "p": page,
        "_mid": call.message.message_id,
    })
    bot.answer_callback_query(call.id)

    cancel_btn = btn("🚫 إلغاء", "dstore_cancel_edit",
                     {"p": page, "back": "alliances"},
                     color=_R, owner=owner)
    try:
        bot.edit_message_text(
            f"✏️ <b>تعديل ترقية: {row['name_ar']}</b>\n\n"
            f"أرسل الحقول التي تريد تعديلها (سطر لكل حقل):\n\n"
            f"<code>price: {row['price']}\n"
            f"max_level: {row['max_level']}\n"
            f"effect_value: {row['effect_value']}</code>\n\n"
            f"أو اضغط إلغاء:",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=_single_btn_markup(cancel_btn, uid),
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# 🪖 القوات والمعدات
# ══════════════════════════════════════════

@register_action("dstore_troops")
def show_troops(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_any_dev(uid):
        return

    tab   = data.get("tab", "troops")   # "troops" أو "equip"
    page  = int(data.get("p", 0))
    owner = (uid, cid)

    if tab == "troops":
        all_items = _safe_query("SELECT * FROM troop_types ORDER BY base_cost")
        title     = "🪖 أنواع الجنود"
        edit_act  = "dstore_edit_troop"
        def _row_text(item):
            return (
                f"{item.get('emoji','🪖')} <b>{item['name_ar']}</b>\n"
                f"   ⚔️ هجوم: {item.get('attack',0):.0f} | "
                f"🛡 دفاع: {item.get('defense',0):.0f} | "
                f"❤️ HP: {item.get('hp',0):.0f}\n"
                f"   💵 تكلفة: {item.get('base_cost',0):.0f} {CURRENCY_ARABIC_NAME}\n\n"
            )
    else:
        all_items = _safe_query("SELECT * FROM equipment_types ORDER BY base_cost")
        title     = "🔧 أنواع المعدات"
        edit_act  = "dstore_edit_equip"
        def _row_text(item):
            return (
                f"{item.get('emoji','🔧')} <b>{item['name_ar']}</b>\n"
                f"   ⚔️ هجوم: {item.get('attack_bonus',0):.0f} | "
                f"🛡 دفاع: {item.get('defense_bonus',0):.0f}\n"
                f"   💵 تكلفة: {item.get('base_cost',0):.0f} {CURRENCY_ARABIC_NAME}\n\n"
            )

    # تبويب التبديل
    other_tab  = "equip" if tab == "troops" else "troops"
    other_label = "🔧 المعدات" if tab == "troops" else "🪖 الجنود"

    if not all_items:
        edit_ui(call,
                text=f"{title}\n\nلا توجد بيانات. تأكد من تشغيل create_all_tables().",
                buttons=[
                    btn(other_label, "dstore_troops", {"tab": other_tab, "p": 0},
                        color=_B, owner=owner),
                    _back_main(owner),
                ], layout=[1, 1])
        return

    items, total_pages = paginate_list(all_items, page, per_page=PER_PAGE)
    text = f"{title} ({page+1}/{max(1, total_pages)})\n{get_lines()}\n\n"

    buttons = []
    for item in items:
        text += _row_text(item)
        if is_primary_dev(uid):
            buttons.append(btn(
                f"✏️ {item['name_ar']}", edit_act,
                {"id": item["id"], "tab": tab, "p": page},
                color=_B, owner=owner,
            ))

    nav = _nav_buttons(page, total_pages, "dstore_troops", {"tab": tab}, owner)
    nav.append(btn(other_label, "dstore_troops", {"tab": other_tab, "p": 0},
                   color=_B, owner=owner))
    nav.append(_back_main(owner))
    layout = [1] * len(buttons) + ([len(nav)] if nav else [1])
    edit_ui(call, text=text, buttons=buttons + nav, layout=layout)


@register_action("dstore_edit_troop")
def prompt_edit_troop(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_primary_dev(uid):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط", show_alert=True)
        return

    item_id = data["id"]
    tab     = data.get("tab", "troops")
    page    = data.get("p", 0)
    owner   = (uid, cid)

    rows = _safe_query("SELECT * FROM troop_types WHERE id=?", (item_id,))
    if not rows:
        bot.answer_callback_query(call.id, "❌ الجندي غير موجود", show_alert=True)
        return
    row = rows[0]

    set_state(uid, cid, "dstore_await_troop", data={
        "id": item_id, "tab": tab, "p": page,
        "_mid": call.message.message_id,
    })
    bot.answer_callback_query(call.id)

    cancel_btn = btn("🚫 إلغاء", "dstore_cancel_edit",
                     {"tab": tab, "p": page, "back": "troops"},
                     color=_R, owner=owner)
    try:
        bot.edit_message_text(
            f"✏️ <b>تعديل جندي: {row['name_ar']}</b>\n\n"
            f"أرسل الحقول التي تريد تعديلها:\n\n"
            f"<code>base_cost: {row.get('base_cost', 0)}\n"
            f"attack: {row.get('attack', 0)}\n"
            f"defense: {row.get('defense', 0)}\n"
            f"hp: {row.get('hp', 100)}</code>\n\n"
            f"أو اضغط إلغاء:",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=_single_btn_markup(cancel_btn, uid),
        )
    except Exception:
        pass


@register_action("dstore_edit_equip")
def prompt_edit_equip(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_primary_dev(uid):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط", show_alert=True)
        return

    item_id = data["id"]
    tab     = data.get("tab", "equip")
    page    = data.get("p", 0)
    owner   = (uid, cid)

    rows = _safe_query("SELECT * FROM equipment_types WHERE id=?", (item_id,))
    if not rows:
        bot.answer_callback_query(call.id, "❌ المعدة غير موجودة", show_alert=True)
        return
    row = rows[0]

    set_state(uid, cid, "dstore_await_equip", data={
        "id": item_id, "tab": tab, "p": page,
        "_mid": call.message.message_id,
    })
    bot.answer_callback_query(call.id)

    cancel_btn = btn("🚫 إلغاء", "dstore_cancel_edit",
                     {"tab": tab, "p": page, "back": "troops"},
                     color=_R, owner=owner)
    try:
        bot.edit_message_text(
            f"✏️ <b>تعديل معدة: {row['name_ar']}</b>\n\n"
            f"أرسل الحقول التي تريد تعديلها:\n\n"
            f"<code>base_cost: {row.get('base_cost', 0)}\n"
            f"attack_bonus: {row.get('attack_bonus', 0)}\n"
            f"defense_bonus: {row.get('defense_bonus', 0)}\n"
            f"maintenance_cost: {row.get('maintenance_cost', 1)}</code>\n\n"
            f"أو اضغط إلغاء:",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=_single_btn_markup(cancel_btn, uid),
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# 🃏 البطاقات
# ══════════════════════════════════════════

@register_action("dstore_cards")
def show_cards(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_any_dev(uid):
        return

    page  = int(data.get("p", 0))
    owner = (uid, cid)

    all_items = _safe_query("SELECT * FROM cards ORDER BY category, price")

    if not all_items:
        edit_ui(call,
                text="🃏 <b>البطاقات</b>\n\nلا توجد بطاقات مسجلة.",
                buttons=[_back_main(owner)], layout=[1])
        return

    items, total_pages = paginate_list(all_items, page, per_page=PER_PAGE)
    text = f"🃏 <b>البطاقات</b> ({page+1}/{max(1, total_pages)})\n{get_lines()}\n\n"

    buttons = []
    for c in items:
        text += (
            f"{c['emoji']} <b>{c['name_ar']}</b> [{c['category']}]\n"
            f"   📝 {c['description_ar']}\n"
            f"   💵 {c['price']:.0f} {CURRENCY_ARABIC_NAME} | تأثير: {c['effect_value']}\n\n"
        )
        if is_primary_dev(uid):
            buttons.append(btn(
                f"✏️ {c['name_ar']}", "dstore_edit_card",
                {"id": c["id"], "p": page},
                color=_B, owner=owner,
            ))

    nav = _nav_buttons(page, total_pages, "dstore_cards", {}, owner)
    nav.append(_back_main(owner))
    layout = [1] * len(buttons) + ([len(nav)] if nav else [1])
    edit_ui(call, text=text, buttons=buttons + nav, layout=layout)


@register_action("dstore_edit_card")
def prompt_edit_card(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_primary_dev(uid):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط", show_alert=True)
        return

    item_id = data["id"]
    page    = data.get("p", 0)
    owner   = (uid, cid)

    rows = _safe_query("SELECT * FROM cards WHERE id=?", (item_id,))
    if not rows:
        bot.answer_callback_query(call.id, "❌ البطاقة غير موجودة", show_alert=True)
        return
    row = rows[0]

    set_state(uid, cid, "dstore_await_card", data={
        "id": item_id, "p": page,
        "_mid": call.message.message_id,
    })
    bot.answer_callback_query(call.id)

    cancel_btn = btn("🚫 إلغاء", "dstore_cancel_edit",
                     {"p": page, "back": "cards"},
                     color=_R, owner=owner)
    try:
        bot.edit_message_text(
            f"✏️ <b>تعديل بطاقة: {row['name_ar']}</b>\n\n"
            f"أرسل الحقول التي تريد تعديلها:\n\n"
            f"<code>price: {row['price']}\n"
            f"effect_value: {row['effect_value']}\n"
            f"description_ar: {row['description_ar']}</code>\n\n"
            f"أو اضغط إلغاء:",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=_single_btn_markup(cancel_btn, uid),
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# 🕵️ عملاء التجسس (ثوابت)
# ══════════════════════════════════════════

_SPY_KEYS = [
    "spy_cost", "spy_cooldown_sec", "scout_cost", "saboteur_cost",
    "assassin_cost", "spy_xp_per_mission", "spy_level_up_xp", "exploration_cost",
]

@register_action("dstore_spy_agents")
def show_spy_agents(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_any_dev(uid):
        return

    owner = (uid, cid)

    try:
        from core.admin import get_const
        items = [
            {"name": k, "value": get_const(k, "—"),
             "description": k.replace("_", " ")}
            for k in _SPY_KEYS
        ]
    except Exception:
        items = []

    text = f"🕵️ <b>ثوابت نظام الجواسيس</b>\n{get_lines()}\n\n"
    buttons = []
    for c in items:
        text += f"🔹 <b>{c['name']}</b> = <code>{c['value']}</code>\n\n"
        if is_primary_dev(uid):
            buttons.append(btn(
                f"✏️ {c['name']}", "dstore_edit_const",
                {"name": c["name"], "cat": "spy", "p": 0},
                color=_B, owner=owner,
            ))

    buttons.append(_back_main(owner))
    edit_ui(call, text=text, buttons=buttons, layout=[1] * len(buttons))


# ══════════════════════════════════════════
# 🚫 إلغاء التعديل
# ══════════════════════════════════════════

@register_action("dstore_cancel_edit")
def cancel_edit(call, data):
    """يلغي وضع التعديل ويعود للقسم السابق"""
    uid = call.from_user.id
    cid = call.message.chat.id
    clear_state(uid, cid)
    bot.answer_callback_query(call.id, "تم الإلغاء")

    back = data.get("back", "main")
    page = int(data.get("p", 0))

    if back == "constants":
        cat = data.get("cat", "all")
        show_constants(call, {"cat": cat, "p": page})
    elif back == "alliances":
        show_alliances(call, {"p": page})
    elif back == "troops":
        tab = data.get("tab", "troops")
        show_troops(call, {"tab": tab, "p": page})
    elif back == "cards":
        show_cards(call, {"p": page})
    else:
        back_to_main(call, {})


# ══════════════════════════════════════════
# 🔧 مساعد بناء لوحة المفاتيح لزر واحد
# ══════════════════════════════════════════

def _single_btn_markup(button, owner_id: int):
    """يبني InlineKeyboardMarkup لزر واحد"""
    from utils.pagination.buttons import build_keyboard
    return build_keyboard([button], [1], owner_id)


# ══════════════════════════════════════════
# 📝 معالج الإدخال النصي الموحد
# ══════════════════════════════════════════

def handle_dev_store_input(message) -> bool:
    """
    يعالج كل إدخالات متجر المطورين.
    يرجع True إذا تم التعامل مع الرسالة.
    """
    uid = message.from_user.id
    cid = message.chat.id

    if not is_any_dev(uid):
        return False

    state = get_state(uid, cid)
    if not state or "state" not in state:
        return False

    s     = state["state"]
    sdata = state.get("data", {})

    # فقط حالات متجر المطورين
    if not s.startswith("dstore_await_"):
        return False

    raw_text = (message.text or "").strip()
    mid      = sdata.get("_mid")
    clear_state(uid, cid)

    # حذف رسالة المستخدم لإبقاء المحادثة نظيفة
    try:
        bot.delete_message(cid, message.message_id)
    except Exception:
        pass

    # إذا لم يكن نصاً — أعد الحالة وأخبر المستخدم
    if not raw_text:
        owner = (uid, cid)
        cancel_btn = btn("🚫 إلغاء", "dstore_cancel_edit",
                         {"back": "main"}, color=_R, owner=owner)
        set_state(uid, cid, s, data={**sdata, "_mid": mid})
        if mid:
            from utils.pagination.buttons import build_keyboard
            try:
                bot.edit_message_text(
                    "❌ أرسل نصاً فقط. لا يمكن قبول صور أو ملفات.\n\nأرسل القيمة الجديدة أو اضغط إلغاء:",
                    cid, mid, parse_mode="HTML",
                    reply_markup=build_keyboard([cancel_btn], [1], uid),
                )
            except Exception:
                pass
        return True

    # ── دالة تحرير الرسالة الأصلية ──
    def _edit_msg(text: str, extra_buttons: list = None, layout: list = None):
        if not mid:
            return
        from utils.pagination.buttons import build_keyboard
        markup = None
        if extra_buttons:
            markup = build_keyboard(extra_buttons, layout or [1] * len(extra_buttons), uid)
        try:
            bot.edit_message_text(text, cid, mid, parse_mode="HTML",
                                  reply_markup=markup)
        except Exception:
            pass

    # ── دالة بناء أزرار الرجوع بعد التعديل ──
    def _back_buttons(back_action: str, back_data: dict) -> list:
        owner = (uid, cid)
        return [
            btn("🔙 رجوع", back_action, back_data, color=_R, owner=owner),
            _back_main(owner),
        ]

    # ── تحليل حقول متعددة (key: value) ──
    def _parse_fields(txt: str) -> dict:
        result = {}
        for line in txt.splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                k, v = k.strip(), v.strip()
                if k and v:
                    result[k] = v
        return result

    # ── تحديث جدول عام ──
    def _do_update(table: str, fields: dict, row_id) -> tuple[bool, str]:
        if not fields:
            return False, "❌ لم يتم إرسال أي حقول صالحة."
        # التحقق من القيم الرقمية
        for k, v in fields.items():
            try:
                float(v)
            except ValueError:
                pass  # نص عادي — مقبول
        try:
            conn   = get_db_conn()
            cursor = conn.cursor()
            sets   = ", ".join(f"{k}=?" for k in fields)
            cursor.execute(
                f"UPDATE {table} SET {sets} WHERE id=?",
                list(fields.values()) + [row_id],
            )
            conn.commit()
            if cursor.rowcount == 0:
                return False, "❌ لم يتم العثور على العنصر."
            return True, f"✅ تم تعديل {len(fields)} حقل بنجاح."
        except Exception as e:
            return False, f"❌ خطأ في قاعدة البيانات: {e}"

    # ════════════════════════════════════════
    # معالجة كل حالة
    # ════════════════════════════════════════

    # ─── تعديل ثابت (قيمة واحدة) ───
    if s == "dstore_await_const":
        name = sdata.get("name", "")
        cat  = sdata.get("cat", "all")
        page = sdata.get("p", 0)
        owner = (uid, cid)

        ok, val = _validate_value(raw_text)
        if not ok:
            # أعد عرض نموذج التعديل مع رسالة الخطأ
            from core.admin import get_const
            current = get_const(name, "—")
            cancel_btn = btn("🚫 إلغاء", "dstore_cancel_edit",
                             {"cat": cat, "p": page, "back": "constants"},
                             color=_R, owner=owner)
            set_state(uid, cid, "dstore_await_const",
                      data={"name": name, "cat": cat, "p": page, "_mid": mid})
            _edit_msg(
                f"⚠️ {val}\n\n"
                f"✏️ <b>تعديل: {name}</b>\n"
                f"القيمة الحالية: <code>{current}</code>\n\n"
                f"أرسل القيمة الجديدة أو اضغط إلغاء:",
                [cancel_btn], [1],
            )
            return True

        if set_const(name, val):
            back_btns = _back_buttons("dstore_constants", {"cat": cat, "p": page})
            _edit_msg(
                f"✅ <b>تم التحديث بنجاح!</b>\n\n"
                f"الثابت: <code>{name}</code>\n"
                f"القيمة الجديدة: <code>{val}</code>",
                back_btns, [2],
            )
        else:
            back_btns = _back_buttons("dstore_constants", {"cat": cat, "p": page})
            _edit_msg(f"❌ فشل تحديث <b>{name}</b>.", back_btns, [2])
        return True

    # ─── تعديل ترقية تحالف ───
    if s == "dstore_await_alliance":
        uid_item = sdata.get("uid")
        page     = sdata.get("p", 0)
        fields   = _parse_fields(raw_text)
        ok, msg  = _do_update("alliance_upgrade_types", fields, uid_item)
        back_btns = _back_buttons("dstore_alliances", {"p": page})
        _edit_msg(msg, back_btns, [2])
        return True

    # ─── تعديل جندي ───
    if s == "dstore_await_troop":
        item_id  = sdata.get("id")
        tab      = sdata.get("tab", "troops")
        page     = sdata.get("p", 0)
        fields   = _parse_fields(raw_text)
        ok, msg  = _do_update("troop_types", fields, item_id)
        back_btns = _back_buttons("dstore_troops", {"tab": tab, "p": page})
        _edit_msg(msg, back_btns, [2])
        return True

    # ─── تعديل معدة ───
    if s == "dstore_await_equip":
        item_id  = sdata.get("id")
        tab      = sdata.get("tab", "equip")
        page     = sdata.get("p", 0)
        fields   = _parse_fields(raw_text)
        ok, msg  = _do_update("equipment_types", fields, item_id)
        back_btns = _back_buttons("dstore_troops", {"tab": tab, "p": page})
        _edit_msg(msg, back_btns, [2])
        return True

    # ─── تعديل بطاقة ───
    if s == "dstore_await_card":
        item_id  = sdata.get("id")
        page     = sdata.get("p", 0)
        fields   = _parse_fields(raw_text)
        ok, msg  = _do_update("cards", fields, item_id)
        back_btns = _back_buttons("dstore_cards", {"p": page})
        _edit_msg(msg, back_btns, [2])
        return True

    return False
