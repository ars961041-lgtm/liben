import json

from utils.pagination import btn, edit_ui, paginate_list, register_action, send_ui
from utils.helpers import is_group
from handlers.tops.tops_builder import build_top
from database.db_queries.tops_queries import (
    get_top_richest, get_group_members_stats,
    get_top_cities_by, get_top_countries_by
)

from handlers.tops.tops_menu import (
    CITY_METRICS, CITY_LABELS,
    COUNTRY_METRICS, COUNTRY_LABELS
)


# ── owner helper ─────────────────────────────
def _owner(call):
    return (call.from_user.id, call.message.chat.id)


# ── main menu buttons ─────────────────────────
def _main_nav(owner):
    return [
        btn("🏙 المدن",        "top_show_city_metrics",    owner=owner, color="d"),
        btn("🌍 الدول",        "top_show_country_metrics", owner=owner),
        btn("💰 الأغنى",       "show_top_richest",         owner=owner),
        btn("🔥 المتفاعلين",   "show_top_activity",        owner=owner, color="su"),
        btn("⚔️ توب الحروب",   "top_war_menu",             owner=owner, color="d"),
        btn("🏰 توب التحالفات","top_alliances",            data={"page": 0}, owner=owner),
    ]


# ── metric buttons ────────────────────────────
def _city_metric_btns(owner):
    btns = [
        btn(
            CITY_LABELS[m],
            "top_city_metric",
            json.dumps({"m": m, "p": 0}),
            owner=owner
        )
        for m in CITY_METRICS
    ]

    btns.append(btn("رجوع", "top_main_menu", owner=owner))
    return btns


def _country_metric_btns(owner):
    btns = [
        btn(
            COUNTRY_LABELS[m],
            "top_country_metric",
            json.dumps({"m": m, "p": 0}),
            owner=owner
        )
        for m in COUNTRY_METRICS
    ]

    btns.append(btn("رجوع", "top_main_menu", owner=owner))
    return btns


# ═══════════════════════════════════
# 🏙 ارسال توب المدن
# ═══════════════════════════════════
def _send_city_metrics(chat_id, uid, owner, metric=None, page=0, call=None):

    metric = metric or CITY_METRICS[0]

    rows = get_top_cities_by(metric, limit=50)

    paged, total_pages = paginate_list(rows, page, 10) if rows else ([], 1)

    caption = (
        build_top(
            f"🏙 توب المدن — {CITY_LABELS.get(metric, metric)}",
            [{"name": r["name"], "value": r["value"]} for r in paged]
        )
        if paged else "❌ لا توجد بيانات للمدن."
    )

    if total_pages > 1:
        caption += f"\n\n📄 صفحة {page+1} / {total_pages}"

    btns = _city_metric_btns(owner)

    nav = []

    if page > 0:
        nav.append(
            btn("⬅️", "top_city_metric",
                json.dumps({"m": metric, "p": page-1}),
                owner=owner)
        )

    if page < total_pages - 1:
        nav.append(
            btn("➡️", "top_city_metric",
                json.dumps({"m": metric, "p": page+1}),
                owner=owner)
        )

    layout = [3, 2] + ([len(nav)] if nav else []) + [1]

    if call:
        edit_ui(call, text=caption, buttons=btns + nav, layout=layout)
    else:
        send_ui(chat_id, text=caption, buttons=btns + nav, layout=layout, owner_id=uid)


# ═══════════════════════════════════
# 🌍 ارسال توب الدول
# ═══════════════════════════════════
def _send_country_metrics(chat_id, uid, owner, metric=None, page=0, call=None):

    metric = metric or COUNTRY_METRICS[0]

    rows = get_top_countries_by(metric, limit=50)

    paged, total_pages = paginate_list(rows, page, 10) if rows else ([], 1)

    caption = (
        build_top(
            f"🌍 توب الدول — {COUNTRY_LABELS.get(metric, metric)}",
            [{"name": r["name"], "value": r["value"]} for r in paged]
        )
        if paged else "❌ لا توجد بيانات للدول."
    )

    if total_pages > 1:
        caption += f"\n\n📄 صفحة {page+1} / {total_pages}"

    btns = _country_metric_btns(owner)

    nav = []

    if page > 0:
        nav.append(
            btn("⬅️", "top_country_metric",
                json.dumps({"m": metric, "p": page-1}),
                owner=owner)
        )

    if page < total_pages - 1:
        nav.append(
            btn("➡️", "top_country_metric",
                json.dumps({"m": metric, "p": page+1}),
                owner=owner)
        )

    layout = [3, 2] + ([len(nav)] if nav else []) + [1]

    if call:
        edit_ui(call, text=caption, buttons=btns + nav, layout=layout)
    else:
        send_ui(chat_id, text=caption, buttons=btns + nav, layout=layout, owner_id=uid)


