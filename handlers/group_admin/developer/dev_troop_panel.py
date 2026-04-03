"""
Developer War Management Panel
Manages troop_types and equipment_types from inside the bot.
Hub: Troops | Equipment
Single-message UX — all navigation uses edit_ui.
"""
from core.bot import bot
from handlers.group_admin.permissions import is_developer
from database.connection import get_db_conn
from database.db_queries.war_queries import (
    get_all_troop_types, get_troop_type_by_id,
    get_all_equipment_types, get_equipment_type_by_id,
)
from utils.pagination import (
    btn, edit_ui, send_ui, register_action,
    set_state, get_state, clear_state, build_keyboard, grid
)

GREEN = "su"
RED   = "d"
BLUE  = "p"

_FIELD_LABELS = {
    "attack":    "⚔️ الهجوم",
    "defense":   "🛡 الدفاع",
    "hp":        "❤️ الصحة",
    "speed":     "💨 السرعة",
    "base_cost": "💰 السعر",
}

_EQ_FIELD_LABELS = {
    "attack_bonus":  "⚔️ مكافأة الهجوم",
    "defense_bonus": "🛡 مكافأة الدفاع",
    "base_cost":     "💰 السعر",
    "maintenance_cost": "🔧 الصيانة",
}

_TROOP_TEMPLATE = (
    "name: \nname_ar: \nemoji: 🪖\n"
    "attack: 5\ndefense: 5\nhp: 100\nspeed: 1.0\nbase_cost: 10"
)

_EQ_TEMPLATE = (
    "name: \nname_ar: \nemoji: 🛡\n"
    "attack_bonus: 0\ndefense_bonus: 0\n"
    "special_effect: \nbase_cost: 20\nmaintenance_cost: 1"
)


# ── helpers ──────────────────────────────────────────────────

def _owner(call):
    return (call.from_user.id, call.message.chat.id)

def _grid(n, cols=2):
    layout, rem = [], n
    while rem > 0:
        layout.append(min(cols, rem))
        rem -= cols
    return layout or [1]

def _back_btn(action, data, owner):
    return [btn("رجوع", action, data, color=RED, owner=owner)]

def _set_await(uid, cid, msg_id, state_name, data):
    set_state(uid, cid, state_name, data={**data, "_mid": msg_id})

def _edit_panel(chat_id, msg_id, text, buttons, layout, owner_id):
    markup = build_keyboard(buttons, layout, owner_id) if buttons else None
    try:
        bot.edit_message_text(text, chat_id, msg_id,
                              reply_markup=markup, parse_mode="HTML")
    except Exception:
        pass


# ══════════════════════════════════════════
# Entry — Hub (Troops | Equipment)
# ══════════════════════════════════════════

def open_troop_dev_panel(message):
    if not is_developer(message):
        bot.reply_to(message, "❌ هذا القسم خاص بالمطور")
        return
    _show_war_hub_new(message)


def _show_war_hub_new(message):
    owner = (message.from_user.id, message.chat.id)
    text  = "🪖 إدارة نظام الحرب\n━━━━━━━━━━━━━━━\nاختر القسم:"
    buttons = [
        btn("🪖 الجنود",  "dev_troop_menu",     color=GREEN, owner=owner),
        btn("🛡 المعدات", "dev_equipment_menu",  color=BLUE,  owner=owner),
    ]
    send_ui(message.chat.id, text=text, buttons=buttons,
            layout=[2], owner_id=message.from_user.id)


def _show_war_hub(call):
    owner = _owner(call)
    text  = "🪖 إدارة نظام الحرب\n━━━━━━━━━━━━━━━\nاختر القسم:"
    buttons = [
        btn("🪖 الجنود",  "dev_troop_menu",    color=GREEN, owner=owner),
        btn("🛡 المعدات", "dev_equipment_menu", color=BLUE,  owner=owner),
    ]
    edit_ui(call, text=text, buttons=buttons, layout=[2])


def _back_btn(action, data, owner):
    return [btn("رجوع", action, data, color=RED, owner=owner)]

def _set_await(uid, cid, msg_id, state_name, data):
    set_state(uid, cid, state_name, data={**data, "_mid": msg_id})

