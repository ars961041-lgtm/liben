"""
لوحة إدارة المطور — ثوابت البوت، أدوار المطورين، الكتم العالمي
"""
from core.bot import bot
from core.admin import (
    is_primary_dev, is_secondary_dev, is_any_dev,
    get_all_constants, set_const,
    get_all_developers, add_developer, remove_developer,
    promote_developer, demote_developer,
    global_mute, global_unmute, group_mute, group_unmute,
    get_global_mutes, get_group_mutes,
)
from utils.pagination import (
    btn, send_ui, edit_ui, register_action, paginate_list, set_state, get_state, clear_state
)
from utils.helpers import get_lines

_RED  = "d"
_GRN  = "su"
_BLUE = "p"


def _back(action, data, owner):
    return btn("🔙 رجوع", action, data, color=_RED, owner=owner)


# ══════════════════════════════════════════
# 🏠 القائمة الرئيسية
# ══════════════════════════════════════════

def open_admin_panel(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not is_any_dev(user_id):
        bot.reply_to(message, "❌ هذا الأمر للمطورين فقط.")
        return

    _send_main_panel(message)


def _send_main_panel(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    owner = (user_id, chat_id)
    
    buttons = [
        btn("⚙️ ثوابت البوت",        "adm_constants",   data={"page": 0}, owner=owner, color=_BLUE),
        btn("👨‍💻 المطورون",           "adm_devs",        data={},          owner=owner, color=_BLUE),
        btn("🔇 الكتم العالمي",       "adm_global_mutes",data={"page": 0}, owner=owner, color=_RED),
        btn("🔕 كتم المجموعة",        "adm_group_mutes", data={"page": 0}, owner=owner, color=_RED),
        btn("📿 إدارة الأذكار",       "adm_azkar_panel",         data={}, owner=owner, color=_BLUE),
        btn("📰 المجلة والهدايا",     "adm_magazine_panel",      data={}, owner=owner, color=_BLUE),
        btn("📚 إدارة المحتوى",       "adm_content_hub",         data={}, owner=owner, color=_BLUE),
        btn("📖 إدارة القرآن",        "adm_quran_panel",         data={}, owner=owner, color=_BLUE),
        btn("🎮 إعادة تعيين الألعاب", "adm_reset_games_confirm", data={}, owner=owner, color=_RED),
        btn("🔄 إعادة تحميل الآيات", "adm_reload_ayat_confirm", data={}, owner=owner, color=_RED),
        btn("🗑 مسح قاعدة البيانات", "adm_reset_db_confirm",    data={}, owner=owner, color=_RED),
    ]
    send_ui(chat_id,
            text=f"🛠 <b>لوحة إدارة البوت</b>\n{get_lines()}\nاختر ما تريد إدارته:",
            buttons=buttons, layout=[2, 2, 2, 2, 2, 1], owner_id=user_id, reply_to=message.message_id)


# ══════════════════════════════════════════
# 🛠 لوحة المطور (ثوابت البوت)
# ══════════════════════════════════════════

@register_action("adm_constants")
def show_constants(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if not is_any_dev(user_id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return

    page = int(data.get("page", 0))
    all_consts = get_all_constants()
    items, total_pages = paginate_list(all_consts, page, per_page=8)
    owner = (user_id, chat_id)

    # أرقام عربية للعرض
    _nums = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣"]

    text = f"🛠 لوحة المطور (صفحة {page+1}/{total_pages})\n‏• ━━━━━━━━━━━━ •\n\n"
    buttons = []
    for i, c in enumerate(items):
        num = _nums[i]
        text += f"{num} {c['name']} = <code>{c['value']}</code>\n{c['description']}\n\n"
        if is_primary_dev(user_id):
            buttons.append(btn(f"{i+1}", "adm_edit_const",
                               data={"name": c["name"], "page": page},
                               owner=owner, color=_BLUE))

    nav = []
    if page < total_pages - 1:
        nav.append(btn("التالي", "adm_constants", data={"page": page+1}, owner=owner))
    nav.append(_back("adm_main_back", {}, owner))
    if page > 0:
        nav.append(btn("السابق", "adm_constants", data={"page": page-1}, owner=owner))

    # أزرار الثوابت: 4 في كل صف
    btn_rows = [4] * (len(buttons) // 4)
    if len(buttons) % 4:
        btn_rows.append(len(buttons) % 4)
    layout = btn_rows + ([len(nav)] if nav else [1])

    edit_ui(call, text=text, buttons=buttons + nav, layout=layout)


@register_action("adm_edit_const")
def edit_constant(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if not is_primary_dev(user_id):
        bot.answer_callback_query(call.id, "❌ فقط المطور الأساسي يمكنه التعديل.", show_alert=True)
        return

    name = data["name"]
    page = data.get("page", 0)
    owner = (user_id, chat_id)

    set_state(user_id, chat_id, "adm_awaiting_const_value",
              data={"name": name, "page": page, "_mid": call.message.message_id})
    bot.answer_callback_query(call.id)

    try:
        bot.edit_message_text(
            f"✏️ <b>تعديل الثابت: {name}</b>\n\nأرسل القيمة الجديدة:",
            chat_id, call.message.message_id, parse_mode="HTML"
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# 👨‍💻 إدارة المطورين
# ══════════════════════════════════════════

@register_action("adm_devs")
def show_developers(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if not is_primary_dev(user_id):
        bot.answer_callback_query(call.id, "❌ فقط المطور الأساسي.", show_alert=True)
        return

    devs  = get_all_developers()
    owner = (user_id, chat_id)

    text = f"👨‍💻 <b>قائمة المطورين</b>\n{get_lines()}\n\n"
    buttons = []
    for d in devs:
        role_ar = "👑 أساسي" if d["role"] == "primary" else "🔧 ثانوي"
        text += f"{role_ar} — ID: <code>{d['user_id']}</code>\n"
        if d["user_id"] != user_id:
            if d["role"] == "secondary":
                buttons.append(btn(f"⬆️ ترقية {d['user_id']}", "adm_promote_dev",
                                   data={"uid": d["user_id"]}, owner=owner, color=_GRN))
            else:
                buttons.append(btn(f"⬇️ تخفيض {d['user_id']}", "adm_demote_dev",
                                   data={"uid": d["user_id"]}, owner=owner, color=_RED))
            buttons.append(btn(f"🗑 إزالة {d['user_id']}", "adm_remove_dev",
                               data={"uid": d["user_id"]}, owner=owner, color=_RED))

    buttons.append(btn("➕ إضافة مطور", "adm_add_dev_prompt", data={}, owner=owner, color=_GRN))
    buttons.append(_back("adm_main_back", {}, owner))

    layout = [2] * (len(buttons) // 2) + ([1] if len(buttons) % 2 else []) + [1]
    edit_ui(call, text=text, buttons=buttons, layout=layout)


@register_action("adm_promote_dev")
def promote_dev(call, data):
    if not is_primary_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط.", show_alert=True)
        return
    promote_developer(int(data["uid"]))
    bot.answer_callback_query(call.id, "✅ تمت الترقية", show_alert=True)
    show_developers(call, {})


@register_action("adm_demote_dev")
def demote_dev(call, data):
    if not is_primary_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط.", show_alert=True)
        return
    demote_developer(int(data["uid"]))
    bot.answer_callback_query(call.id, "✅ تم التخفيض", show_alert=True)
    show_developers(call, {})


@register_action("adm_remove_dev")
def remove_dev(call, data):
    if not is_primary_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط.", show_alert=True)
        return
    ok = remove_developer(int(data["uid"]))
    bot.answer_callback_query(call.id, "✅ تمت الإزالة" if ok else "❌ لا يمكن إزالة هذا المطور",
                              show_alert=True)
    show_developers(call, {})


@register_action("adm_add_dev_prompt")
def add_dev_prompt(call, data):
    if not is_primary_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط.", show_alert=True)
        return
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    set_state(user_id, chat_id, "adm_awaiting_new_dev",
              data={"_mid": call.message.message_id})
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(
            "➕ <b>إضافة مطور جديد</b>\n\nأرسل ID المستخدم:",
            chat_id, call.message.message_id, parse_mode="HTML"
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# 🔇 الكتم العالمي
# ══════════════════════════════════════════

@register_action("adm_global_mutes")
def show_global_mutes(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if not is_any_dev(user_id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return

    page  = int(data.get("page", 0))
    mutes = get_global_mutes()
    items, total_pages = paginate_list(mutes, page, per_page=8)
    owner = (user_id, chat_id)

    text = f"🔇 <b>الكتم العالمي</b> ({len(mutes)} مكتوم)\n{get_lines()}\n\n"
    buttons = []
    for m in items:
        reason_label = (m.get('reason') or '').strip()
        text += f"🔇 <code>{m['user_id']}</code>"
        if reason_label:
            text += f" — {reason_label}"
        text += "\n"
        buttons.append(btn(f"🔊 {m['user_id']}", "adm_global_unmute",
                           data={"uid": m["user_id"], "page": page},
                           owner=owner, color=_GRN))

    buttons.append(btn("➕ كتم مستخدم", "adm_global_mute_prompt",
                       data={"page": page}, owner=owner, color=_RED))

    nav = []
    if page > 0:
        nav.append(btn("◀️", "adm_global_mutes", data={"page": page-1}, owner=owner))
    if page < total_pages - 1:
        nav.append(btn("▶️", "adm_global_mutes", data={"page": page+1}, owner=owner))
    nav.append(_back("adm_main_back", {}, owner))

    layout = [1] * len(buttons) + ([len(nav)] if nav else [1])
    edit_ui(call, text=text or "✅ لا يوجد مكتومون عالمياً.",
            buttons=buttons + nav, layout=layout)


@register_action("adm_global_unmute")
def do_global_unmute(call, data):
    if not is_any_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return
    ok, _ = global_unmute(int(data["uid"]))
    bot.answer_callback_query(call.id,
                              "✅ تم رفع الكتم العالمي" if ok else "❌ المستخدم غير مكتوم",
                              show_alert=True)
    show_global_mutes(call, {"page": data.get("page", 0)})


@register_action("adm_global_mute_prompt")
def global_mute_prompt(call, data):
    if not is_any_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    set_state(user_id, chat_id, "adm_awaiting_global_mute",
              data={"_mid": call.message.message_id, "page": data.get("page", 0)})
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(
            "🔇 <b>كتم عالمي</b>\n\nأرسل: <code>ID السبب</code>\nمثال: <code>123456789 سبام</code>",
            chat_id, call.message.message_id, parse_mode="HTML"
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# 🔕 كتم المجموعة
# ══════════════════════════════════════════

@register_action("adm_group_mutes")
def show_group_mutes(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if not is_any_dev(user_id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return

    page  = int(data.get("page", 0))
    mutes = get_group_mutes(chat_id)
    items, total_pages = paginate_list(mutes, page, per_page=8)
    owner = (user_id, chat_id)

    text = f"🔕 <b>كتم المجموعة</b> ({len(mutes)} مكتوم)\n{get_lines()}\n\n"
    buttons = []
    for m in items:
        reason_label = (m.get('reason') or '').strip()
        text += f"🔕 ID: <code>{m['user_id']}</code>"
        if reason_label:
            text += f" | {reason_label}"
        text += "\n"
        buttons.append(btn(f"🔊 رفع {m['user_id']}", "adm_group_unmute",
                           data={"uid": m["user_id"], "gid": chat_id, "page": page},
                           owner=owner, color=_GRN))

    buttons.append(btn("➕ كتم في المجموعة", "adm_group_mute_prompt",
                       data={"gid": chat_id, "page": page}, owner=owner, color=_RED))

    nav = []
    if page > 0:
        nav.append(btn("◀️", "adm_group_mutes", data={"page": page-1}, owner=owner))
    if page < total_pages - 1:
        nav.append(btn("▶️", "adm_group_mutes", data={"page": page+1}, owner=owner))
    nav.append(_back("adm_main_back", {}, owner))

    layout = [1] * len(buttons) + ([len(nav)] if nav else [1])
    edit_ui(call, text=text or "✅ لا يوجد مكتومون في هذه المجموعة.",
            buttons=buttons + nav, layout=layout)


@register_action("adm_group_unmute")
def do_group_unmute(call, data):
    if not is_any_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return
    ok = group_unmute(int(data["uid"]), int(data["gid"]))
    bot.answer_callback_query(call.id,
                              f"🔊 تم رفع الكتم عن المستخدم {data['uid']}" if ok
                              else "❌ المستخدم غير مكتوم في هذه المجموعة.",
                              show_alert=True)
    show_group_mutes(call, {"page": data.get("page", 0)})


@register_action("adm_group_mute_prompt")
def group_mute_prompt(call, data):
    if not is_any_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    set_state(user_id, chat_id, "adm_awaiting_group_mute",
              data={"_mid": call.message.message_id, "gid": data.get("gid", chat_id),
                    "page": data.get("page", 0)})
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(
            "🔕 <b>كتم في المجموعة</b>\n\nأرسل: <code>ID السبب</code>",
            chat_id, call.message.message_id, parse_mode="HTML"
        )
    except Exception:
        pass


# ══════════════════════════════════════════
# 🔙 رجوع للرئيسية
# ══════════════════════════════════════════

@register_action("adm_main_back")
def back_to_main(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    if not is_any_dev(user_id):
        return
    owner = (user_id, chat_id)
    buttons = [
        btn("⚙️ ثوابت البوت",        "adm_constants",   data={"page": 0}, owner=owner, color=_BLUE),
        btn("👨‍💻 المطورون",           "adm_devs",        data={},          owner=owner, color=_BLUE),
        btn("🔇 الكتم العالمي",       "adm_global_mutes",data={"page": 0}, owner=owner, color=_RED),
        btn("🔕 كتم المجموعة",        "adm_group_mutes", data={"page": 0}, owner=owner, color=_RED),
        btn("📿 إدارة الأذكار",       "adm_azkar_panel",         data={}, owner=owner, color=_BLUE),
        btn("📰 المجلة والهدايا",     "adm_magazine_panel",      data={}, owner=owner, color=_BLUE),
        btn("📚 إدارة المحتوى",       "adm_content_hub",         data={}, owner=owner, color=_BLUE),
        btn("📖 إدارة القرآن",        "adm_quran_panel",         data={}, owner=owner, color=_BLUE),
        btn("🎮 إعادة تعيين الألعاب", "adm_reset_games_confirm", data={}, owner=owner, color=_RED),
        btn("🔄 إعادة تحميل الآيات", "adm_reload_ayat_confirm", data={}, owner=owner, color=_RED),
        btn("🗑 مسح قاعدة البيانات", "adm_reset_db_confirm",    data={}, owner=owner, color=_RED),
    ]
    edit_ui(call,
            text=f"🛠 <b>لوحة إدارة البوت</b>\n{get_lines()}\nاختر ما تريد إدارته:",
            buttons=buttons, layout=[2, 2, 2, 2, 2, 1])


# ══════════════════════════════════════════
# 📝 معالج الإدخال النصي
# ══════════════════════════════════════════

def handle_admin_input(message) -> bool:
    """
    يعالج الإدخال النصي لحالات الانتظار في لوحة الإدارة.
    يرجع True إذا تم التعامل مع الرسالة.
    """
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not is_any_dev(user_id):
        return False

    state = get_state(user_id, chat_id)
    if not state or "state" not in state:
        return False

    s = state["state"]

    # ── يتعامل فقط مع حالات admin_panel ──
    _HANDLED_STATES = {
        "adm_awaiting_const_value",
        "adm_awaiting_new_dev",
        "adm_awaiting_global_mute",
        "adm_awaiting_group_mute",
    }
    if s not in _HANDLED_STATES:
        return False   # اترك الحالة لمعالجات أخرى

    sdata = state.get("data", {})
    text  = (message.text or "").strip()
    mid   = sdata.get("_mid")   # get بدلاً من pop
    clear_state(user_id, chat_id)

    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass

    def _edit(msg_text):
        if mid:
            try:
                bot.edit_message_text(msg_text, chat_id, mid, parse_mode="HTML")
            except Exception:
                pass

    # ─── تعديل ثابت ───
    if s == "adm_awaiting_const_value":
        name = sdata.get("name")
        page = sdata.get("page", 0)
        if set_const(name, text):
            _edit(f"✅ تم تحديث <b>{name}</b> = <code>{text}</code>")
        else:
            _edit(f"❌ فشل تحديث الثابت <b>{name}</b>")
        return True

    # ─── إضافة مطور ───
    if s == "adm_awaiting_new_dev":
        if not is_primary_dev(user_id):
            return True
        parts = text.split()
        uid_str = parts[0] if parts else ""
        role    = parts[1] if len(parts) > 1 else "secondary"
        if uid_str.isdigit():
            add_developer(int(uid_str), role)
            _edit(f"✅ تمت إضافة المطور <code>{uid_str}</code> كـ {role}")
        else:
            _edit("❌ ID غير صالح")
        return True

    # ─── كتم عالمي ───
    if s == "adm_awaiting_global_mute":
        parts  = text.split(maxsplit=1)
        uid_str = parts[0] if parts else ""
        reason  = parts[1] if len(parts) > 1 else ""
        if uid_str.isdigit():
            global_mute(int(uid_str), user_id, reason)
            _edit(
                f"🔇 تم كتم المستخدم <code>{uid_str}</code> عالمياً."
                + (f"\n📝 السبب: {reason}" if reason else "")
            )
        else:
            _edit("❌ ID غير صالح.")
        return True

    # ─── كتم في المجموعة ───
    if s == "adm_awaiting_group_mute":
        gid    = sdata.get("gid", chat_id)
        parts  = text.split(maxsplit=1)
        uid_str = parts[0] if parts else ""
        reason  = parts[1] if len(parts) > 1 else ""
        if uid_str.isdigit():
            group_mute(int(uid_str), int(gid), user_id, reason)
            _edit(
                f"🔕 تم كتم المستخدم <code>{uid_str}</code> في هذه المجموعة."
                + (f"\n📝 السبب: {reason}" if reason else "")
            )
        else:
            _edit("❌ ID غير صالح.")
        return True

    return False


# ══════════════════════════════════════════
# 📿 إدارة الأذكار
# ══════════════════════════════════════════

@register_action("adm_azkar_panel")
def adm_azkar_panel(call, data):
    if not is_any_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return
    from modules.azkar.azkar_handler import _send_admin_panel
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)
    bot.answer_callback_query(call.id)
    _send_admin_panel(cid, uid, owner, call=call)


@register_action("adm_magazine_panel")
def adm_magazine_panel(call, data):
    if not is_any_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return
    from modules.magazine.magazine_handler import open_magazine_admin
    uid = call.from_user.id
    cid = call.message.chat.id
    bot.answer_callback_query(call.id)
    open_magazine_admin(cid, uid, call=call)


@register_action("adm_content_hub")
def adm_content_hub(call, data):
    if not is_any_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    from handlers.group_admin.developer.dev_control_panel import _show_content_hub_panel
    _show_content_hub_panel(call)


@register_action("adm_quran_panel")
def adm_quran_panel(call, data):
    if not is_any_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    from handlers.group_admin.developer.dev_control_panel import _show_quran_dev_panel
    _show_quran_dev_panel(call)


# ══════════════════════════════════════════
# 🎮 إعادة تعيين بيانات الألعاب
# ══════════════════════════════════════════

@register_action("adm_reset_games_confirm")
def reset_games_confirm(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if not is_primary_dev(user_id):
        bot.answer_callback_query(call.id, "❌ فقط المطور الأساسي.", show_alert=True)
        return

    owner = (user_id, chat_id)
    edit_ui(call,
        text=(
            "⚠️ <b>إعادة تعيين بيانات الألعاب</b>\n"
            f"{get_lines()}\n\n"
            "سيتم حذف جميع بيانات اللعب:\n"
            "• الدول والمدن والمباني والجيوش\n"
            "• التحالفات والحروب والمعارك\n"
            "• الأرصدة والقروض والاقتصاد\n"
            "• الإنجازات والمواسم والنفوذ\n"
            "• المهام اليومية والكولداون\n\n"
            "✅ <b>لن يُمس:</b>\n"
            "المستخدمون، الأسماء، المجموعات،\n"
            "الأذكار، الختمة، القرآن، التذاكر.\n\n"
            "⚠️ <b>هذا الإجراء لا يمكن التراجع عنه!</b>\n\nهل أنت متأكد؟"
        ),
        buttons=[
            btn("✅ تأكيد الإعادة", "adm_reset_games_execute", data={},
                owner=owner, color=_RED),
            btn("❌ إلغاء", "adm_main_back", data={},
                owner=owner, color=_GRN),
        ],
        layout=[1, 1]
    )


@register_action("adm_reset_games_execute")
def reset_games_execute(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if not is_primary_dev(user_id):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط.", show_alert=True)
        return

    bot.answer_callback_query(call.id, "⏳ جاري إعادة التعيين...")

    ok, summary = _execute_games_reset(user_id)

    try:
        bot.edit_message_text(
            f"{'✅' if ok else '❌'} <b>إعادة تعيين الألعاب</b>\n{get_lines()}\n\n{summary}",
            chat_id, call.message.message_id, parse_mode="HTML"
        )
    except Exception:
        pass


def _execute_games_reset(executed_by: int) -> tuple[bool, str]:
    """
    يحذف جميع بيانات اللعب بشكل transactional.
    يحافظ على: users, user_accounts, countries, cities, buildings,
               alliances, bot_constants, bot_developers, mutes.
    """
    from database.connection import get_db_conn
    from utils.logger import log_event

    # الجداول التي تُحذف بالكامل (بيانات اللعب فقط)
    # محفوظ: users, users_name, groups, group_members, bot_constants, bot_developers,
    #         global_mutes, group_mutes, azkar*, khatma*, quran*, tickets*, magazine*
    GAME_TABLES = [
        # تقدم اللاعبين
        "user_achievements", "season_history", "season_titles", "country_influence",
        # دول ومدن وبنية تحتية
        "countries", "cities", "city_buildings", "city_troops", "city_equipment",
        "country_assets", "country_resources",
        # معارك وحروب
        "country_battles", "battle_state", "battle_effects", "battle_events",
        "battle_action_cooldowns", "battle_history", "battle_losses", "battles",
        "war_costs_log", "support_requests",
        # جيش وصيانة
        "army_maintenance", "army_fatigue", "country_recovery",
        "injured_troops", "damaged_equipment", "repair_queue",
        # تجسس واستكشاف
        "spy_operations", "discovered_countries", "exploration_log", "spy_agents",
        # اقتصاد وبنك
        "loans", "bank_cooldowns", "city_budget",
        "alliance_support_stats", "user_accounts",
        # تحالفات
        "alliances", "alliance_members", "alliance_wars",
        # مهام وكولداون
        "daily_tasks", "action_cooldowns",
        # أحداث عالمية
        "global_events",
    ]

    conn = get_db_conn()
    cursor = conn.cursor()
    deleted = {}
    errors  = []

    try:
        cursor.execute("BEGIN")

        for table in GAME_TABLES:
            try:
                cursor.execute(f"DELETE FROM {table}")
                deleted[table] = cursor.rowcount
            except Exception as e:
                # الجدول قد لا يوجد — تجاهل بأمان
                errors.append(f"{table}: {e}")

        conn.commit()

    except Exception as e:
        conn.rollback()
        return False, f"❌ فشلت العملية: {e}"

    # تسجيل الحدث
    log_event("games_reset", user=executed_by,
              tables_cleared=len(deleted),
              total_rows=sum(deleted.values()))

    total_rows = sum(deleted.values())
    summary = (
        f"✅ تمت إعادة التعيين بنجاح!\n\n"
        f"📊 الجداول المُعادة: {len(deleted)}\n"
        f"🗑 الصفوف المحذوفة: {total_rows}\n"
        f"👤 بواسطة: <code>{executed_by}</code>"
    )
    if errors:
        summary += f"\n\n⚠️ تجاهل {len(errors)} جدول غير موجود."

    return True, summary


# ══════════════════════════════════════════
# 🗑 مسح قاعدة البيانات
# ══════════════════════════════════════════

@register_action("adm_reset_db_confirm")
def reset_db_confirm(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if not is_primary_dev(user_id):
        bot.answer_callback_query(call.id, "❌ فقط المطور الأساسي يمكنه مسح قاعدة البيانات.",
                                  show_alert=True)
        return

    owner = (user_id, chat_id)
    edit_ui(
        call,
        text=(
            "⚠️ <b>تحذير: مسح قاعدة البيانات</b>\n"
            f"{get_lines()}\n"
            "سيتم حذف <b>جميع البيانات</b> بشكل نهائي:\n"
            "• جميع المستخدمين والدول والمدن\n"
            "• جميع الأرصدة والمعارك والتحالفات\n"
            "• جميع الإنجازات والمواسم\n\n"
            "⚠️ <b>هذا الإجراء لا يمكن التراجع عنه!</b>\n\n"
            "هل أنت متأكد؟"
        ),
        buttons=[
            btn("✅ نعم، امسح كل شيء", "adm_reset_db_execute", data={},
                owner=owner, color=_RED),
            btn("❌ لا، تراجع",         "adm_main_back",        data={},
                owner=owner, color=_GRN),
        ],
        layout=[1, 1]
    )


@register_action("adm_reset_db_execute")
def reset_db_execute(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if not is_primary_dev(user_id):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط.", show_alert=True)
        return

    bot.answer_callback_query(call.id, "⏳ جاري مسح قاعدة البيانات...")

    try:
        from database.reset_db import reset_database
        from database.update_db import update_database
        ok, err_msg = reset_database()

        if not ok:
            try:
                bot.edit_message_text(
                    f"⚠️ <b>تعذّر مسح قاعدة البيانات</b>\n{err_msg}",
                    chat_id, call.message.message_id, parse_mode="HTML"
                )
            except Exception:
                pass
            return

        update_database()

        # إعادة بذر الثوابت الافتراضية
        from database.db_schema.admin_system import _seed_defaults
        from database.connection import get_db_conn as _get
        _seed_defaults(_get())

        try:
            bot.edit_message_text(
                "✅ <b>تم مسح قاعدة البيانات وإعادة إنشائها بنجاح!</b>\n"
                "جميع الثوابت الافتراضية تم استعادتها.",
                chat_id, call.message.message_id, parse_mode="HTML"
            )
        except Exception:
            pass

    except Exception as e:
        try:
            bot.edit_message_text(
                f"❌ <b>فشل مسح قاعدة البيانات!</b>\n<code>{e}</code>",
                chat_id, call.message.message_id, parse_mode="HTML"
            )
        except Exception:
            pass


# ══════════════════════════════════════════
# 🔄 إعادة تحميل الآيات
# ══════════════════════════════════════════

@register_action("adm_reload_ayat_confirm")
def reload_ayat_confirm(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if not is_primary_dev(user_id):
        bot.answer_callback_query(call.id, "❌ فقط المطور الأساسي.", show_alert=True)
        return

    owner = (user_id, chat_id)
    edit_ui(
        call,
        text=(
            "⚠️ <b>إعادة تحميل الآيات</b>\n"
            f"{get_lines()}\n\n"
            "سيتم <b>حذف جميع الآيات</b> من قاعدة البيانات\n"
            "وإعادة تحميلها من API.\n\n"
            "⚠️ <b>هذا الإجراء لا يمكن التراجع عنه!</b>\n\n"
            "هل أنت متأكد؟"
        ),
        buttons=[
            btn("✅ تأكيد الإعادة", "adm_reload_ayat_execute", data={},
                owner=owner, color=_RED),
            btn("❌ إلغاء", "adm_main_back", data={},
                owner=owner, color=_GRN),
        ],
        layout=[1, 1],
    )


@register_action("adm_reload_ayat_execute")
def reload_ayat_execute(call, data):
    import threading

    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if not is_primary_dev(user_id):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط.", show_alert=True)
        return

    bot.answer_callback_query(call.id, "⏳ جاري إعادة التحميل...")

    # ── إنشاء رسالة التقدم الوحيدة ──
    header   = "🔄 <b>إعادة تحميل الآيات</b>\n" + get_lines() + "\n\n"
    init_msg = header + "⏳ جاري التحميل...\nقد تستغرق العملية بعض الوقت."

    try:
        progress_msg = bot.send_message(chat_id, init_msg, parse_mode="HTML")
        prog_mid     = progress_msg.message_id
    except Exception:
        prog_mid = None

    # ── تراكم سطور التقدم وتحديث الرسالة ──
    lines = []

    def _edit_progress():
        if not prog_mid:
            return
        body = "\n".join(lines[-60:])   # آخر 60 سطر لتجنب تجاوز حد تيليغرام
        try:
            bot.edit_message_text(
                header + body,
                chat_id, prog_mid, parse_mode="HTML"
            )
        except Exception:
            pass

    def _progress(msg: str):
        lines.append(msg)
        _edit_progress()

    # ── تشغيل العملية في thread منفصل لعدم تجميد البوت ──
    def _run():
        from modules.quran import quran_db as qr_db
        ok, summary = qr_db.reload_ayat_from_api(progress_callback=_progress)

        final = header + "\n".join(lines[-60:]) + f"\n\n{'✅' if ok else '❌'} {summary}"
        if prog_mid:
            try:
                bot.edit_message_text(final, chat_id, prog_mid, parse_mode="HTML")
                return
            except Exception:
                pass
        bot.send_message(chat_id, f"{'✅' if ok else '❌'} {summary}", parse_mode="HTML")

    threading.Thread(target=_run, daemon=True).start()
