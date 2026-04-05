"""
معالج مركز المحتوى — اقتباسات، نوادر، قصص، حكم
"""
from core.bot import bot
from core.admin import is_any_dev

from utils.helpers import get_bot_link
from utils.pagination import btn, send_ui, edit_ui, register_action, set_state, get_state, clear_state

from modules.content_hub.hub_db import (
    CONTENT_TYPES, TYPE_LABELS, CONTENT_SEPARATOR,
    get_random, get_by_id, insert_content, update_content,
    delete_content, count_rows, create_tables,
)
from utils.helpers import get_lines

# ── تهيئة الجداول عند الاستيراد ──
create_tables()

_B = "p"
_G = "su"
_R = "d"



# ══════════════════════════════════════════
# نقطة الدخول — أوامر المستخدم
# ══════════════════════════════════════════

def handle_content_command(message) -> bool:
    """
    يعالج: اقتباس / نوادر / قصص / حكمة [id؟]
    يرجع True إذا تم التعامل مع الأمر.
    """
    text  = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    cmd   = parts[0]

    if cmd not in CONTENT_TYPES:
        return False

    table = CONTENT_TYPES[cmd]
    uid   = message.from_user.id
    cid   = message.chat.id

    # اقتباس [id] — جلب بمعرف محدد
    if len(parts) == 2 and parts[1].isdigit():
        row_id = int(parts[1])
        row    = get_by_id(table, row_id)
        if not row:
            bot.reply_to(message, f"❌ لا يوجد محتوى بالرقم {row_id}.")
            return True
        _send_content(message, uid, cid, table, row)
        return True

    # جلب عشوائي
    row = get_random(table)
    if not row:
        bot.reply_to(message, f"❌ لا يوجد محتوى في {TYPE_LABELS.get(table, table)} بعد.")
        return True

    _send_content(message, uid, cid, table, row)
    return True


def _build_buttons(uid: int, cid: int, table: str, row: dict) -> tuple[list, list]:
    """يبني قائمة الأزرار والتخطيط لعرض المحتوى."""
    owner   = (uid, cid)
    row_id  = row["id"]
    buttons = [
        btn("🔄 تغيير",   "hub_refresh", {"table": table},                    color=_B, owner=owner),
        btn("📤 مشاركة",  "hub_share",   {"table": table, "row_id": row_id},  color=_G, owner=owner),
        btn("❌ إلغاء",   "hub_close",   {},                                   color=_R, owner=owner),
    ]
    if is_any_dev(uid):
        buttons.insert(2, btn("✏️ تعديل", "hub_edit_prompt",
                               {"table": table, "row_id": row_id},
                               color=_B, owner=owner))
        buttons.insert(3, btn("🗑️ حذف",  "hub_delete",
                               {"table": table, "row_id": row_id},
                               color=_R, owner=owner))

    # تخطيط: صفان من 2 أو 3 حسب العدد
    n      = len(buttons)
    layout = [2, n - 2] if n > 2 else [n]
    return buttons, layout


def _send_content(message, uid: int, cid: int, table: str, row: dict):
    label   = TYPE_LABELS.get(table, table)
    total   = count_rows(table)
    text    = (
        f"{label}\n"
        f"{get_lines()}\n\n"
        f"{row['content']}\n\n"
        f"<i>#{row['id']} من {total}</i>"
    )
    buttons, layout = _build_buttons(uid, cid, table, row)
    send_ui(cid, text=text, buttons=buttons, layout=layout,
            owner_id=uid, reply_to=message.message_id)


# ══════════════════════════════════════════
# أزرار المحتوى
# ══════════════════════════════════════════

@register_action("hub_refresh")
def on_refresh(call, data):
    table = data.get("table")
    uid   = call.from_user.id
    cid   = call.message.chat.id

    row = get_random(table)
    if not row:
        bot.answer_callback_query(call.id, "❌ لا يوجد محتوى.", show_alert=True)
        return

    label   = TYPE_LABELS.get(table, table)
    total   = count_rows(table)
    text    = (
        f"{label}\n"
        f"{get_lines()}\n\n"
        f"{row['content']}\n\n"
        f"<i>#{row['id']} من {total}</i>"
    )
    buttons, layout = _build_buttons(uid, cid, table, row)
    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons, layout=layout)


