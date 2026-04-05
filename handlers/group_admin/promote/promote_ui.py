"""
Builds and renders the promote inline keyboard UI.
Uses the existing pagination/buttons system.
"""
import time
from core.bot import bot
from utils.pagination.buttons import btn, build_keyboard
from utils.pagination.router import paginate_list
from .promote_state import PERMISSIONS, get_promote_extra

PER_PAGE = 4   # permissions per page


def _perm_buttons(uid: int, cid: int, perms: dict, page: int) -> tuple[list, list, int]:
    """Returns (buttons, layout, total_pages)."""
    items, total_pages = paginate_list(PERMISSIONS, page=page, per_page=PER_PAGE)

    buttons = []
    for perm_key, label in items:
        enabled = perms.get(perm_key, False)
        icon = "✅" if enabled else "❌"
        buttons.append(btn(
            f"{icon} {label}",
            "prm_toggle",
            {"perm": perm_key, "page": page},
            color="su" if enabled else "d",
            owner=(uid, cid),
        ))

    # Navigation row
    nav = []
    if page < total_pages - 1:
        nav.append(btn("التالي ◀️", "prm_page", {"page": page + 1}, owner=(uid, cid)))
    if page > 0:
        nav.append(btn("▶️ السابق", "prm_page", {"page": page - 1}, owner=(uid, cid)))

    # Action row
    actions = [
        btn("✏️ تعيين اللقب", "prm_set_title", {"page": page}, owner=(uid, cid)),
        btn("✅ تعيين",        "prm_assign",    {"page": page}, color="su", owner=(uid, cid)),
        btn("❌ إلغاء",        "prm_cancel",    {},             color="d",  owner=(uid, cid)),
    ]

    all_buttons = buttons + (nav if nav else []) + actions
    # layout: one button per row for perms, nav in one row, actions in one row
    layout = [1] * len(items)
    if nav:
        layout.append(len(nav))
    layout.append(len(actions))

    return all_buttons, layout, total_pages


def build_promote_text(extra: dict, page: int, total_pages: int) -> str:
    target_name = extra.get("target_name", "")
    target_uid  = extra.get("target_uid", "")
    title       = extra.get("title", "")
    mode        = extra.get("mode", "promote")
    mode_label  = "تعديل صلاحيات" if mode == "edit" else "ترقية"

    lines = [
        f"👤 <b>{mode_label}:</b> <a href='tg://user?id={target_uid}'>{target_name}</a>",
        f"📄 الصفحة {page + 1}/{total_pages}",
    ]
    if title:
        lines.append(f"🏷 اللقب: <b>{title}</b>")
    lines.append("\nاختر الصلاحيات:")
    return "\n".join(lines)


def send_promote_ui(chat_id: int, uid: int, cid: int, page: int = 0, reply_to: int = None):
    """Send a fresh promote UI message."""
    extra = get_promote_extra(uid, cid)
    if not extra:
        return None

    perms = extra.get("perms", {})
    buttons, layout, total_pages = _perm_buttons(uid, cid, perms, page)
    text    = build_promote_text(extra, page, total_pages)
    markup  = build_keyboard(buttons, layout, uid)

    kwargs = {"parse_mode": "HTML", "disable_web_page_preview": True, "reply_markup": markup}
    if reply_to:
        kwargs["reply_to_message_id"] = reply_to

    msg = bot.send_message(chat_id, text, **kwargs)
    return msg


def edit_promote_ui(call, uid: int, cid: int, page: int = 0):
    """Edit existing promote UI message in-place."""
    extra = get_promote_extra(uid, cid)
    if not extra:
        return

    perms = extra.get("perms", {})
    buttons, layout, total_pages = _perm_buttons(uid, cid, perms, page)
    text   = build_promote_text(extra, page, total_pages)
    markup = build_keyboard(buttons, layout, uid)

    try:
        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=markup,
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise
