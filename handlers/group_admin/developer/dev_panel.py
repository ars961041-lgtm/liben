"""
Developer Management Panel  —  متجر المطور
Single-message UX: every step edits the same message.
msg_id stored in state so handle_dev_input can edit it.
"""
from core.bot import bot
from handlers.group_admin.permissions import is_developer
from database.db_queries.assets_queries import (
    get_all_sectors, get_assets_by_sector,
    get_asset_by_id,
)
from database.connection import get_db_conn
from utils.pagination import send_ui
from utils.pagination import btn, build_keyboard, clear_state, edit_ui, get_state, register_action, set_state
from handlers.group_admin.developer.dev_troop_panel import (
    handle_troop_dev_input, open_troop_dev_panel
)
from utils.helpers import get_lines


GREEN = "su"
RED  = "d"
BLUE  = "p"

_ASSET_TEMPLATE = (
    "name: \nname_ar: \nemoji: 🏗\nbase_price: 100\nbase_value: 1\n"
    "cost_scale: 1.5\nmaintenance: 0\nincome: 0\nmax_level: 10\n"
    "stat_economy: 0\nstat_health: 0\nstat_education: 0\n"
    "stat_military: 0\nstat_infrastructure: 0\n"
    "pop_effect: 0\neco_effect: 0\nprot_effect: 0"
)
_ALIASES = {
    "stat_eco": "stat_economy", "stat_edu": "stat_education",
    "stat_mil": "stat_military", "stat_infra": "stat_infrastructure",
}


# ── helpers ──────────────────────────────────────────────────

def _grid(n, cols=2):
    layout, rem = [], n
    while rem > 0:
        layout.append(min(cols, rem))
        rem -= cols
    return layout or [1]

def _is_emoji_char(s):
    return bool(s) and len(s) <= 2 and ord(s[0]) > 0x2000

def _parse_fields(text):
    result = {}
    for line in text.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if k and v:
                result[k] = v
    return result

def _asset_block(a):
    return (
        f"📋 بيانات العنصر\n{get_lines()}\n<code>"
        f"name: {a['name']}\nname_ar: {a['name_ar']}\nemoji: {a['emoji']}\n"
        f"sector_id: {a['sector_id']}\nbase_price: {a['base_price']}\n"
        f"base_value: {a['base_value']}\ncost_scale: {a['cost_scale']}\n"
        f"maintenance: {a['maintenance']}\nincome: {a['income']}\n"
        f"max_level: {a['max_level']}\nstat_economy: {a['stat_economy']}\n"
        f"stat_health: {a['stat_health']}\nstat_education: {a['stat_education']}\n"
        f"stat_military: {a['stat_military']}\nstat_infrastructure: {a['stat_infrastructure']}\n"
        f"pop_effect: {a['pop_effect']}\neco_effect: {a['eco_effect']}\n"
        f"prot_effect: {a['prot_effect']}</code>"
    )

def _edit_panel(chat_id, msg_id, text, buttons, layout, owner_id):
    """Edit the panel message directly by ID."""
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = build_keyboard(buttons, layout, owner_id) if buttons else None
    try:
        bot.edit_message_text(text, chat_id, msg_id,
                              reply_markup=markup, parse_mode="HTML")
    except Exception:
        pass

def _set_await(uid, cid, msg_id, state_name, data):
    """Store state with the panel message ID so input handler can edit it."""
    set_state(uid, cid, state_name, data={**data, "_mid": msg_id})

def _back_btn(action, data, owner):
    return [btn("رجوع", action, data, color=RED, owner=owner)]


# ══════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════

def open_dev_panel(message):
    if not is_developer(message):
        bot.reply_to(message, "❌ ليس لديك صلاحية")
        return
    _show_sectors_new(message)

def _show_sectors_new(message):
    sectors = get_all_sectors()
    owner   = (message.from_user.id, message.chat.id)
    text    = f"🛠 لوحة المطور\n{get_lines()}\nاختر الجانب:"
    buttons = [
        btn(f"{s['emoji']} {s['name']}", "dev_sector", {"sid": s["id"]}, color=BLUE, owner=owner)
        for s in sectors
    ]
    buttons.append(btn("➕ إضافة جانب",    "dev_add_sector",  color=GREEN, owner=owner))
    buttons.append(btn("🪖 إدارة القوات",  "dev_troop_menu",  color=BLUE,  owner=owner))
    send_ui(message.chat.id, text=text, buttons=buttons,
            layout=_grid(len(sectors), 2) + [1, 1], owner_id=message.from_user.id)

