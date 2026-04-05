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

    _send_main_panel(chat_id, user_id)


def _send_main_panel(chat_id, user_id):
    owner = (user_id, chat_id)
    buttons = [
        btn("⚙️ ثوابت البوت",    "adm_constants",   data={"page": 0}, owner=owner, color=_BLUE),
        btn("👨‍💻 المطورون",       "adm_devs",        data={},          owner=owner, color=_BLUE),
        btn("🔇 الكتم العالمي",   "adm_global_mutes",data={"page": 0}, owner=owner, color=_RED),
        btn("🔕 كتم المجموعة",    "adm_group_mutes", data={"page": 0}, owner=owner, color=_RED),
        btn("🗑 مسح قاعدة البيانات", "adm_reset_db_confirm", data={}, owner=owner, color=_RED),
    ]
    send_ui(chat_id,
            text=f"🛠 <b>لوحة إدارة البوت</b>\n{get_lines()}\nاختر ما تريد إدارته:",
            buttons=buttons, layout=[2, 2, 1], owner_id=user_id)


# ══════════════════════════════════════════
# ⚙️ ثوابت البوت
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

    text = f"⚙️ <b>ثوابت البوت</b> (صفحة {page+1}/{total_pages})\n{get_lines()}\n\n"
    buttons = []
    for c in items:
        text += f"🔹 <b>{c['name']}</b> = <code>{c['value']}</code>\n   {c['description']}\n\n"
        if is_primary_dev(user_id):
            buttons.append(btn(f"✏️ {c['name']}", "adm_edit_const",
                               data={"name": c["name"], "page": page},
                               owner=owner, color=_BLUE))

    nav = []
    if page > 0:
        nav.append(btn("◀️", "adm_constants", data={"page": page-1}, owner=owner))
    if page < total_pages - 1:
        nav.append(btn("▶️", "adm_constants", data={"page": page+1}, owner=owner))
    nav.append(_back("adm_main_back", {}, owner))

    layout = [1] * len(buttons) + ([len(nav)] if nav else [1])
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
        text += f"🔇 ID: <code>{m['user_id']}</code> | {m.get('reason','') or 'بدون سبب'}\n"
        buttons.append(btn(f"🔊 رفع كتم {m['user_id']}", "adm_global_unmute",
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
    global_unmute(int(data["uid"]))
    bot.answer_callback_query(call.id, "✅ تم رفع الكتم العالمي", show_alert=True)
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
        text += f"🔕 ID: <code>{m['user_id']}</code> | {m.get('reason','') or 'بدون سبب'}\n"
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
    group_unmute(int(data["uid"]), int(data["gid"]))
    bot.answer_callback_query(call.id, "✅ تم رفع الكتم", show_alert=True)
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
        btn("⚙️ ثوابت البوت",    "adm_constants",   data={"page": 0}, owner=owner, color=_BLUE),
        btn("👨‍💻 المطورون",       "adm_devs",        data={},          owner=owner, color=_BLUE),
        btn("🔇 الكتم العالمي",   "adm_global_mutes",data={"page": 0}, owner=owner, color=_RED),
        btn("🔕 كتم المجموعة",    "adm_group_mutes", data={"page": 0}, owner=owner, color=_RED),
        btn("🗑 مسح قاعدة البيانات", "adm_reset_db_confirm", data={}, owner=owner, color=_RED),
    ]
    edit_ui(call,
            text=f"🛠 <b>لوحة إدارة البوت</b>\n{get_lines()}\nاختر ما تريد إدارته:",
            buttons=buttons, layout=[2, 2, 1])


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
            _edit(f"🔇 تم الكتم العالمي للمستخدم <code>{uid_str}</code>")
        else:
            _edit("❌ ID غير صالح")
        return True

    # ─── كتم في المجموعة ───
    if s == "adm_awaiting_group_mute":
        gid    = sdata.get("gid", chat_id)
        parts  = text.split(maxsplit=1)
        uid_str = parts[0] if parts else ""
        reason  = parts[1] if len(parts) > 1 else ""
        if uid_str.isdigit():
            group_mute(int(uid_str), int(gid), user_id, reason)
            _edit(f"🔕 تم الكتم في المجموعة للمستخدم <code>{uid_str}</code>")
        else:
            _edit("❌ ID غير صالح")
        return True

    return False


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
