"""
معالج الأذكار — أذكار الصباح والمساء مع تتبع التقدم.
"""
from core.bot import bot
from utils.pagination import btn, send_ui, edit_ui, register_action
from utils.helpers import get_lines
from modules.azkar import azkar_db as db

TYPE_MORNING = 0
TYPE_EVENING = 1
TYPE_SLEEP   = 2
TYPE_WAKEUP  = 3

TYPE_LABELS = {
    TYPE_MORNING: "الصباح",
    TYPE_EVENING: "المساء",
    TYPE_SLEEP:   "النوم",
    TYPE_WAKEUP:  "الاستيقاظ",
}
TYPE_EMOJI = {
    TYPE_MORNING: "🌅",
    TYPE_EVENING: "🌙",
    TYPE_SLEEP:   "😴",
    TYPE_WAKEUP:  "☀️",
}


# ══════════════════════════════════════════
# نقطة الدخول النصية
# ══════════════════════════════════════════

def handle_azkar_command(message) -> bool:
    text = (message.text or "").strip()
    if text == "أذكار الصباح":
        _open_azkar(message, TYPE_MORNING)
        return True
    if text == "أذكار المساء":
        _open_azkar(message, TYPE_EVENING)
        return True
    if text == "أذكار النوم":
        _open_azkar(message, TYPE_SLEEP)
        return True
    if text == "أذكار الاستيقاظ":
        _open_azkar(message, TYPE_WAKEUP)
        return True
    return False


# ══════════════════════════════════════════
# فتح الأذكار
# ══════════════════════════════════════════

def _open_azkar(message, zikr_type: int):
    uid   = message.from_user.id
    cid   = message.chat.id
    azkar = db.get_azkar_list(zikr_type)
    if not azkar:
        bot.reply_to(message, "❌ لا توجد أذكار متاحة حالياً.")
        return

    prog = db.get_progress(uid, zikr_type)
    idx  = prog["zikr_index"]

    if idx >= len(azkar):
        db.reset_progress(uid, zikr_type)
        idx = 0

    zikr      = azkar[idx]
    remaining = prog["remaining"] if prog["remaining"] >= 0 else zikr["repeat_count"]
    db.save_progress(uid, zikr_type, idx, remaining)

    _send_zikr(cid, uid, zikr_type, azkar, idx, remaining,
               reply_to=message.message_id)


def _open_azkar_for_user(chat_id: int, uid: int, zikr_type: int):
    """يفتح الأذكار مباشرة بدون رسالة أصلية — يُستخدم من المُجدوِل."""
    azkar = db.get_azkar_list(zikr_type)
    if not azkar:
        return

    prog = db.get_progress(uid, zikr_type)
    idx  = prog["zikr_index"]

    if idx >= len(azkar):
        db.reset_progress(uid, zikr_type)
        idx = 0

    zikr      = azkar[idx]
    remaining = prog["remaining"] if prog["remaining"] >= 0 else zikr["repeat_count"]
    db.save_progress(uid, zikr_type, idx, remaining)

    _send_zikr(chat_id, uid, zikr_type, azkar, idx, remaining)


# ══════════════════════════════════════════
# بناء وإرسال الذكر
# ══════════════════════════════════════════

def _send_zikr(cid, uid, zikr_type, azkar, idx, remaining,
               reply_to=None, call=None):
    total = len(azkar)
    zikr  = azkar[idx]
    emoji = TYPE_EMOJI[zikr_type]
    label = TYPE_LABELS[zikr_type]

    text = (
        f"{emoji} <b>أذكار {label}</b>  ({idx+1}/{total})\n"
        f"{get_lines()}\n\n"
        f"{zikr['text']}\n\n"
        f"🔁 التكرار: <b>{remaining}</b> / {zikr['repeat_count']}"
    )

    owner = (uid, cid)
    buttons = _build_buttons(owner, zikr_type, idx, remaining, total, zikr)

    # layout: [تسبيح] [السابق، التالي، إغلاق]
    layout = [1, 3]

    if call:
        edit_ui(call, text=text, buttons=buttons, layout=layout)
    else:
        send_ui(cid, text=text, buttons=buttons, layout=layout,
                owner_id=uid, reply_to=reply_to)


# def _build_buttons(owner, zikr_type, idx, remaining, total, zikr):
#     t = zikr_type
#     buttons = [
#         # زر التسبيح — يعرض العدد المتبقي
#         btn(f"({remaining})", "azkar_tasbih",
#             {"t": t, "i": idx, "r": remaining}, owner=owner, color="su"),
#         # تنقل
#         btn("التالي ◀️", "azkar_nav",
#             {"t": t, "i": min(total-1, idx+1)}, owner=owner,
#             color="p" if idx < total-1 else "d"),
        