def _edit_panel(chat_id, msg_id, text, buttons, layout, owner_id):
    markup = build_keyboard(buttons, layout, owner_id) if buttons else None
    try:
        bot.edit_message_text(text, chat_id, msg_id,
                              reply_markup=markup, parse_mode="HTML")
    except Exception:
        pass

def _troop_block(t: dict) -> str:
    return (
        f"🪖 {t['emoji']} {t['name_ar']}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"<code>"
        f"name: {t['name']}\n"
        f"name_ar: {t['name_ar']}\n"
        f"emoji: {t['emoji']}\n"
        f"attack: {t['attack']}\n"
        f"defense: {t['defense']}\n"
        f"hp: {t['hp']}\n"
        f"speed: {t['speed']}\n"
        f"base_cost: {t['base_cost']}"
        f"</code>"
    )


def _show_troop_menu(call):
    troops = [dict(t) for t in get_all_troop_types()]
    owner  = _owner(call)
    text   = "🪖 إدارة الجنود\n━━━━━━━━━━━━━━━\nاختر نوع الجنود للتعديل:"
    buttons = [
        btn(f"{t['emoji']} {t['name_ar']}", "dev_troop_edit",
            {"tid": t["id"]}, color=BLUE, owner=owner)
        for t in troops
    ]
    buttons.append(btn("➕ إضافة جندي جديد", "dev_troop_add", color=GREEN, owner=owner))
    buttons.append(btn("رجوع", "dev_war_hub", color=RED, owner=owner))
    edit_ui(call, text=text, buttons=buttons, layout=_grid(len(troops), 2) + [1, 1])


# ══════════════════════════════════════════
# View / Edit troop
# ══════════════════════════════════════════

@register_action("dev_troop_menu")
def handle_dev_troop_menu(call, data):
    from core.config import developers_id
    if call.from_user.id not in developers_id:
        bot.answer_callback_query(call.id, "❌ هذا القسم خاص بالمطور", show_alert=True)
        return
    _show_troop_menu(call)


@register_action("dev_war_hub")
def handle_dev_war_hub(call, data):
    _show_war_hub(call)


@register_action("dev_troop_edit")
def handle_dev_troop_edit(call, data):
    tid   = data.get("tid")
    owner = _owner(call)
    t     = get_troop_type_by_id(tid)
    if not t:
        bot.answer_callback_query(call.id, "❌ القوة غير موجودة", show_alert=True)
        return

    text = _troop_block(t)
    buttons = [
        btn("✏️ الهجوم",   "dev_troop_field", {"tid": tid, "f": "attack"},    color=BLUE,  owner=owner),
        btn("✏️ الدفاع",   "dev_troop_field", {"tid": tid, "f": "defense"},   color=BLUE,  owner=owner),
        btn("✏️ الصحة",    "dev_troop_field", {"tid": tid, "f": "hp"},        color=BLUE,  owner=owner),
        btn("✏️ السعر",    "dev_troop_field", {"tid": tid, "f": "base_cost"}, color=BLUE,  owner=owner),
        btn("🗑 حذف",      "dev_troop_delete", {"tid": tid},                  color=RED,   owner=owner),
        btn("رجوع",        "dev_troop_menu",   {},                            color=RED,   owner=owner),
    ]
    edit_ui(call, text=text, buttons=buttons, layout=[2, 2, 1, 1])


# ══════════════════════════════════════════
# Edit single field
# ══════════════════════════════════════════

@register_action("dev_troop_field")
def handle_dev_troop_field(call, data):
    tid   = data.get("tid")
    field = data.get("f")
    owner = _owner(call)
    mid   = call.message.message_id

    t = get_troop_type_by_id(tid)
    if not t:
        bot.answer_callback_query(call.id, "❌ القوة غير موجودة", show_alert=True)
        return

    label   = _FIELD_LABELS.get(field, field)
    current = t[field]

    _set_await(call.from_user.id, call.message.chat.id, mid,
               "dev_troop_field_input", {"tid": tid, "f": field})
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=(f"✏️ تعديل {label}\n"
                  f"━━━━━━━━━━━━━━━\n"
                  f"القيمة الحالية: <code>{current}</code>\n\n"
                  f"أرسل القيمة الجديدة:"),
            buttons=_back_btn("dev_troop_edit", {"tid": tid}, owner),
            layout=[1])