def _show_sectors(call):
    sectors = get_all_sectors()
    owner   = (call.from_user.id, call.message.chat.id)
    text = f"🛠 لوحة المطور\n{get_lines()}\nاختر الجانب:"
    buttons = [
        btn(f"{s['emoji']} {s['name']}", "dev_sector", {"sid": s["id"]}, color=BLUE, owner=owner)
        for s in sectors
    ]
    buttons.append(btn("➕ إضافة جانب",   "dev_add_sector", color=GREEN, owner=owner))
    buttons.append(btn("🪖 إدارة القوات", "dev_troop_menu", color=BLUE,  owner=owner))
    edit_ui(call, text=text, buttons=buttons, layout=_grid(len(sectors), 2) + [1, 1])

# ══════════════════════════════════════════
# Sector actions
# ══════════════════════════════════════════

@register_action("dev_sector")
def _on_sector(call, data):
    sid   = data.get("sid")
    owner = (call.from_user.id, call.message.chat.id)

    row = get_db_conn().cursor().execute(
        "SELECT * FROM asset_sectors WHERE id=?", (sid,)
    ).fetchone()

    if not row:
        bot.answer_callback_query(call.id, "❌ الجانب غير موجود", show_alert=True)
        return

    s = dict(row)

    text = f"🗂 الجانب: {s['emoji']} {s['name']}\nID: {s['id']}"

    buttons = [
        btn("➕ إضافة",       "dev_add_sector",    color=GREEN,  owner=owner),
        btn("✏️ تعديل",       "dev_update_sector", {"sid": sid}, color=BLUE, owner=owner),
        btn("🗑 حذف",         "dev_delete_sector", {"sid": sid}, color=RED, owner=owner),
        btn("📦 عرض العناصر", "dev_assets_list",   {"sid": sid}, color=BLUE, owner=owner),
        btn("رجوع",           "dev_back_sectors",              color=RED, owner=owner),
    ]

    edit_ui(
        call,
        text=text,
        buttons=buttons,
        layout=[2, 2, 1]
    )

@register_action("dev_back_sectors")
def _on_back_sectors(call, data):
    _show_sectors(call)

@register_action("dev_add_sector")
def _on_add_sector(call, data):
    owner = (call.from_user.id, call.message.chat.id)
    mid   = call.message.message_id
    _set_await(call.from_user.id, call.message.chat.id, mid, "dev_sector_add", {})
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text="✏️ أرسل اسم الجانب الجديد\nمثال: <code>سياحة 🏖</code>",
            buttons=_back_btn("dev_back_sectors", {}, owner), layout=[1])

@register_action("dev_update_sector")
def _on_update_sector(call, data):
    sid   = data.get("sid")
    owner = (call.from_user.id, call.message.chat.id)
    mid   = call.message.message_id
    _set_await(call.from_user.id, call.message.chat.id, mid, "dev_sector_update", {"sid": sid})
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text="✏️ أرسل الاسم الجديد للجانب:",
            buttons=_back_btn("dev_sector", {"sid": sid}, owner), layout=[1])

@register_action("dev_delete_sector")
def _on_delete_sector(call, data):
    sid  = data.get("sid")
    conn = get_db_conn()
    cur  = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM assets WHERE sector_id=?", (sid,))
    count = cur.fetchone()[0]
    if count > 0:
        bot.answer_callback_query(
            call.id, f"❌ لا يمكن حذف هذا الجانب لأنه يحتوي على {count} عنصر", show_alert=True)
        return
    cur.execute("DELETE FROM asset_sectors WHERE id=?", (sid,))
    conn.commit()
    bot.answer_callback_query(call.id, "✅ تم حذف الجانب")
    _show_sectors(call)


# ══════════════════════════════════════════
# Assets list + single asset
# ══════════════════════════════════════════