#         btn("❌ إغلاق", "azkar_close", {"t": t}, owner=owner, color="d"),
        
#         btn("▶️ السابق", "azkar_nav",
#             {"t": t, "i": max(0, idx-1)}, owner=owner,
#             color="p" if idx > 0 else "d"),
#     ]
#     return buttons

def _build_buttons(owner, zikr_type, idx, remaining, total, zikr):
    t = zikr_type

    buttons = [
        # زر التسبيح
        btn(f"({remaining})", "azkar_tasbih",
            {"t": t, "i": idx, "r": remaining}, owner=owner, color="su"),
    ]

    if idx < total - 1:
        buttons.append(btn("التالي ◀️", "azkar_nav", {"t": t, "i": idx+1}, owner=owner, color="p"))
        
    buttons.append(btn("❌ إغلاق", "azkar_close", {"t": t}, owner=owner, color="d"),)
    
    if idx > 0:
        buttons.append(btn("▶️ السابق", "azkar_nav", {"t": t, "i": idx-1}, owner=owner, color="p"))

    return buttons

# ══════════════════════════════════════════
# معالجات الأزرار
# ══════════════════════════════════════════

@register_action("azkar_tasbih")
def on_tasbih(call, data):
    uid       = call.from_user.id
    cid       = call.message.chat.id
    zikr_type = int(data["t"])
    idx       = int(data["i"])
    remaining = int(data["r"])

    azkar = db.get_azkar_list(zikr_type)
    if not azkar or idx >= len(azkar):
        bot.answer_callback_query(call.id)
        return

    remaining -= 1

    if remaining <= 0:
        # انتقل للذكر التالي تلقائياً
        next_idx = idx + 1
        if next_idx >= len(azkar):
            # أنهى الكل
            db.reset_progress(uid, zikr_type)
            bot.answer_callback_query(call.id, "🎉 أتممت الأذكار!", show_alert=True)
            label = TYPE_LABELS[zikr_type]
            emoji = TYPE_EMOJI[zikr_type]
            try:
                bot.edit_message_text(
                    f"{emoji} <b>أحسنت! أتممت أذكار {label} 🎉</b>\n\n"
                    f"اكتب <code>أذكار {label}</code> للبدء من جديد.",
                    cid, call.message.message_id, parse_mode="HTML"
                )
            except Exception:
                pass
            return

        # الذكر التالي
        next_zikr = azkar[next_idx]
        remaining = next_zikr["repeat_count"]
        db.save_progress(uid, zikr_type, next_idx, remaining)
        bot.answer_callback_query(call.id, "✅ انتقلت للذكر التالي")
        _send_zikr(cid, uid, zikr_type, azkar, next_idx, remaining, call=call)
    else:
        db.save_progress(uid, zikr_type, idx, remaining)
        bot.answer_callback_query(call.id)
        _send_zikr(cid, uid, zikr_type, azkar, idx, remaining, call=call)


@register_action("azkar_nav")
def on_nav(call, data):
    uid       = call.from_user.id
    cid       = call.message.chat.id
    zikr_type = int(data["t"])
    idx       = int(data["i"])

    azkar = db.get_azkar_list(zikr_type)
    if not azkar or idx >= len(azkar):
        bot.answer_callback_query(call.id)
        return

    zikr      = azkar[idx]
    prog      = db.get_progress(uid, zikr_type)
    # إذا انتقل للذكر نفسه الذي كان فيه → استخدم remaining المحفوظ
    if prog["zikr_index"] == idx and prog["remaining"] >= 0:
        remaining = prog["remaining"]
    else:
        remaining = zikr["repeat_count"]

    db.save_progress(uid, zikr_type, idx, remaining)
    bot.answer_callback_query(call.id)
    _send_zikr(cid, uid, zikr_type, azkar, idx, remaining, call=call)


@register_action("azkar_close")
def on_close(call, data):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


# ══════════════════════════════════════════
# لوحة المطور — إدارة الأذكار
# ══════════════════════════════════════════

def open_azkar_admin(message):
    """يفتح لوحة إدارة الأذكار للمطور."""
    uid   = message.from_user.id
    cid   = message.chat.id
    owner = (uid, cid)
    _send_admin_panel(cid, uid, owner)


