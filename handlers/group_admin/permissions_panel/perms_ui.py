"""
UI builder — admin permissions only, single paginated list, 2 per row.
"""
from core.bot import bot
from utils.pagination.buttons import btn, build_keyboard
from utils.pagination.router import paginate_list
from .perms_config import ADMIN_PERMS, PRESETS
from .perms_state import get_extra

PER_PAGE = 14   # 4 rows of 2


def _header(extra: dict, page: int, total_pages: int) -> str:
    name   = extra.get("target_name", "")
    uid    = extra.get("target_uid", "")
    title  = extra.get("title", "")
    is_adm = extra.get("target_is_admin", False)
    role   = "🛡 مشرف" if is_adm else "👤 عضو"

    lines = [
        f"🔧 <b>صلاحيات الإشراف:</b> <a href='tg://user?id={uid}'>{name}</a>  {role}",
    ]
    if total_pages > 1:
        lines.append(f"📄 الصفحة {page + 1}/{total_pages}")
    if title:
        lines.append(f"🏷 <b>اللقب:</b> {title}")
    lines.append("")
    return "\n".join(lines)


def _perm_buttons(uid: int, cid: int, extra: dict, page: int) -> tuple[list, list, int]:
    promote = extra.get("promote", {})
    items, total_pages = paginate_list(ADMIN_PERMS, page=page, per_page=PER_PAGE)

    buttons = []
    layout  = []

    for i in range(0, len(items), 2):
        row = items[i:i+2]
        for key, label in row:
            on = promote.get(key, False)
            buttons.append(btn(
                f"{'✅' if on else '❌'} {label}",
                "pp_toggle", {"k": key, "pg": page},
                color="su" if on else "d",
                owner=(uid, cid),
            ))
        layout.append(len(row))

    return buttons, layout, total_pages


def _control_buttons(uid: int, cid: int, extra: dict, page: int, total_pages: int) -> tuple[list, list]:
    buttons = []
    layout  = []

    # Navigation
    nav = []
    if page > 0:
        nav.append(btn("▶️ السابق", "pp_page", {"pg": page - 1}, owner=(uid, cid)))
    if page < total_pages - 1:
        nav.append(btn("التالي ◀️", "pp_page", {"pg": page + 1}, owner=(uid, cid)))
    if nav:
        buttons += nav
        layout.append(len(nav))

    # Single preset button
    for p_key, p_val in PRESETS.items():
        buttons.append(btn(p_val["label"], "pp_preset", {"p": p_key}, color="de", owner=(uid, cid)))
    layout.append(len(PRESETS))

    # Actions
    actions = [
        btn("✏️ لقب",   "pp_title",  {}, color="p",  owner=(uid, cid)),
        btn("✅ تطبيق", "pp_apply",  {}, color="su", owner=(uid, cid)),
        btn("❌ إلغاء", "pp_cancel", {}, color="d",  owner=(uid, cid)),
    ]
    buttons += actions
    layout.append(len(actions))

    return buttons, layout


def build_ui(uid: int, cid: int) -> tuple[str, object] | None:
    extra = get_extra(uid, cid)
    if not extra:
        return None

    page = extra.get("page", 0)
    perm_btns, perm_layout, total_pages = _perm_buttons(uid, cid, extra, page)
    ctrl_btns, ctrl_layout              = _control_buttons(uid, cid, extra, page, total_pages)

    text   = _header(extra, page, total_pages)
    markup = build_keyboard(perm_btns + ctrl_btns, perm_layout + ctrl_layout, uid)
    return text, markup


def send_ui(chat_id: int, uid: int, cid: int, reply_to: int = None):
    result = build_ui(uid, cid)
    if not result:
        return None
    text, markup = result
    kwargs = {"parse_mode": "HTML", "disable_web_page_preview": True, "reply_markup": markup}
    if reply_to:
        kwargs["reply_to_message_id"] = reply_to
    try:
        return bot.send_message(chat_id, text, **kwargs)
    except Exception:
        kwargs.pop("reply_to_message_id", None)
        return bot.send_message(chat_id, text, **kwargs)


def edit_ui(call, uid: int, cid: int):
    result = build_ui(uid, cid)
    if not result:
        return
    text, markup = result
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
        if "message is not modified" not in str(e).lower():
            raise