@register_action("hub_close")
def on_close(call, data):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


@register_action("hub_share")
def on_share(call, data):
    """يرسل المحتوى بصيغة مشاركة — رسالة جديدة منفصلة."""
    table  = data.get("table")
    row_id = data.get("row_id")
    cid    = call.message.chat.id

    row = get_by_id(table, row_id)
    if not row:
        bot.answer_callback_query(call.id, "❌ المحتوى غير موجود.", show_alert=True)
        return

    label    = TYPE_LABELS.get(table, table)

    share_text = (
        f"{get_lines()}\n"
        f"📜 {label} #{row['id']}\n\n"
        f"{row['content']}\n\n"
        f"{get_lines()}\n"
        f"🤖 via {get_bot_link()}"
    )

    bot.answer_callback_query(call.id)
    try:
        bot.send_message(cid, share_text, parse_mode="HTML")
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خطأ: {e}", show_alert=True)


@register_action("hub_delete")
def on_delete(call, data):
    uid = call.from_user.id
    if not is_any_dev(uid):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط.", show_alert=True)
        return

    table  = data.get("table")
    row_id = data.get("row_id")
    ok     = delete_content(table, row_id)
    bot.answer_callback_query(call.id, "✅ تم الحذف." if ok else "❌ لم يتم العثور على المحتوى.",
                              show_alert=True)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