# ═══════════════════════════════════
# 📊 أمر التوب
# ═══════════════════════════════════
def top_commands(message):
    """
    Returns True if the message was handled as a top command.
    """
    if not is_group(message):
        return False

    text = message.text.strip() if message.text else ""
    normalized_text = text.lower()

    # قائمة أوامر التوب المسموح بها
    allowed = ["توب الأغنى", "توب المتفاعلين", "توب المدن", "توب الدول",
               "توب الحروب", "توب التحالفات", "توب الدول بالمستوى", "توب"]

    if normalized_text not in allowed:
        return False  # لم يتم التعامل

    owner = (message.from_user.id, message.chat.id)

    # 💰 توب الأغنى
    if normalized_text == "توب":
        rows = get_top_richest(10)
        caption = build_top("💰 توب الأغنى", rows) if rows else "❌ لا توجد بيانات."

        send_ui(
            message.chat.id,
            text=caption,
            buttons=_main_nav(owner),
            layout=[2, 2],
            owner_id=message.from_user.id
        )
    
        
    elif normalized_text == "توب الأغنى":
        rows = get_top_richest(10)
        caption = build_top("💰 توب الأغنى", rows) if rows else "❌ لا توجد بيانات."
        send_ui(
            message.chat.id,
            text=caption,
            buttons=_main_nav(owner),
            layout=[2, 2],
            owner_id=message.from_user.id
        )

    # 🔥 توب المتفاعلين
    elif normalized_text == "توب المتفاعلين":
        members = get_group_members_stats(message.chat.id, 10)
        if members:
            rows = [{"name": m.get("name", "Unknown"), "value": f"{m.get('messages_count',0)} رسالة"} for m in members]
            caption = build_top("🔥 أعلى المتفاعلين", rows)
        else:
            caption = "❌ لا يوجد بيانات متاحة."
        send_ui(
            message.chat.id,
            text=caption,
            buttons=_main_nav(owner),
            layout=[2, 2],
            owner_id=message.from_user.id
        )

    # 🏙 توب المدن / 🌍 توب الدول
    elif normalized_text in ["توب المدن", "توب الدول"]:
        from handlers.tops.tops_builder import handle_top_text_command
        handle_top_text_command(message, normalized_text)

    elif normalized_text in ["توب الحروب", "توب التحالفات", "توب الدول بالمستوى"]:
        _handle_war_tops(message, normalized_text)

    return True
# ═══════════════════════════════════
# 🔘 Button handlers
# ═══════════════════════════════════

@register_action("top_show_city_metrics")
def handle_show_city_metrics(call, data):

    o = _owner(call)

    _send_city_metrics(
        call.message.chat.id,
        call.from_user.id,
        o,
        call=call
    )


@register_action("top_show_country_metrics")
def handle_show_country_metrics(call, data):

    o = _owner(call)

    _send_country_metrics(
        call.message.chat.id,
        call.from_user.id,
        o,
        call=call
    )


@register_action("top_city_metric")
def handle_top_city(call, data):

    if isinstance(data, str):
        data = json.loads(data)

    o = _owner(call)

    metric = data.get("m", CITY_METRICS[0])
    page = int(data.get("p", 0))

    _send_city_metrics(
        call.message.chat.id,
        call.from_user.id,
        o,
        metric=metric,
        page=page,
        call=call
    )


@register_action("top_country_metric")
def handle_top_country(call, data):

    if isinstance(data, str):
        data = json.loads(data)

    o = _owner(call)

    metric = data.get("m", COUNTRY_METRICS[0])
    page = int(data.get("p", 0))

    _send_country_metrics(
        call.message.chat.id,
        call.from_user.id,
        o,
        metric=metric,
        page=page,
        call=call
    )