def _send_admin_panel(cid, uid, owner, call=None):
    counts = {t: len(db.get_azkar_list(t))
              for t in (TYPE_MORNING, TYPE_EVENING, TYPE_SLEEP, TYPE_WAKEUP)}
    text = (
        f"📿 <b>إدارة الأذكار</b>\n{get_lines()}\n\n"
        f"🌅 أذكار الصباح: <b>{counts[TYPE_MORNING]}</b> ذكر\n"
        f"🌙 أذكار المساء: <b>{counts[TYPE_EVENING]}</b> ذكر\n"
        f"😴 أذكار النوم: <b>{counts[TYPE_SLEEP]}</b> ذكر\n"
        f"☀️ أذكار الاستيقاظ: <b>{counts[TYPE_WAKEUP]}</b> ذكر\n\n"
        f"اختر نوع الأذكار:"
    )
    buttons = [
        btn("🌅 الصباح",     "azkar_adm_list", {"t": TYPE_MORNING, "p": 0}, owner=owner, color="p"),
        btn("🌙 المساء",      "azkar_adm_list", {"t": TYPE_EVENING, "p": 0}, owner=owner, color="p"),
        btn("😴 النوم",       "azkar_adm_list", {"t": TYPE_SLEEP,   "p": 0}, owner=owner, color="p"),
        btn("☀️ الاستيقاظ",  "azkar_adm_list", {"t": TYPE_WAKEUP,  "p": 0}, owner=owner, color="p"),
        btn("➕ إضافة صباح",  "azkar_adm_add",  {"t": TYPE_MORNING},         owner=owner, color="su"),
        btn("➕ إضافة مساء",  "azkar_adm_add",  {"t": TYPE_EVENING},         owner=owner, color="su"),
        btn("➕ إضافة نوم",   "azkar_adm_add",  {"t": TYPE_SLEEP},           owner=owner, color="su"),
        btn("➕ إضافة استيقاظ","azkar_adm_add", {"t": TYPE_WAKEUP},          owner=owner, color="su"),
    ]
    if call:
        edit_ui(call, text=text, buttons=buttons, layout=[2, 2, 2, 2])
    else:
        send_ui(cid, text=text, buttons=buttons, layout=[2, 2, 2, 2], owner_id=uid)


@register_action("azkar_adm_list")
def on_adm_list(call, data):
    from utils.pagination import paginate_list
    uid       = call.from_user.id
    cid       = call.message.chat.id
    zikr_type = int(data["t"])
    page      = int(data.get("p", 0))
    owner     = (uid, cid)

    azkar = db.get_azkar_list(zikr_type)
    items, total_pages = paginate_list(azkar, page, per_page=5)

    label = TYPE_LABELS[zikr_type]
    text  = f"📿 <b>أذكار {label}</b> ({page+1}/{total_pages})\n{get_lines()}\n\n"
    buttons = []
    for z in items:
        preview = z["text"][:30] + ("…" if len(z["text"]) > 30 else "")
        text += f"• [{z['id']}] {preview} (×{z['repeat_count']})\n"
        buttons.append(btn(f"✏️ {z['id']}", "azkar_adm_item",
                           {"id": z["id"], "t": zikr_type, "p": page},
                           owner=owner))

    nav = []
    if page > 0:
        nav.append(btn("◀️", "azkar_adm_list", {"t": zikr_type, "p": page-1}, owner=owner))
    if page < total_pages - 1:
        nav.append(btn("▶️", "azkar_adm_list", {"t": zikr_type, "p": page+1}, owner=owner))
    nav.append(btn("🔙 رجوع", "azkar_adm_back", {}, owner=owner))

    layout = [1] * len(buttons) + ([len(nav)] if nav else [1])
    edit_ui(call, text=text, buttons=buttons + nav, layout=layout)


@register_action("azkar_adm_item")
def on_adm_item(call, data):
    uid       = call.from_user.id
    cid       = call.message.chat.id
    zikr_id   = int(data["id"])
    zikr_type = int(data["t"])
    page      = int(data.get("p", 0))
    owner     = (uid, cid)

    z = db.get_zikr(zikr_id)
    if not z:
        bot.answer_callback_query(call.id, "❌ الذكر غير موجود", show_alert=True)
        return

    text = (
        f"📿 <b>الذكر #{zikr_id}</b>\n{get_lines()}\n\n"
        f"{z['text']}\n\n"
        f"🔁 التكرار: {z['repeat_count']}"
    )
    buttons = [
        btn("✏️ تعديل النص",      "azkar_adm_edit",   {"id": zikr_id, "t": zikr_type, "p": page, "f": "text"},    owner=owner, color="p"),
        btn("🔢 تعديل التكرار",   "azkar_adm_edit",   {"id": zikr_id, "t": zikr_type, "p": page, "f": "repeat"},  owner=owner, color="p"),
        btn("🗑 حذف",             "azkar_adm_delete", {"id": zikr_id, "t": zikr_type, "p": page},                  owner=owner, color="d"),
        btn("🔙 رجوع",            "azkar_adm_list",   {"t": zikr_type, "p": page},                                 owner=owner),
    ]
    edit_ui(call, text=text, buttons=buttons, layout=[2, 1, 1])


