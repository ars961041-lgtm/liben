"""
معالج التوب — 6 فئات رئيسية قابلة للتوسع.

لإضافة فئة جديدة:
1. أضف دالة استعلام في tops_queries.py
2. أضف مدخلاً في TOP_CATEGORIES
3. أضف زراً في _main_buttons()
"""
from utils.pagination import btn, edit_ui, paginate_list, register_action, send_ui
from utils.helpers import is_group, get_lines
from handlers.tops.tops_builder import build_top
from database.db_queries.tops_queries import (
    get_top_active_users, get_top_active_in_group,
    get_top_spending_cities, get_top_spending_countries,
    get_top_alliances, get_top_groups, get_top_betrayals,
    get_top_richest, get_top_wars, get_top_war_winners, get_top_war_loot,
)

from modules.bank.utils.constants import CURRENCY_ENGLISH_NAME

# ══════════════════════════════════════════
# 📋 سجل الفئات — أضف هنا لتوسيع النظام
# ══════════════════════════════════════════

def _fetch_active(chat_id, **_):
    return get_top_active_in_group(chat_id) or get_top_active_users()

TOP_CATEGORIES = {
    "active":      {"label": "🔥 المتفاعلون",   "fetch": lambda chat_id, **_: get_top_active_in_group(chat_id)},
    "cities":      {"label": "🏙 المدن",         "fetch": lambda **_: get_top_spending_cities()},
    "countries":   {"label": "🌍 الدول",         "fetch": lambda **_: get_top_spending_countries()},
    "alliances":   {"label": "🏰 التحالفات",     "fetch": lambda **_: get_top_alliances()},
    "groups":      {"label": "👥 المجموعات",     "fetch": lambda **_: get_top_groups()},
    "betrayals":   {"label": "🗡 الخيانات",      "fetch": lambda **_: get_top_betrayals()},
    "richest":     {"label": "💰 الأغنى",        "fetch": lambda **_: get_top_richest()},
    "wars":        {"label": "⚔️ الحروب",        "fetch": lambda **_: get_top_wars()},
    "war_winners": {"label": "🏆 الانتصارات",    "fetch": lambda **_: get_top_war_winners()},
    "war_loot":    {"label": "💎 الغنائم",       "fetch": lambda **_: get_top_war_loot()},
}

# عناوين العرض
TOP_TITLES = {
    "active":      "🔥 توب المتفاعلين",
    "cities":      "🏙 توب المدن بالإنفاق",
    "countries":   "🌍 توب الدول بالإنفاق",
    "alliances":   "🏰 توب التحالفات",
    "groups":      "👥 توب المجموعات",
    "betrayals":   "🗡 توب الخيانات",
    "richest":     "💰 توب الأغنى",
    "wars":        "⚔️ توب الدول بعدد الحروب",
    "war_winners": "🏆 توب الدول بالانتصارات",
    "war_loot":    "💎 توب الدول بالغنائم",
}

# وحدات القيم
TOP_UNITS = {
    "active":      "رسالة",
    "cities":      f"{CURRENCY_ENGLISH_NAME}",
    "countries":   f"{CURRENCY_ENGLISH_NAME}",
    "alliances":   "نقطة",
    "groups":      "رسالة",
    "betrayals":   "مرة",
    "richest":     f"{CURRENCY_ENGLISH_NAME}",
    "wars":        "معركة",
    "war_winners": "انتصار",
    "war_loot":    f"{CURRENCY_ENGLISH_NAME}",
}


# ══════════════════════════════════════════
# 🔘 أزرار القائمة الرئيسية
# ══════════════════════════════════════════

def _main_buttons(owner):
    return [
        btn(TOP_CATEGORIES[k]["label"], "top_show",
            data={"cat": k, "p": 0}, owner=owner)
        for k in TOP_CATEGORIES
    ]


# ══════════════════════════════════════════
# 📊 عرض فئة
# ══════════════════════════════════════════