@register_action("dev_assets_list")
def _on_assets_list(call, data):
    sid    = data.get("sid")
    owner  = (call.from_user.id, call.message.chat.id)
    assets = get_assets_by_sector(sid)

    text = "📦 عناصر الجانب:"

    buttons = [
        btn(f"{a['emoji']} {a['name_ar']}", "dev_asset",
            {"aid": a["id"], "sid": sid}, color=BLUE, owner=owner)
        for a in assets
    ]

    buttons += [
        btn("➕ إضافة عنصر", "dev_add_asset", {"sid": sid}, color=GREEN, owner=owner),
        btn("رجوع", "dev_sector", {"sid": sid}, color=RED, owner=owner),
    ]

    edit_ui(
        call,
        text=text,
        buttons=buttons,
        layout=_grid(len(assets), 2) + [1, 1],
    )

@register_action("dev_asset")
def _on_asset(call, data):
    aid   = data.get("aid")
    sid   = data.get("sid")
    owner = (call.from_user.id, call.message.chat.id)

    a = get_asset_by_id(aid)

    if not a:
        bot.answer_callback_query(call.id, "❌ العنصر غير موجود", show_alert=True)
        return

    buttons = [
        btn("➕ إضافة",  "dev_add_asset",    {"sid": sid},             color=GREEN, owner=owner),
        btn("✏️ تعديل",  "dev_update_asset", {"aid": aid, "sid": sid}, color=BLUE, owner=owner),
        btn("🗑 حذف",    "dev_delete_asset", {"aid": aid, "sid": sid}, color=RED, owner=owner),
        btn("رجوع",      "dev_assets_list",  {"sid": sid},             color=RED, owner=owner),
    ]

    edit_ui(
        call,
        text=_asset_block(a),
        buttons=buttons,
        layout=[2, 1, 1]
    )
    
@register_action("dev_add_asset")
def _on_add_asset(call, data):
    sid   = data.get("sid")
    owner = (call.from_user.id, call.message.chat.id)
    mid   = call.message.message_id
    _set_await(call.from_user.id, call.message.chat.id, mid, "dev_asset_add", {"sid": sid})
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=f"✏️ أرسل بيانات العنصر الجديد:\n\n<code>{_ASSET_TEMPLATE}</code>",
            buttons=_back_btn("dev_assets_list", {"sid": sid}, owner), layout=[1])

@register_action("dev_update_asset")
def _on_update_asset(call, data):
    aid   = data.get("aid")
    sid   = data.get("sid")
    owner = (call.from_user.id, call.message.chat.id)
    mid   = call.message.message_id
    a     = get_asset_by_id(aid)
    _set_await(call.from_user.id, call.message.chat.id, mid, "dev_asset_update", {"aid": aid, "sid": sid})
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=f"✏️ عدّل الحقول وأرسلها:\n\n{_asset_block(a)}",
            buttons=_back_btn("dev_asset", {"aid": aid, "sid": sid}, owner), layout=[1])

@register_action("dev_delete_asset")
def _on_delete_asset(call, data):
    aid  = data.get("aid")
    sid  = data.get("sid")
    conn = get_db_conn()
    conn.cursor().execute("DELETE FROM assets WHERE id=?", (aid,))
    conn.commit()
    bot.answer_callback_query(call.id, "✅ تم حذف العنصر")
    _on_assets_list(call, {"sid": sid})


# ══════════════════════════════════════════
# Text input handler
# ══════════════════════════════════════════

