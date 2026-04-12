"""
لوحة تحكم ميزات المجموعة — الأوامر
يُستخدم بواسطة مشرفي المجموعة لتفعيل/تعطيل الوحدات.

الأمر: الأوامر
"""
from core.bot import bot
from utils.pagination import btn, send_ui, edit_ui, register_action
from utils.helpers import get_lines
from handlers.group_admin.permissions import is_admin
from database.db_queries.group_features_queries import (
    get_group_features, toggle_feature, FEATURES,
)

_B = "p"
_G = "su"
_R = "d"

# ── تسميات الميزات وأيقوناتها ──
_LABELS = {
    "enable_games":         ("🎮", "الألعاب",             "بنك، دول، حرب، تحالفات، ألعاب ترفيهية"),
    "enable_admin":         ("🛠", "أدوات الإدارة",       "كتم، حظر، تقييد، ترقية مشرفين"),
    "enable_replies":       ("💬", "الردود التلقائية",     "ردود البوت على الكلمات المحددة"),
    "enable_media":         ("🎨", "أوامر الوسائط",       "أوامر الستيكرات والوسائط التفاعلية"),
    "enable_welcome":       ("👋", "الترحيب",              "رسائل الترحيب للأعضاء الجدد"),
    "enable_leave_notify":  ("🚪", "إشعارات المغادرة",    "يُرسل إشعاراً عند مغادرة أو طرد عضو"),
    "enable_profile":       ("👤", "الملف الشخصي",        "عني/عنه — 0=يخفي الصورة فقط"),
    "enable_lock_stickers": ("🎭", "حذف الستيكرات",       "يحذف ستيكرات غير المشرفين تلقائياً"),
    "enable_lock_media":    ("🖼", "حذف الوسائط",         "يحذف صور/فيديو/ملفات غير المشرفين تلقائياً"),
    "quotes_enabled":       ("💬", "الاقتباسات التلقائية", "يرسل اقتباسات وحكم دورياً للمجموعة"),
    "azkar_enabled":        ("📿", "الأذكار التلقائية",    "يرسل أذكاراً دورياً للمجموعة"),
    "enable_whispers":      ("💌", "الهمسات",              "يتيح إرسال همسات خاصة بين الأعضاء"),
}


def handle_features_control(message) -> bool:
    """أمر: الأوامر — يفتح لوحة تحكم الميزات للمشرفين."""
    if (message.text or "").strip() not in ["الأوامر", "الاوامر"]:
        return False
    if message.chat.type not in ("group", "supergroup"):
        return False
    if not is_admin(message):
        bot.reply_to(message, "❌ هذا الأمر للمشرفين فقط.")
        return True

    uid = message.from_user.id
    cid = message.chat.id
    _send_panel(cid, uid, reply_to=message.message_id)
    return True


def _send_panel(cid, uid, reply_to=None, call=None):
    features = get_group_features(cid)
    owner    = (uid, cid)

    text = (
        f"⚙️ <b>إدارة ميزات المجموعة</b>\n{get_lines()}\n\n"
        f"📛 المجموعة: <b>{_get_group_name(cid)}</b>\n\n"
        "اضغط على أي ميزة لتفعيلها أو تعطيلها:\n"
        "✅ = مفعّل  |  ❌ = معطّل\n\n"
    )

    buttons = []
    for feat, (emoji, label, desc) in _LABELS.items():
        enabled = bool(features.get(feat, 1))
        status  = "✅" if enabled else "❌"
        text   += f"{status} {emoji} <b>{label}</b>\n<i>{desc}</i>\n\n"

        buttons.append(btn(
            f"{emoji} {label} {status}",
            "grp_feat_toggle",
            {"f": feat},
            color=_G if enabled else _R,
            owner=owner,
        ))

    # زر الإغلاق
    buttons.append(btn("❌ إغلاق", "grp_feat_close", {}, color=_R, owner=owner))

    # layout ديناميكي (2 في كل صف)
    count = len(_LABELS)
    layout = [2] * (count // 2)

    if count % 2:
        layout.append(1)

    layout.append(1)

    if call:
        edit_ui(call, text=text, buttons=buttons, layout=layout)
    else:
        send_ui(cid, text=text, buttons=buttons, layout=layout,
                owner_id=uid, reply_to=reply_to)
        
        
@register_action("grp_feat_toggle")
def on_toggle(call, data):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    feat = data.get("f")

    # تحقق من صلاحية المشرف
    try:
        member = bot.get_chat_member(cid, uid)
        if member.status not in ("administrator", "creator"):
            bot.answer_callback_query(call.id, "❌ للمشرفين فقط.", show_alert=True)
            return
    except Exception:
        bot.answer_callback_query(call.id, "❌ تعذّر التحقق من الصلاحية.", show_alert=True)
        return

    if feat not in FEATURES:
        bot.answer_callback_query(call.id, "❌ ميزة غير معروفة.", show_alert=True)
        return

    new_state = toggle_feature(cid, feat)
    emoji, label, _ = _LABELS[feat]
    status_ar = "مفعّلة ✅" if new_state else "معطّلة ❌"
    bot.answer_callback_query(call.id, f"{emoji} {label} — {status_ar}", show_alert=False)
    _send_panel(cid, uid, call=call)


@register_action("grp_feat_close")
def on_close(call, data):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


def _get_group_name(cid: int) -> str:
    try:
        return bot.get_chat(cid).title or str(cid)
    except Exception:
        return str(cid)