# ══════════════════════════════════════════
# Add new troop
# ══════════════════════════════════════════

@register_action("dev_troop_add")
def handle_dev_troop_add(call, data):
    owner = _owner(call)
    mid   = call.message.message_id
    _set_await(call.from_user.id, call.message.chat.id, mid, "dev_troop_add_input", {})
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=f"➕ إضافة قوة جديدة\n━━━━━━━━━━━━━━━\nأرسل البيانات:\n\n<code>{_TROOP_TEMPLATE}</code>",
            buttons=_back_btn("dev_troop_menu", {}, owner),
            layout=[1])


# ══════════════════════════════════════════
# Delete troop — confirm then delete
# ══════════════════════════════════════════

@register_action("dev_troop_delete")
def handle_dev_troop_delete(call, data):
    tid   = data.get("tid")
    owner = _owner(call)
    t     = get_troop_type_by_id(tid)
    if not t:
        bot.answer_callback_query(call.id, "❌ القوة غير موجودة", show_alert=True)
        return

    text = (f"🗑 حذف القوة: {t['emoji']} {t['name_ar']}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"⚠️ هل أنت متأكد؟ سيتم حذف هذه القوة نهائياً.")
    buttons = [
        btn("✅ تأكيد الحذف", "dev_troop_delete_confirm", {"tid": tid}, color=RED,  owner=owner),
        btn("إلغاء",          "dev_troop_edit",            {"tid": tid}, color=BLUE, owner=owner),
    ]
    edit_ui(call, text=text, buttons=buttons, layout=[1, 1])


@register_action("dev_troop_delete_confirm")
def handle_dev_troop_delete_confirm(call, data):
    tid  = data.get("tid")
    conn = get_db_conn()
    conn.cursor().execute("DELETE FROM troop_types WHERE id=?", (tid,))
    conn.commit()
    bot.answer_callback_query(call.id, "✅ تم حذف القوة")
    _show_troop_menu(call)


# ══════════════════════════════════════════
# Text input handler — called from handle_dev_input
# ══════════════════════════════════════════

def handle_troop_dev_input(uid, cid, text, s, sdata) -> bool:
    """
    Returns True if the state was handled here.
    Called from the main handle_dev_input dispatcher.
    """
    mid   = sdata.get("_mid")
    owner = (uid, cid)
    conn  = get_db_conn()
    cur   = conn.cursor()

    def _done(result_text, back_action, back_data):
        if mid:
            _edit_panel(cid, mid, result_text,
                        _back_btn(back_action, back_data, owner), [1], uid)

    # ── Edit single troop field ───────────────────────────────
    if s == "dev_troop_field_input":
        tid   = sdata.get("tid")
        field = sdata.get("f")
        label = _FIELD_LABELS.get(field, field)
        try:
            value = float(text)
            cur.execute(f"UPDATE troop_types SET {field}=? WHERE id=?", (value, tid))
            conn.commit()
            _done(f"✅ تم تعديل {label} إلى {value}", "dev_troop_edit", {"tid": tid})
        except ValueError:
            _done(f"❌ قيمة غير صالحة: {text}", "dev_troop_edit", {"tid": tid})
        except Exception as e:
            _done(f"❌ خطأ: {e}", "dev_troop_edit", {"tid": tid})
        return True

    # ── Add new troop ─────────────────────────────────────────
    if s == "dev_troop_add_input":
        fields = _parse_fields(text)
        try:
            cur.execute("""
                INSERT INTO troop_types
                (name, name_ar, emoji, attack, defense, hp, speed, base_cost)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                fields.get("name", "new_troop"),
                fields.get("name_ar", "قوة جديدة"),
                fields.get("emoji", "🪖"),
                float(fields.get("attack", 5)),
                float(fields.get("defense", 5)),
                float(fields.get("hp", 100)),
                float(fields.get("speed", 1.0)),
                float(fields.get("base_cost", 10)),
            ))
            conn.commit()
            _done(f"✅ تم إضافة القوة: {fields.get('name_ar', '')}", "dev_troop_menu", {})
        except Exception as e:
            _done(f"❌ خطأ: {e}", "dev_troop_menu", {})
        return True

    # ── Equipment states ──────────────────────────────────────
    if s.startswith("dev_eq_"):
        return _handle_eq_input(uid, cid, text, s, sdata, cur, conn, owner, _done)

    return False


# ── field parser ─────────────────────────────────────────────

def _parse_fields(text: str) -> dict:
    result = {}
    for line in text.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if k and v:
                result[k] = v
    return result


# ══════════════════════════════════════════
# 🛡 Equipment Management
# ══════════════════════════════════════════

def _eq_block(e: dict) -> str:
    return (
        f"🛡 {e['emoji']} {e['name_ar']}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"<code>"
        f"name: {e['name']}\n"
        f"name_ar: {e['name_ar']}\n"
        f"emoji: {e['emoji']}\n"
        f"attack_bonus: {e['attack_bonus']}\n"
        f"defense_bonus: {e['defense_bonus']}\n"
        f"special_effect: {e.get('special_effect') or ''}\n"
        f"base_cost: {e['base_cost']}\n"
        f"maintenance_cost: {e['maintenance_cost']}"
        f"</code>"
    )


def _show_equipment_menu(call):
    equipment = [dict(e) for e in get_all_equipment_types()]
    owner     = _owner(call)
    text      = "🛡 إدارة المعدات\n━━━━━━━━━━━━━━━\nاختر نوع المعدات للتعديل:"
    buttons   = [
        btn(f"{e['emoji']} {e['name_ar']}", "dev_eq_edit",
            {"eid": e["id"]}, color=BLUE, owner=owner)
        for e in equipment
    ]
    buttons.append(btn("➕ إضافة معدة جديدة", "dev_eq_add", color=GREEN, owner=owner))
    buttons.append(btn("رجوع", "dev_war_hub", color=RED, owner=owner))
    edit_ui(call, text=text, buttons=buttons, layout=_grid(len(equipment), 2) + [1, 1])


@register_action("dev_equipment_menu")
def handle_dev_equipment_menu(call, data):
    from core.config import developers_id
    if call.from_user.id not in developers_id:
        bot.answer_callback_query(call.id, "❌ هذا القسم خاص بالمطور", show_alert=True)
        return
    _show_equipment_menu(call)


@register_action("dev_eq_edit")
def handle_dev_eq_edit(call, data):
    eid   = data.get("eid")
    owner = _owner(call)
    e     = get_equipment_type_by_id(eid)
    if not e:
        bot.answer_callback_query(call.id, "❌ المعدة غير موجودة", show_alert=True)
        return
    buttons = [
        btn("✏️ مكافأة الهجوم",  "dev_eq_field", {"eid": eid, "f": "attack_bonus"},    color=BLUE, owner=owner),
        btn("✏️ مكافأة الدفاع",  "dev_eq_field", {"eid": eid, "f": "defense_bonus"},   color=BLUE, owner=owner),
        btn("✏️ السعر",           "dev_eq_field", {"eid": eid, "f": "base_cost"},       color=BLUE, owner=owner),
        btn("✏️ الصيانة",         "dev_eq_field", {"eid": eid, "f": "maintenance_cost"},color=BLUE, owner=owner),
        btn("🗑 حذف",             "dev_eq_delete", {"eid": eid},                        color=RED,  owner=owner),
        btn("رجوع",               "dev_equipment_menu", {},                             color=RED,  owner=owner),
    ]
    edit_ui(call, text=_eq_block(e), buttons=buttons, layout=[2, 2, 1, 1])


@register_action("dev_eq_field")
def handle_dev_eq_field(call, data):
    eid   = data.get("eid")
    field = data.get("f")
    owner = _owner(call)
    mid   = call.message.message_id
    e     = get_equipment_type_by_id(eid)
    if not e:
        bot.answer_callback_query(call.id, "❌ المعدة غير موجودة", show_alert=True)
        return
    label   = _EQ_FIELD_LABELS.get(field, field)
    current = e[field]
    _set_await(call.from_user.id, call.message.chat.id, mid,
               "dev_eq_field_input", {"eid": eid, "f": field})
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=(f"✏️ تعديل {label}\n━━━━━━━━━━━━━━━\n"
                  f"القيمة الحالية: <code>{current}</code>\n\nأرسل القيمة الجديدة:"),
            buttons=_back_btn("dev_eq_edit", {"eid": eid}, owner), layout=[1])


@register_action("dev_eq_add")
def handle_dev_eq_add(call, data):
    owner = _owner(call)
    mid   = call.message.message_id
    _set_await(call.from_user.id, call.message.chat.id, mid, "dev_eq_add_input", {})
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=f"➕ إضافة معدة جديدة\n━━━━━━━━━━━━━━━\nأرسل البيانات:\n\n<code>{_EQ_TEMPLATE}</code>",
            buttons=_back_btn("dev_equipment_menu", {}, owner), layout=[1])


@register_action("dev_eq_delete")
def handle_dev_eq_delete(call, data):
    eid   = data.get("eid")
    owner = _owner(call)
    e     = get_equipment_type_by_id(eid)
    if not e:
        bot.answer_callback_query(call.id, "❌ المعدة غير موجودة", show_alert=True)
        return
    text = (f"🗑 حذف المعدة: {e['emoji']} {e['name_ar']}\n━━━━━━━━━━━━━━━\n⚠️ هل أنت متأكد؟")
    buttons = [
        btn("✅ تأكيد الحذف", "dev_eq_delete_confirm", {"eid": eid}, color=RED,  owner=owner),
        btn("إلغاء",          "dev_eq_edit",            {"eid": eid}, color=BLUE, owner=owner),
    ]
    edit_ui(call, text=text, buttons=buttons, layout=[1, 1])


@register_action("dev_eq_delete_confirm")
def handle_dev_eq_delete_confirm(call, data):
    eid  = data.get("eid")
    conn = get_db_conn()
    conn.cursor().execute("DELETE FROM equipment_types WHERE id=?", (eid,))
    conn.commit()
    bot.answer_callback_query(call.id, "✅ تم حذف المعدة")
    _show_equipment_menu(call)


# ── equipment input states ────────────────────────────────────

def _handle_eq_input(uid, cid, text, s, sdata, cur, conn, owner, _done_fn):
    mid = sdata.get("_mid")

    if s == "dev_eq_field_input":
        eid   = sdata.get("eid")
        field = sdata.get("f")
        label = _EQ_FIELD_LABELS.get(field, field)
        try:
            value = float(text)
            cur.execute(f"UPDATE equipment_types SET {field}=? WHERE id=?", (value, eid))
            conn.commit()
            _done_fn(f"✅ تم تعديل {label} إلى {value}", "dev_eq_edit", {"eid": eid})
        except ValueError:
            _done_fn(f"❌ قيمة غير صالحة: {text}", "dev_eq_edit", {"eid": eid})
        except Exception as e:
            _done_fn(f"❌ خطأ: {e}", "dev_eq_edit", {"eid": eid})
        return True

    if s == "dev_eq_add_input":
        fields = _parse_fields(text)
        try:
            cur.execute("""
                INSERT INTO equipment_types
                (name, name_ar, emoji, attack_bonus, defense_bonus,
                 special_effect, base_cost, maintenance_cost)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                fields.get("name", "new_eq"),
                fields.get("name_ar", "معدة جديدة"),
                fields.get("emoji", "🛡"),
                float(fields.get("attack_bonus", 0)),
                float(fields.get("defense_bonus", 0)),
                fields.get("special_effect", None),
                float(fields.get("base_cost", 20)),
                float(fields.get("maintenance_cost", 1)),
            ))
            conn.commit()
            _done_fn(f"✅ تم إضافة المعدة: {fields.get('name_ar', '')}", "dev_equipment_menu", {})
        except Exception as e:
            _done_fn(f"❌ خطأ: {e}", "dev_equipment_menu", {})
        return True

    return False