@register_action("azkar_adm_delete")
def on_adm_delete(call, data):
    from core.admin import is_primary_dev
    if not is_primary_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطور الأساسي فقط", show_alert=True)
        return
    zikr_id   = int(data["id"])
    zikr_type = int(data["t"])
    page      = int(data.get("p", 0))
    db.delete_zikr(zikr_id)
    bot.answer_callback_query(call.id, "✅ تم الحذف", show_alert=True)
    on_adm_list(call, {"t": zikr_type, "p": page})


@register_action("azkar_adm_edit")
def on_adm_edit(call, data):
    from utils.pagination import set_state
    uid     = call.from_user.id
    cid     = call.message.chat.id
    field   = data.get("f", "text")   # "text" or "repeat"
    zikr_id = int(data["id"])
    prompt  = "أرسل النص الجديد للذكر:" if field == "text" else "أرسل عدد التكرار (رقم):"
    set_state(uid, cid, "azkar_awaiting_edit",
              data={"id": zikr_id, "f": field,
                    "t": data["t"], "p": data.get("p", 0),
                    "_mid": call.message.message_id})
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(f"✏️ {prompt}", cid, call.message.message_id,
                              parse_mode="HTML")
    except Exception:
        pass


@register_action("azkar_adm_add")
def on_adm_add(call, data):
    from utils.pagination import set_state
    uid       = call.from_user.id
    cid       = call.message.chat.id
    zikr_type = int(data["t"])
    set_state(uid, cid, "azkar_awaiting_add",
              data={"t": zikr_type, "_mid": call.message.message_id})
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(
            "➕ أرسل الذكر الجديد بالصيغة:\n<code>النص | عدد التكرار</code>\n\nمثال:\n<code>سبحان الله | 33</code>",
            cid, call.message.message_id, parse_mode="HTML"
        )
    except Exception:
        pass


@register_action("azkar_adm_back")
def on_adm_back(call, data):
    uid   = call.from_user.id
    cid   = call.message.chat.id
    owner = (uid, cid)
    _send_admin_panel(cid, uid, owner, call=call)


# ══════════════════════════════════════════
# معالج الإدخال النصي (حالات الانتظار)
# ══════════════════════════════════════════

def handle_azkar_input(message) -> bool:
    from utils.pagination import get_state, clear_state
    uid   = message.from_user.id
    cid   = message.chat.id
    state = get_state(uid, cid)
    if not state:
        return False

    s = state.get("state", "")
    if s not in ("azkar_awaiting_edit", "azkar_awaiting_add"):
        return False

    sdata = state.get("data", {})
    text  = (message.text or "").strip()
    mid   = sdata.get("_mid")
    clear_state(uid, cid)

    try:
        bot.delete_message(cid, message.message_id)
    except Exception:
        pass

    def _edit(msg):
        if mid:
            try:
                bot.edit_message_text(msg, cid, mid, parse_mode="HTML")
            except Exception:
                pass

    if s == "azkar_awaiting_edit":
        zikr_id   = int(sdata["id"])
        field     = sdata["f"]
        zikr_type = int(sdata["t"])
        page      = int(sdata.get("p", 0))
        z = db.get_zikr(zikr_id)
        if not z:
            _edit("❌ الذكر غير موجود.")
            return True
        if field == "text":
            db.update_zikr(zikr_id, text, z["repeat_count"])
            _edit(f"✅ تم تحديث نص الذكر #{zikr_id}")
        else:
            if not text.isdigit() or int(text) < 1:
                _edit("❌ أرسل رقماً صحيحاً أكبر من صفر.")
                return True
            db.update_zikr(zikr_id, z["text"], int(text))
            _edit(f"✅ تم تحديث تكرار الذكر #{zikr_id} إلى {text}")

    elif s == "azkar_awaiting_add":
        zikr_type = int(sdata["t"])
        if "|" not in text:
            _edit("❌ الصيغة غير صحيحة.\nاستخدم: <code>النص | عدد التكرار</code>")
            return True
        parts  = text.split("|", 1)
        ztext  = parts[0].strip()
        rcount = parts[1].strip()
        if not rcount.isdigit() or int(rcount) < 1:
            _edit("❌ عدد التكرار يجب أن يكون رقماً أكبر من صفر.")
            return True
        new_id = db.add_zikr(ztext, int(rcount), zikr_type)
        label  = TYPE_LABELS[zikr_type]
        _edit(f"✅ تمت إضافة الذكر #{new_id} لأذكار {label}")

    return True