@register_action("show_top_richest")
def handle_top_richest_btn(call, data):

    o = _owner(call)

    rows = get_top_richest(10)

    caption = build_top("💰 توب الأغنى", rows) if rows else "❌ لا توجد بيانات."

    edit_ui(call, text=caption, buttons=_main_nav(o), layout=[2, 2])


@register_action("show_top_activity")
def handle_top_activity_btn(call, data):

    o = _owner(call)

    members = get_group_members_stats(call.message.chat.id, 10)

    if members:

        rows = [
            {
                "name": m.get("name", "Unknown"),
                "value": f"{m.get('messages_count', 0)} رسالة"
            }
            for m in members
        ]

        caption = build_top("🔥 أعلى المتفاعلين", rows)

    else:
        caption = "❌ لا يوجد بيانات متاحة."

    edit_ui(call, text=caption, buttons=_main_nav(o), layout=[2, 2])


@register_action("top_main_menu")
def handle_top_main_menu(call, data):

    o = _owner(call)

    rows = get_top_richest(10)

    caption = build_top("💰 توب الأغنى", rows) if rows else "❌ لا توجد بيانات."

    edit_ui(call, text=caption, buttons=_main_nav(o), layout=[2, 2])


# ══════════════════════════════════════════
# ⚔️ توب الحروب والتحالفات والمستويات
# ══════════════════════════════════════════

def _handle_war_tops(message, normalized_text):
    owner = (message.from_user.id, message.chat.id)
    chat_id = message.chat.id
    uid = message.from_user.id

    if normalized_text == "توب الحروب":
        _send_top_war_countries(chat_id, uid, owner)
    elif normalized_text == "توب التحالفات":
        _send_top_alliances(chat_id, uid, owner, page=0)
    elif normalized_text == "توب الدول بالمستوى":
        _send_top_countries_level(chat_id, uid, owner, page=0)


def _send_top_war_countries(chat_id, uid, owner, call=None):
    """توب الدول بالمستوى والقوة"""
    try:
        from modules.war.country_level import get_top_countries_by_level
        rows = get_top_countries_by_level(limit=20)
        data = [{"name": f"{r['label']} — {r['name']}", "value": f"نقاط: {r['score']:.0f}"} for r in rows]
        caption = build_top("⚔️ توب الدول بالمستوى", data) if data else "❌ لا توجد بيانات."
    except Exception as e:
        caption = f"❌ خطأ: {e}"

    btns = [btn("🔙 رجوع", "top_main_menu", owner=owner)]
    if call:
        edit_ui(call, text=caption, buttons=btns, layout=[1])
    else:
        send_ui(chat_id, text=caption, buttons=btns, layout=[1], owner_id=uid)


def _send_top_alliances(chat_id, uid, owner, page=0, call=None):
    """توب التحالفات"""
    try:
        from database.db_queries.alliances_queries import get_top_alliances
        rows = get_top_alliances(limit=20)
        items, total_pages = paginate_list(rows, page, per_page=10)
        data = [{"name": r["name"],
                 "value": f"💪 {r['power']:.0f} | 👥 {r['member_count']}"}
                for r in items]
        caption = build_top("🏰 توب التحالفات", data) if data else "❌ لا توجد تحالفات."
        if total_pages > 1:
            caption += f"\n\n📄 صفحة {page+1}/{total_pages}"
    except Exception as e:
        caption = f"❌ خطأ: {e}"
        items, total_pages = [], 1

    nav = []
    if page > 0:
        nav.append(btn("◀️", "top_alliances", data={"page": page-1}, owner=owner))
    if page < total_pages - 1:
        nav.append(btn("▶️", "top_alliances", data={"page": page+1}, owner=owner))
    nav.append(btn("🔙 رجوع", "top_main_menu", owner=owner))

    if call:
        edit_ui(call, text=caption, buttons=nav, layout=[len(nav)])
    else:
        send_ui(chat_id, text=caption, buttons=nav, layout=[len(nav)], owner_id=uid)


