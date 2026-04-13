"""
Permission definitions — admin/moderation only.
All permissions use promoteChatMember.
"""
from core.bot import bot

# ── Admin permissions (promoteChatMember only) ────────────────────────────────

ADMIN_PERMS = [
    ("can_change_info",        "تغيير معلومات المجموعة"),
    ("can_invite_users",       "دعوة المستخدمين"),
    ("can_pin_messages",       "تثبيت الرسائل"),
    ("can_manage_topics",      "إدارة المواضيع"),
    ("can_delete_messages",    "حذف الرسائل"),
    ("can_restrict_members",   "تقييد الأعضاء"),
    ("can_promote_members",    "ترقية الأعضاء"),
    ("can_manage_chat",        "إدارة المحادثة"),
    ("can_manage_video_chats", "إدارة المكالمات"),
    ("can_post_stories",       "نشر القصص"),
    ("can_edit_stories",       "تعديل القصص"),
    ("can_delete_stories",     "حذف القصص"),
    ("can_manage_tags",        "تعديل الوسوم"),
    ("is_anonymous",           "إخفاء الهوية"),
]

PROMOTE_KEYS = {k for k, _ in ADMIN_PERMS}

# ── Single preset ─────────────────────────────────────────────────────────────

PRESETS = {
    "full": {
        "label": "👑 كامل الصلاحيات",
        "promote": {
            k: (False if k == "is_anonymous" else True)
            for k, _ in ADMIN_PERMS
        },
    },
}

# ── Bot capability helpers ────────────────────────────────────────────────────

def get_bot_member(cid: int):
    try:
        return bot.get_chat_member(cid, bot.get_me().id)
    except Exception:
        return None


def bot_can_promote(cid: int) -> bool:
    m = get_bot_member(cid)
    if not m:
        return False
    if m.status == "creator":
        return True
    return bool(m.status == "administrator" and getattr(m, "can_promote_members", False))


def bot_can_manage_tags(cid: int) -> bool:
    m = get_bot_member(cid)
    if not m:
        return False
    if m.status == "creator":
        return True
    return bool(m.status == "administrator" and getattr(m, "can_manage_tags", False))


def get_bot_available_promote_perms(cid: int) -> set:
    """Returns admin perms the bot actually holds (can only grant what it has)."""
    m = get_bot_member(cid)
    if not m:
        return set()
    if m.status == "creator":
        return set(PROMOTE_KEYS)
    if m.status != "administrator":
        return set()
    return {k for k in PROMOTE_KEYS if bool(getattr(m, k, False))}


def friendly_error(e: Exception) -> str:
    err = str(e).lower()
    if "chat_admin_required" in err or "not enough rights" in err:
        return "❌ البوت لا يملك الصلاحيات الكافية لتنفيذ هذا الإجراء."
    if "user_not_participant" in err:
        return "❌ المستخدم غير موجود في المجموعة."
    if "creator" in err:
        return "❌ لا يمكن تعديل صلاحيات مؤسس المجموعة."
    if "bot was kicked" in err:
        return "❌ البوت مطرود من المجموعة."
    return "❌ البوت لا يملك الصلاحيات الكافية لتنفيذ هذا الإجراء."