def handle_dev_input(message) -> bool:
    if not is_developer(message):
        return False

    uid   = message.from_user.id
    cid   = message.chat.id
    state = get_state(uid, cid)
    if not state or "state" not in state:
        return False

    s = state["state"]

    # ── يتعامل فقط مع حالات dev_panel — يتجاهل حالات الأنظمة الأخرى ──
    _HANDLED_STATES = {
        "dev_sector_add", "dev_sector_update",
        "dev_asset_add",  "dev_asset_update",
    }
    if s not in _HANDLED_STATES and not s.startswith("dev_troop_"):
        return False   # اترك الحالة كما هي لمعالجات أخرى

    # الآن نأخذ البيانات ونمسح الحالة
    sdata = state.get("data", {})
    text  = (message.text or "").strip()
    mid   = sdata.get("_mid")   # get بدلاً من pop — لا نعدّل القاموس
    clear_state(uid, cid)

    # delete developer's input message to keep chat clean
    try:
        bot.delete_message(cid, message.message_id)
    except Exception:
        pass

    conn = get_db_conn()
    cur  = conn.cursor()
    owner = (uid, cid)

    def _done(result_text, back_action, back_data):
        """Edit panel message with result + back button."""
        if mid:
            _edit_panel(cid, mid, result_text,
                        _back_btn(back_action, back_data, owner), [1], uid)

    # ── Sector add ────────────────────────────────────────────
    if s == "dev_sector_add":
        parts = text.split()
        name  = " ".join(p for p in parts if not _is_emoji_char(p)).strip() or text
        emoji = next((p for p in parts if _is_emoji_char(p)), "🏗")
        try:
            cur.execute("INSERT INTO asset_sectors (name, emoji) VALUES (?,?)", (name, emoji))
            conn.commit()
            _done(f"✅ تم إضافة الجانب: {emoji} {name}", "dev_back_sectors", {})
        except Exception as e:
            _done(f"❌ خطأ: {e}", "dev_back_sectors", {})
        return True

    # ── Sector update ─────────────────────────────────────────
    if s == "dev_sector_update":
        sid   = sdata.get("sid")
        parts = text.split()
        name  = " ".join(p for p in parts if not _is_emoji_char(p)).strip() or text
        emoji = next((p for p in parts if _is_emoji_char(p)), None)
        try:
            if emoji:
                cur.execute("UPDATE asset_sectors SET name=?, emoji=? WHERE id=?", (name, emoji, sid))
            else:
                cur.execute("UPDATE asset_sectors SET name=? WHERE id=?", (name, sid))
            conn.commit()
            _done("✅ تم تعديل الجانب", "dev_sector", {"sid": sid})
        except Exception as e:
            _done(f"❌ خطأ: {e}", "dev_sector", {"sid": sid})
        return True

    # ── Asset add ─────────────────────────────────────────────
    if s == "dev_asset_add":
        sid    = sdata.get("sid")
        fields = _parse_fields(text)
        try:
            cur.execute("""
                INSERT INTO assets
                (name,name_ar,emoji,sector_id,base_price,base_value,cost_scale,
                 maintenance,income,max_level,
                 stat_economy,stat_health,stat_education,stat_military,stat_infrastructure,
                 pop_effect,eco_effect,prot_effect)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                fields.get("name","new_asset"), fields.get("name_ar","عنصر"),
                fields.get("emoji","🏗"), int(fields.get("sector_id", sid or 1)),
                float(fields.get("base_price",100)), float(fields.get("base_value",1)),
                float(fields.get("cost_scale",1.5)), float(fields.get("maintenance",0)),
                float(fields.get("income",0)), int(fields.get("max_level",10)),
                float(fields.get("stat_economy",0)), float(fields.get("stat_health",0)),
                float(fields.get("stat_education",0)), float(fields.get("stat_military",0)),
                float(fields.get("stat_infrastructure",0)),
                float(fields.get("pop_effect",0)), float(fields.get("eco_effect",0)),
                float(fields.get("prot_effect",0)),
            ))
            conn.commit()
            _done(f"✅ تم إضافة العنصر: {fields.get('name_ar','')}", "dev_assets_list", {"sid": sid})
        except Exception as e:
            _done(f"❌ خطأ: {e}", "dev_assets_list", {"sid": sid})
        return True

    # ── Asset update ──────────────────────────────────────────
    if s == "dev_asset_update":
        aid    = sdata.get("aid")
        sid    = sdata.get("sid")
        fields = {_ALIASES.get(k, k): v for k, v in _parse_fields(text).items()}
        if not fields:
            _done("❌ لم يتم إرسال أي حقول", "dev_asset", {"aid": aid, "sid": sid})
            return True
        try:
            sets   = ", ".join(f"{k}=?" for k in fields)
            values = list(fields.values()) + [aid]
            cur.execute(f"UPDATE assets SET {sets} WHERE id=?", values)
            conn.commit()
            _done(f"✅ تم تعديل {len(fields)} حقل", "dev_asset", {"aid": aid, "sid": sid})
        except Exception as e:
            _done(f"❌ خطأ: {e}", "dev_asset", {"aid": aid, "sid": sid})
        return True

    # ── Troop states — delegate to troop panel ────────────────
    if s.startswith("dev_troop_"):
        return handle_troop_dev_input(uid, cid, text, s, sdata)

    return False