def _send_top_countries_level(chat_id, uid, owner, page=0, call=None):
    """توب الدول بالمستوى مع pagination"""
    try:
        from modules.war.country_level import get_top_countries_by_level
        all_rows = get_top_countries_by_level(limit=50)
        items, total_pages = paginate_list(all_rows, page, per_page=10)
        data = [{"name": r["name"], "value": f"{r['label']} | نقاط: {r['score']:.0f}"}
                for r in items]
        caption = build_top("🌍 توب الدول بالمستوى", data) if data else "❌ لا توجد بيانات."
        if total_pages > 1:
            caption += f"\n\n📄 صفحة {page+1}/{total_pages}"
    except Exception as e:
        caption = f"❌ خطأ: {e}"
        total_pages = 1

    nav = []
    if page > 0:
        nav.append(btn("◀️", "top_countries_level", data={"page": page-1}, owner=owner))
    if page < total_pages - 1:
        nav.append(btn("▶️", "top_countries_level", data={"page": page+1}, owner=owner))
    nav.append(btn("🔙 رجوع", "top_main_menu", owner=owner))

    if call:
        edit_ui(call, text=caption, buttons=nav, layout=[len(nav)])
    else:
        send_ui(chat_id, text=caption, buttons=nav, layout=[len(nav)], owner_id=uid)


def _send_top_reputation(chat_id, uid, owner, page=0, call=None):
    """توب اللاعبين بالسمعة"""
    try:
        from database.connection import get_db_conn
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pr.user_id, pr.reputation_title, pr.loyalty_score,
                   pr.battles_helped, u.user_id as uid
            FROM player_reputation pr
            LEFT JOIN users u ON pr.user_id = u.user_id
            ORDER BY pr.loyalty_score DESC LIMIT 50
        """)
        all_rows = [dict(r) for r in cursor.fetchall()]
        items, total_pages = paginate_list(all_rows, page, per_page=10)
        data = [{"name": f"ID:{r['user_id']} {r['reputation_title']}",
                 "value": f"ولاء: {r['loyalty_score']} | مساعدات: {r['battles_helped']}"}
                for r in items]
        caption = build_top("🏆 توب اللاعبين بالسمعة", data) if data else "❌ لا توجد بيانات."
    except Exception as e:
        caption = f"❌ خطأ: {e}"
        total_pages = 1

    nav = [btn("🔙 رجوع", "top_main_menu", owner=owner)]
    if call:
        edit_ui(call, text=caption, buttons=nav, layout=[1])
    else:
        send_ui(chat_id, text=caption, buttons=nav, layout=[1], owner_id=uid)


# ── New button handlers ──────────────────────────────────────

@register_action("top_war_menu")
def handle_top_war_menu(call, data):
    o = _owner(call)
    chat_id = call.message.chat.id
    uid = call.from_user.id
    buttons = [
        btn("🌍 توب الدول بالمستوى", "top_countries_level", data={"page": 0}, owner=o),
        btn("🏰 توب التحالفات",       "top_alliances",       data={"page": 0}, owner=o),
        btn("🏆 توب السمعة",          "top_reputation",      data={"page": 0}, owner=o, color="su"),
        btn("🔙 رجوع",                "top_main_menu",        owner=o),
    ]
    edit_ui(call, text="⚔️ <b>توب الحروب والتحالفات</b>\n\nاختر ما تريد:",
            buttons=buttons, layout=[1, 1, 1, 1])


@register_action("top_alliances")
def handle_top_alliances(call, data):
    o = _owner(call)
    page = int(data.get("page", 0)) if isinstance(data, dict) else 0
    _send_top_alliances(call.message.chat.id, call.from_user.id, o, page=page, call=call)


@register_action("top_countries_level")
def handle_top_countries_level(call, data):
    o = _owner(call)
    page = int(data.get("page", 0)) if isinstance(data, dict) else 0
    _send_top_countries_level(call.message.chat.id, call.from_user.id, o, page=page, call=call)


@register_action("top_reputation")
def handle_top_reputation(call, data):
    o = _owner(call)
    page = int(data.get("page", 0)) if isinstance(data, dict) else 0
    _send_top_reputation(call.message.chat.id, call.from_user.id, o, page=page, call=call)
