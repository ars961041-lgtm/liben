"""
قائمة الإجراءات التأديبية الموحدة — كتم / حظر / تقييد / كتم عالمي
واجهة مشتركة وقابلة لإعادة الاستخدام لجميع أنواع القوائم.
"""
from core.bot import bot
from core.admin import is_any_dev
from database.connection import get_db_conn
from database.db_queries.groups_queries import get_internal_group_id
from utils.pagination import btn, send_ui, edit_ui, register_action
from utils.helpers import get_lines

_PER_PAGE = 10

# ── أنواع القوائم المدعومة ──
LIST_TYPES = {
    "muted":        {"label": "🔇 المكتومون",       "field": "is_muted"},
    "banned":       {"label": "🚫 المحظورون",        "field": "is_banned"},
    "restricted":   {"label": "⚠️ المقيدون",         "field": "is_restricted"},
    "global_muted": {"label": "🔇 الكتم العالمي",    "field": None},  # جدول منفصل
}


# ══════════════════════════════════════════
# استعلامات البيانات
# ══════════════════════════════════════════

def _fetch_group_list(tg_group_id: int, field: str, page: int) -> tuple[list, int]:
    """يجلب قائمة مرقّمة من group_members مع أسماء المستخدمين."""
    internal_id = get_internal_group_id(tg_group_id)
    if not internal_id:
        return [], 0
    conn   = get_db_conn()
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT COUNT(*) FROM group_members WHERE group_id = ? AND {field} = 1",
        (internal_id,)
    )
    total = cursor.fetchone()[0]

    cursor.execute(
        f"""
        SELECT gm.user_id, COALESCE(u.name, '') AS name
        FROM group_members gm
        LEFT JOIN users u ON u.user_id = gm.user_id
        WHERE gm.group_id = ? AND gm.{field} = 1
        ORDER BY gm.user_id
        LIMIT ? OFFSET ?
        """,
        (internal_id, _PER_PAGE, page * _PER_PAGE)
    )
    rows = [{"user_id": r[0], "name": r[1]} for r in cursor.fetchall()]
    return rows, total


def _fetch_global_muted_list(page: int) -> tuple[list, int]:
    """يجلب قائمة الكتم العالمي مع أسماء المستخدمين."""
    conn   = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM global_mutes")
    total = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT gm.user_id, COALESCE(u.name, '') AS name
        FROM global_mutes gm
        LEFT JOIN users u ON u.user_id = gm.user_id
        ORDER BY gm.muted_at DESC
        LIMIT ? OFFSET ?
        """,
        (_PER_PAGE, page * _PER_PAGE)
    )
    rows = [{"user_id": r[0], "name": r[1]} for r in cursor.fetchall()]
    return rows, total


# ══════════════════════════════════════════
# بناء النص
# ══════════════════════════════════════════

def _display_name(entry: dict) -> str:
    name = (entry.get("name") or "").strip()
    return name if name else "Unknown"


def _build_list_text(list_type: str, entries: list, page: int, total: int) -> str:
    info        = LIST_TYPES[list_type]
    total_pages = max(1, (total + _PER_PAGE - 1) // _PER_PAGE)
    offset      = page * _PER_PAGE

    lines_out = [
        f"\u200f{info['label']}",
        f"\u200f{get_lines()}",
        f"\u200fالصفحة {page + 1}/{total_pages} — الإجمالي: {total}",
        "",
    ]
    for i, entry in enumerate(entries, start=offset + 1):
        name = _display_name(entry)
        uid  = entry["user_id"]
        # LTR: رقم | ID | Name
        lines_out.append(f"\u200e{i}. ID: <code>{uid}</code> | Name: {name}")

    return "\n".join(lines_out)


# ══════════════════════════════════════════
# نقطة الدخول الرئيسية
# ══════════════════════════════════════════

def show_moderation_list(message, list_type: str):
    """
    نقطة الدخول النصية — تُستدعى من group_commands.
    list_type: 'muted' | 'banned' | 'restricted' | 'global_muted'
    """
    user_id = message.from_user.id
    chat_id = message.chat.id

    if list_type == "global_muted":
        if not is_any_dev(user_id):
            bot.reply_to(message, "❌ هذا الأمر للمطورين فقط.")
            return
    else:
        from handlers.group_admin.permissions import is_admin
        if not is_admin(message):
            bot.reply_to(message, "❌ هذا الأمر للمشرفين فقط.")
            return

    _send_list(chat_id, user_id, list_type, page=0,
               tg_group_id=chat_id, reply_to=message.message_id)


def _send_list(chat_id: int, owner_id: int, list_type: str,
               page: int, tg_group_id: int, reply_to=None):
    """يبني ويرسل قائمة جديدة."""
    entries, total = _get_entries(list_type, tg_group_id, page)
    info           = LIST_TYPES[list_type]

    if total == 0:
        bot.send_message(
            chat_id,
            f"✅ {info['label']}: لا يوجد أحد في هذه القائمة.",
            reply_to_message_id=reply_to,
        )
        return

    text        = _build_list_text(list_type, entries, page, total)
    total_pages = max(1, (total + _PER_PAGE - 1) // _PER_PAGE)
    owner       = (owner_id, chat_id)

    buttons = _nav_buttons(list_type, page, total_pages, tg_group_id, owner)
    layout  = [len(buttons)] if buttons else [1]

    send_ui(chat_id, text=text, buttons=buttons, layout=layout,
            owner_id=owner_id, reply_to=reply_to)


def _edit_list(call, list_type: str, page: int, tg_group_id: int):
    """يحدّث رسالة موجودة بصفحة جديدة."""
    user_id     = call.from_user.id
    chat_id     = call.message.chat.id
    entries, total = _get_entries(list_type, tg_group_id, page)
    total_pages = max(1, (total + _PER_PAGE - 1) // _PER_PAGE)
    owner       = (user_id, chat_id)

    text    = _build_list_text(list_type, entries, page, total)
    buttons = _nav_buttons(list_type, page, total_pages, tg_group_id, owner)
    layout  = [len(buttons)] if buttons else [1]

    edit_ui(call, text=text, buttons=buttons, layout=layout)


def _get_entries(list_type: str, tg_group_id: int, page: int) -> tuple[list, int]:
    if list_type == "global_muted":
        return _fetch_global_muted_list(page)
    field = LIST_TYPES[list_type]["field"]
    return _fetch_group_list(tg_group_id, field, page)


def _nav_buttons(list_type: str, page: int, total_pages: int,
                 tg_group_id: int, owner: tuple) -> list:
    buttons = []
    if page > 0:
        buttons.append(btn("➡️ السابق", "modlist_page",
                           data={"t": list_type, "p": page - 1, "g": tg_group_id},
                           owner=owner))
    if page < total_pages - 1:
        buttons.append(btn("⬅️ التالي", "modlist_page",
                           data={"t": list_type, "p": page + 1, "g": tg_group_id},
                           owner=owner))
    buttons.append(btn("❌ إغلاق", "modlist_close", data={}, owner=owner, color="d"))
    return buttons


# ══════════════════════════════════════════
# Callbacks
# ══════════════════════════════════════════

@register_action("modlist_page")
def on_modlist_page(call, data):
    user_id      = call.from_user.id
    list_type    = data.get("t", "muted")
    page         = int(data.get("p", 0))
    tg_group_id  = int(data.get("g", call.message.chat.id))

    # فحص الصلاحية
    if list_type == "global_muted" and not is_any_dev(user_id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return

    bot.answer_callback_query(call.id)
    _edit_list(call, list_type, page, tg_group_id)


@register_action("modlist_close")
def on_modlist_close(call, data):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