def _send_top(cat: str, chat_id: int, uid: int, owner: tuple,
              page: int = 0, call=None):
    """عرض أي فئة توب بشكل موحد."""
    category = TOP_CATEGORIES.get(cat)
    if not category:
        return

    try:
        rows = category["fetch"](chat_id=chat_id)
    except Exception as e:
        rows = []

    items, total_pages = paginate_list(rows, page, per_page=10) if rows else ([], 1)

    unit  = TOP_UNITS.get(cat, "")
    title = TOP_TITLES.get(cat, cat)

    # أضف الوحدة كملاحظة بدلاً من دمجها في القيمة حتى تبقى المحاذاة صحيحة
    caption = build_top(title, items, note=unit) if items else f"❌ لا توجد بيانات لـ {title}."
    if total_pages > 1:
        caption += f"\n\n📄 صفحة {page+1}/{total_pages}"

    nav = []
    if page > 0:
        nav.append(btn("◀️", "top_show", data={"cat": cat, "p": page-1}, owner=owner))
    if page < total_pages - 1:
        nav.append(btn("▶️", "top_show", data={"cat": cat, "p": page+1}, owner=owner))
    nav.append(btn("🔙 رجوع", "top_main_menu", owner=owner))

    layout = ([len(nav)] if nav else [1])

    if call:
        edit_ui(call, text=caption, buttons=nav, layout=layout)
    else:
        send_ui(chat_id, text=caption, buttons=nav, layout=layout, owner_id=uid)


# ══════════════════════════════════════════
# 📥 أمر توب النصي
# ══════════════════════════════════════════

def top_commands(message) -> bool:
    if not is_group(message):
        return False

    text = (message.text or "").strip().lower()

    # خريطة الأوامر النصية → فئة
    TEXT_MAP = {
        "توب":                "richest",
        "توب الأغنى":         "richest",
        "توب المتفاعلين":     "active",
        "توب المدن":          "cities",
        "توب الدول":          "countries",
        "توب التحالفات":      "alliances",
        "توب المجموعات":      "groups",
        "توب الخيانات":       "betrayals",
        "توب الحروب":         "wars",
        "توب الانتصارات":     "war_winners",
        "توب الغنائم":        "war_loot",
        # backward compat
        "توب الدول بالمستوى": "countries",
    }

    cat = TEXT_MAP.get(text)
    if not cat:
        return False

    uid   = message.from_user.id
    cid   = message.chat.id
    owner = (uid, cid)

    if text == "توب":
        # القائمة الرئيسية
        rows    = get_top_richest(10)
        unit    = TOP_UNITS.get("richest", "")
        caption = build_top("💰 توب الأغنى", rows, note=unit) if rows else "❌ لا توجد بيانات."
        send_ui(cid, text=caption, buttons=_main_buttons(owner),
                layout=[3, 2, 2, 3], owner_id=uid, reply_to=message.message_id)
    else:
        _send_top(cat, cid, uid, owner)

    return True


# ══════════════════════════════════════════
# 🔘 معالجات الأزرار
# ══════════════════════════════════════════

@register_action("top_show")
def handle_top_show(call, data):
    o    = (call.from_user.id, call.message.chat.id)
    cat  = data.get("cat", "richest")
    page = int(data.get("p", 0))
    _send_top(cat, call.message.chat.id, call.from_user.id, o, page=page, call=call)


@register_action("top_main_menu")
def handle_top_main_menu(call, data):
    o       = (call.from_user.id, call.message.chat.id)
    rows    = get_top_richest(10)
    unit    = TOP_UNITS.get("richest", "")
    caption = build_top("💰 توب الأغنى", rows, note=unit) if rows else "❌ لا توجد بيانات."
    edit_ui(call, text=caption, buttons=_main_buttons(o), layout=[3, 2, 2, 3])


# ── backward-compat aliases (old button actions still work) ──

@register_action("show_top_richest")
def _compat_richest(call, data):
    handle_top_show(call, {"cat": "richest", "p": 0})

@register_action("show_top_activity")
def _compat_activity(call, data):
    handle_top_show(call, {"cat": "active", "p": 0})

@register_action("top_alliances")
def _compat_alliances(call, data):
    handle_top_show(call, {"cat": "alliances", "p": data.get("page", 0)})

@register_action("top_war_menu")
def _compat_war_menu(call, data):
    handle_top_show(call, {"cat": "countries", "p": 0})

@register_action("top_countries_level")
def _compat_countries_level(call, data):
    handle_top_show(call, {"cat": "countries", "p": data.get("page", 0)})

@register_action("top_reputation")
def _compat_reputation(call, data):
    handle_top_show(call, {"cat": "active", "p": data.get("page", 0)})

@register_action("top_show_city_metrics")
def _compat_city_metrics(call, data):
    handle_top_show(call, {"cat": "cities", "p": 0})

@register_action("top_show_country_metrics")
def _compat_country_metrics(call, data):
    handle_top_show(call, {"cat": "countries", "p": 0})