@register_action("hub_edit_prompt")
def on_edit_prompt(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    if not is_any_dev(uid):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط.", show_alert=True)
        return

    table  = data.get("table")
    row_id = data.get("row_id")
    owner  = (uid, cid)

    # حفظ الحالة مع معرف الرسالة الأصلية
    set_state(uid, cid, "hub_awaiting_edit", data={
        "table":  table,
        "row_id": row_id,
        "_mid":   call.message.message_id,
    })
    bot.answer_callback_query(call.id)

    cancel_btn = btn("🚫 إلغاء", "hub_cancel_edit", {}, color=_R, owner=owner)
    try:
        from utils.pagination.buttons import build_keyboard
        bot.edit_message_text(
            f"✏️ <b>تعديل المحتوى #{row_id}</b>\n\n"
            f"أرسل النص الجديد أو اضغط إلغاء:",
            cid, call.message.message_id,
            parse_mode="HTML",
            reply_markup=build_keyboard([cancel_btn], [1], uid),
        )
    except Exception:
        pass


@register_action("hub_cancel_edit")
def on_cancel_edit(call, data):
    uid = call.from_user.id
    cid = call.message.chat.id
    clear_state(uid, cid)
    bot.answer_callback_query(call.id, "تم الإلغاء")
    # أعد عرض المحتوى
    try:
        bot.delete_message(cid, call.message.message_id)
    except Exception:
        pass


# ══════════════════════════════════════════
# معالج الإدخال النصي (تعديل + إضافة)
# ══════════════════════════════════════════

def handle_hub_input(message) -> bool:
    """
    يعالج حالات الانتظار لمركز المحتوى.
    يرجع True إذا تم التعامل مع الرسالة.
    """
    uid = message.from_user.id
    cid = message.chat.id

    state = get_state(uid, cid)
    if not state or "state" not in state:
        return False

    s     = state["state"]
    sdata = state.get("data", {})

    if not s.startswith("hub_"):
        return False

    # ── تعديل محتوى ──
    if s == "hub_awaiting_edit":
        if not is_any_dev(uid):
            clear_state(uid, cid)
            return False

        table    = sdata.get("table")
        row_id   = sdata.get("row_id")
        mid      = sdata.get("_mid")
        new_text = (message.text or "").strip()
        clear_state(uid, cid)

        try:
            bot.delete_message(cid, message.message_id)
        except Exception:
            pass

        if not new_text:
            _send_error(cid, mid, uid, "❌ النص لا يمكن أن يكون فارغاً.")
            return True

        ok = update_content(table, row_id, new_text)
        if ok and mid:
            label = TYPE_LABELS.get(table, table)
            total = count_rows(table)
            text  = (
                f"{label}\n"
                f"{get_lines()}\n\n"
                f"{new_text}\n\n"
                f"<i>#{row_id} من {total}</i>"
            )
            row_updated = {"id": row_id, "content": new_text}
            buttons, layout = _build_buttons(uid, cid, table, row_updated)
            try:
                from utils.pagination.buttons import build_keyboard
                bot.edit_message_text(
                    text, cid, mid,
                    parse_mode="HTML",
                    reply_markup=build_keyboard(buttons, layout, uid),
                )
            except Exception:
                pass
        elif not ok:
            _send_error(cid, mid, uid, "❌ فشل التعديل.")
        return True

    # ── إضافة محتوى ──
    if s == "hub_awaiting_add":
        if not is_any_dev(uid):
            clear_state(uid, cid)
            return False

        table = sdata.get("table")
        raw   = (message.text or "").strip()
        mid   = sdata.get("_mid")
        clear_state(uid, cid)

        try:
            bot.delete_message(cid, message.message_id)
        except Exception:
            pass

        if not raw:
            _send_error(cid, mid, uid, "❌ النص لا يمكن أن يكون فارغاً.")
            return True

        items = [i.strip() for i in raw.split(CONTENT_SEPARATOR) if i.strip()]
        added = 0
        for item in items:
            insert_content(table, item)
            added += 1

        label   = TYPE_LABELS.get(table, table)
        success = (
            f"✅ تمت إضافة <b>{added}</b> عنصر إلى {label}.\n"
            f"الفاصل المستخدم: <code>{CONTENT_SEPARATOR}</code>"
        )
        _send_success(cid, mid, uid, success)
        return True

    return False


def _send_error(cid: int, mid, uid: int, text: str):
    """يعرض رسالة خطأ مع زر إغلاق."""
    from utils.pagination.buttons import build_keyboard
    owner  = (uid, cid)
    markup = build_keyboard([btn("❌ إغلاق", "hub_close", {}, color=_R, owner=owner)], [1], uid)
    if mid:
        try:
            bot.edit_message_text(text, cid, mid, parse_mode="HTML", reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(cid, text, parse_mode="HTML", reply_markup=markup)


def _send_success(cid: int, mid, uid: int, text: str):
    """يعرض رسالة نجاح مع أزرار رجوع وإغلاق — يستبدل الكيبورد القديم."""
    from utils.pagination.buttons import build_keyboard
    owner   = (uid, cid)
    buttons = [
        btn("🔙 رجوع", "hub_cancel_edit", {}, color=_B, owner=owner),
        btn("❌ إغلاق", "hub_close",       {}, color=_R, owner=owner),
    ]
    markup = build_keyboard(buttons, [2], uid)
    if mid:
        try:
            bot.edit_message_text(text, cid, mid, parse_mode="HTML", reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(cid, text, parse_mode="HTML", reply_markup=markup)


# ══════════════════════════════════════════
# أوامر الإضافة (للمطورين)
# ══════════════════════════════════════════

def handle_add_content_command(message) -> bool:
    """
    يعالج: اضف اقتباس / اضف نوادر / اضف قصص / اضف حكم
    """
    text  = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    if parts[0] != "اضف" or len(parts) < 2:
        return False

    cmd_map = {
        "اقتباس": "quotes",
        "نوادر":  "anecdotes",
        "قصص":   "stories",
        "حكم":   "wisdom",
        "حكمة":  "wisdom",
    }
    table = cmd_map.get(parts[1].strip())
    if not table:
        return False

    uid = message.from_user.id
    cid = message.chat.id

    if not is_any_dev(uid):
        bot.reply_to(message, "❌ هذا الأمر للمطورين فقط.")
        return True

    label = TYPE_LABELS.get(table, table)
    set_state(uid, cid, "hub_awaiting_add", data={"table": table})

    owner      = (uid, cid)
    cancel_btn = btn("🚫 إلغاء", "hub_cancel_edit", {}, color=_R, owner=owner)

    from utils.pagination.buttons import build_keyboard
    bot.reply_to(
        message,
        f"✍️ <b>إضافة محتوى إلى {label}</b>\n\n"
        f"أرسل المحتوى.\n"
        f"لإضافة عدة عناصر دفعة واحدة، افصل بينها بـ:\n"
        f"<code>{CONTENT_SEPARATOR}</code>",
        parse_mode="HTML",
        reply_markup=build_keyboard([cancel_btn], [1], uid),
    )
    return True