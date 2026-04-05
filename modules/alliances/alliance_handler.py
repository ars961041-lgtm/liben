"""
معالج التحالفات — واجهة المستخدم الكاملة
"""
from core.bot import bot
from utils.pagination import btn, send_ui, edit_ui, register_action, paginate_list, grid
from database.db_queries.countries_queries import get_country_by_owner
from database.db_queries.alliances_queries import (
    get_alliance_by_user, get_alliance_by_id, get_all_active_alliances,
    get_top_alliances, get_alliance_power, get_alliance_upgrades,
    get_all_upgrade_types, purchase_alliance_upgrade,
    send_alliance_invite, get_user_pending_invites,
    accept_invite, reject_invite, leave_alliance,
    kick_member, transfer_leadership, get_alliance_member_count,
    get_invite_by_id,
)
from database.db_queries.bank_queries import get_user_balance
from utils.helpers import get_lines


# ══════════════════════════════════════════
# 🏠 القائمة الرئيسية
# ══════════════════════════════════════════

def open_alliance_menu(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    alliance = get_alliance_by_user(user_id)

    if not alliance:
        _show_no_alliance_menu(message, user_id, chat_id)
        return

    alliance = dict(alliance)
    _show_alliance_main(message.chat.id, user_id, chat_id, alliance)


def _show_no_alliance_menu(message, user_id, chat_id):
    buttons = [
        btn("📋 قائمة التحالفات", "alliance_list", data={"page": 0},
            owner=(user_id, chat_id), color="p"),
        btn("📩 دعواتي", "alliance_my_invites", data={},
            owner=(user_id, chat_id), color="su"),
        btn("🏆 أقوى التحالفات", "alliance_leaderboard", data={"page": 0},
            owner=(user_id, chat_id), color="p"),
    ]
    send_ui(chat_id,
            text="🏰 <b>نظام التحالفات</b>\n\nلست في أي تحالف حالياً.\nأنشئ تحالفاً: <code>إنشاء تحالف [الاسم]</code>",
            buttons=buttons, layout=[2, 1], owner_id=user_id,
            reply_to=message.message_id)


def _show_alliance_main(chat_id, user_id, owner_chat_id, alliance, edit_call=None):
    power = get_alliance_power(alliance["id"])
    member_count = get_alliance_member_count(alliance["id"])
    is_leader = alliance["leader_id"] == user_id

    text = (
        f"🏰 <b>تحالف: {alliance['name']}</b>\n"
        f"{get_lines()}\n"
        f"💪 القوة: {power:.0f}\n"
        f"👥 الأعضاء: {member_count}/{alliance.get('max_countries', 10)}\n\n"
        f"اختر ما تريد:"
    )

    buttons = [
        btn("👥 الأعضاء", "alliance_members", data={"aid": alliance["id"], "page": 0},
            owner=(user_id, owner_chat_id), color="p"),
        btn("⬆️ الترقيات", "alliance_upgrades_view", data={"aid": alliance["id"]},
            owner=(user_id, owner_chat_id), color="p"),
        btn("🏆 لوحة الصدارة", "alliance_leaderboard", data={"page": 0},
            owner=(user_id, owner_chat_id), color="p"),
        btn("📩 دعواتي", "alliance_my_invites", data={},
            owner=(user_id, owner_chat_id), color="su"),
        btn("🚪 الانسحاب", "alliance_leave_confirm", data={},
            owner=(user_id, owner_chat_id), color="d"),
    ]

    if is_leader:
        buttons.insert(2, btn("➕ دعوة عضو", "alliance_invite_menu",
                               data={"aid": alliance["id"], "page": 0},
                               owner=(user_id, owner_chat_id), color="su"))
        buttons.append(btn("🛒 شراء ترقية", "alliance_buy_upgrade",
                            data={"aid": alliance["id"], "page": 0},
                            owner=(user_id, owner_chat_id), color="su"))

    layout = [2, 2, 2] if is_leader else [2, 2, 1]

    if edit_call:
        edit_ui(edit_call, text=text, buttons=buttons, layout=layout)
    else:
        send_ui(chat_id, text=text, buttons=buttons, layout=layout, owner_id=user_id)


# ══════════════════════════════════════════
# 📋 قائمة التحالفات
# ══════════════════════════════════════════

@register_action("alliance_list")
def show_alliance_list(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    page = int(data.get("page", 0))

    alliances = get_all_active_alliances()
    if not alliances:
        edit_ui(call, text="📋 لا توجد تحالفات حالياً.", buttons=[], layout=[1])
        return

    items, total_pages = paginate_list(alliances, page, per_page=5)
    text = f"📋 <b>التحالفات</b> (صفحة {page+1}/{total_pages})\n\n"
    for a in items:
        text += f"🏰 <b>{a['name']}</b> — قوة: {a['power']:.0f}\n"

    nav = []
    if page > 0:
        nav.append(btn("◀️", "alliance_list", data={"page": page-1}, owner=(user_id, chat_id)))
    if page < total_pages - 1:
        nav.append(btn("▶️", "alliance_list", data={"page": page+1}, owner=(user_id, chat_id)))

    buttons = nav
    layout = [len(nav)] if nav else [1]
    edit_ui(call, text=text, buttons=buttons, layout=layout)


# ══════════════════════════════════════════
# 🏆 لوحة الصدارة
# ══════════════════════════════════════════

@register_action("alliance_leaderboard")
def show_leaderboard(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    page = int(data.get("page", 0))

    top = get_top_alliances(limit=20)
    if not top:
        edit_ui(call, text="🏆 لا توجد تحالفات بعد.", buttons=[], layout=[1])
        return

    items, total_pages = paginate_list(top, page, per_page=5)
    text = f"🏆 <b>أقوى التحالفات</b> (صفحة {page+1}/{total_pages})\n\n"
    for i, a in enumerate(items, start=page*5+1):
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
        text += f"{medal} <b>{a['name']}</b>\n   💪 {a['power']:.0f} | 👥 {a['member_count']}\n\n"

    nav = []
    if page > 0:
        nav.append(btn("◀️", "alliance_leaderboard", data={"page": page-1}, owner=(user_id, chat_id)))
    if page < total_pages - 1:
        nav.append(btn("▶️", "alliance_leaderboard", data={"page": page+1}, owner=(user_id, chat_id)))

    back = [btn("🔙 رجوع", "alliance_back_main", data={}, owner=(user_id, chat_id))]
    buttons = nav + back
    layout = ([len(nav)] if nav else []) + [1]
    edit_ui(call, text=text, buttons=buttons, layout=layout)


# ══════════════════════════════════════════
# 👥 الأعضاء
# ══════════════════════════════════════════

@register_action("alliance_members")
def show_members(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    alliance_id = int(data["aid"])
    page = int(data.get("page", 0))

    alliance = get_alliance_by_id(alliance_id)
    if not alliance:
        bot.answer_callback_query(call.id, "❌ التحالف غير موجود")
        return

    members = alliance["members"]
    items, total_pages = paginate_list(members, page, per_page=5)

    text = f"👥 <b>أعضاء {alliance['name']}</b> ({len(members)} عضو)\n\n"
    for m in items:
        role_ar = {"leader": "👑 قائد", "officer": "⭐ ضابط", "member": "🪖 عضو"}.get(m["role"], m["role"])
        text += f"{role_ar} — ID: {m['user_id']}\n"

    is_leader = alliance["leader_id"] == user_id
    nav = []
    if page > 0:
        nav.append(btn("◀️", "alliance_members", data={"aid": alliance_id, "page": page-1}, owner=(user_id, chat_id)))
    if page < total_pages - 1:
        nav.append(btn("▶️", "alliance_members", data={"aid": alliance_id, "page": page+1}, owner=(user_id, chat_id)))

    buttons = nav + [btn("🔙 رجوع", "alliance_back_main", data={}, owner=(user_id, chat_id))]
    layout = ([len(nav)] if nav else []) + [1]
    edit_ui(call, text=text, buttons=buttons, layout=layout)


# ══════════════════════════════════════════
# ➕ دعوة عضو
# ══════════════════════════════════════════

@register_action("alliance_invite_menu")
def show_invite_menu(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    alliance_id = int(data["aid"])
    page = int(data.get("page", 0))

    # جلب كل الدول غير الأعضاء
    from database.db_queries.countries_queries import get_all_countries
    alliance = get_alliance_by_id(alliance_id)
    if not alliance:
        bot.answer_callback_query(call.id, "❌ التحالف غير موجود")
        return

    member_user_ids = {m["user_id"] for m in alliance["members"]}
    all_countries = [dict(c) for c in get_all_countries() if c["owner_id"] not in member_user_ids]

    if not all_countries:
        edit_ui(call, text="❌ لا توجد دول يمكن دعوتها.",
                buttons=[btn("🔙 رجوع", "alliance_back_main", data={}, owner=(user_id, chat_id))],
                layout=[1])
        return

    items, total_pages = paginate_list(all_countries, page, per_page=6)
    buttons = [
        btn(f"🏳️ {c['name']}", "alliance_send_invite",
            data={"aid": alliance_id, "to_uid": c["owner_id"], "cname": c["name"]},
            owner=(user_id, chat_id), color="su")
        for c in items
    ]

    nav = []
    if page > 0:
        nav.append(btn("◀️", "alliance_invite_menu", data={"aid": alliance_id, "page": page-1}, owner=(user_id, chat_id)))
    if page < total_pages - 1:
        nav.append(btn("▶️", "alliance_invite_menu", data={"aid": alliance_id, "page": page+1}, owner=(user_id, chat_id)))
    nav.append(btn("🔙 رجوع", "alliance_back_main", data={}, owner=(user_id, chat_id)))

    layout = grid(len(items), 2) + [len(nav)]
    edit_ui(call, text=f"➕ اختر دولة لدعوتها (صفحة {page+1}/{total_pages}):",
            buttons=buttons + nav, layout=layout)


@register_action("alliance_send_invite")
def send_invite(call, data):
    user_id = call.from_user.id
    alliance_id = int(data["aid"])
    to_uid = int(data["to_uid"])
    cname = data.get("cname", "")

    ok, result = send_alliance_invite(alliance_id, user_id, to_uid)
    if not ok:
        bot.answer_callback_query(call.id, result, show_alert=True)
        return

    # إشعار المدعو
    try:
        alliance = get_alliance_by_id(alliance_id)
        from utils.pagination import send_ui as _send_ui
        _send_ui(to_uid,
                 text=f"📩 <b>دعوة تحالف!</b>\nتم دعوتك للانضمام لتحالف <b>{alliance['name']}</b>.\nاستخدم: دعوات التحالف",
                 buttons=[], layout=[1], owner_id=to_uid)
    except Exception:
        pass

    bot.answer_callback_query(call.id, f"✅ تم إرسال الدعوة لـ {cname}", show_alert=True)


# ══════════════════════════════════════════
# 📩 دعواتي
# ══════════════════════════════════════════

@register_action("alliance_my_invites")
def show_my_invites(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    invites = get_user_pending_invites(user_id)
    if not invites:
        edit_ui(call, text="📭 لا توجد دعوات معلقة.",
                buttons=[btn("🔙 رجوع", "alliance_back_main", data={}, owner=(user_id, chat_id))],
                layout=[1])
        return

    text = "📩 <b>دعوات التحالف المعلقة:</b>\n\n"
    buttons = []
    for inv in invites[:5]:
        text += f"🏰 <b>{inv['name']}</b>\n"
        buttons.append(btn(f"✅ قبول — {inv['name']}", "alliance_accept_invite",
                           data={"invite_id": inv["id"]}, owner=(user_id, chat_id), color="su"))
        buttons.append(btn(f"❌ رفض", "alliance_reject_invite",
                           data={"invite_id": inv["id"]}, owner=(user_id, chat_id), color="d"))

    buttons.append(btn("🔙 رجوع", "alliance_back_main", data={}, owner=(user_id, chat_id)))
    layout = [2] * len(invites[:5]) + [1]
    edit_ui(call, text=text, buttons=buttons, layout=layout)


@register_action("alliance_accept_invite")
def on_accept_invite(call, data):
    user_id = call.from_user.id
    invite_id = int(data["invite_id"])

    # التحقق من عدم وجود تحالف
    if get_alliance_by_user(user_id):
        bot.answer_callback_query(call.id, "❌ أنت بالفعل في تحالف.", show_alert=True)
        return

    ok, msg = accept_invite(invite_id)
    bot.answer_callback_query(call.id, msg, show_alert=True)
    if ok:
        try:
            alliance = get_alliance_by_user(user_id)
            if alliance:
                alliance = dict(alliance)
                _show_alliance_main(call.message.chat.id, user_id, call.message.chat.id, alliance, edit_call=call)
        except Exception:
            pass


@register_action("alliance_reject_invite")
def on_reject_invite(call, data):
    invite_id = int(data["invite_id"])
    reject_invite(invite_id)
    bot.answer_callback_query(call.id, "❌ تم رفض الدعوة.", show_alert=False)
    try:
        bot.edit_message_text("❌ رفضت الدعوة.", call.message.chat.id, call.message.message_id)
    except Exception:
        pass


# ══════════════════════════════════════════
# 🚪 الانسحاب
# ══════════════════════════════════════════

@register_action("alliance_leave_confirm")
def leave_confirm(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    edit_ui(call,
            text="⚠️ <b>تأكيد الانسحاب</b>\n\nسيتم خصم نقاط من سمعتك.\nهل أنت متأكد؟",
            buttons=[
                btn("✅ نعم، انسحب", "alliance_leave_do", data={}, owner=(user_id, chat_id), color="d"),
                btn("🔙 إلغاء", "alliance_back_main", data={}, owner=(user_id, chat_id)),
            ], layout=[2])


@register_action("alliance_leave_do")
def do_leave(call, data):
    user_id = call.from_user.id
    ok, msg = leave_alliance(user_id, penalty=True)
    bot.answer_callback_query(call.id, msg, show_alert=True)
    try:
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id)
    except Exception:
        pass


# ══════════════════════════════════════════
# ⬆️ عرض الترقيات
# ══════════════════════════════════════════

@register_action("alliance_upgrades_view")
def show_upgrades(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    alliance_id = int(data["aid"])

    upgrades = get_alliance_upgrades(alliance_id)
    all_types = get_all_upgrade_types()

    owned = {u["name"]: u["level"] for u in upgrades}

    text = "⬆️ <b>ترقيات التحالف</b>\n\n"
    for t in all_types:
        lvl = owned.get(t["name"], 0)
        text += f"{t['emoji']} <b>{t['name_ar']}</b> — مستوى {lvl}/{t['max_level']}\n   {t['description_ar']}\n\n"

    buttons = [btn("🔙 رجوع", "alliance_back_main", data={}, owner=(user_id, chat_id))]
    edit_ui(call, text=text, buttons=buttons, layout=[1])


@register_action("alliance_buy_upgrade")
def show_buy_upgrade(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    alliance_id = int(data["aid"])
    page = int(data.get("page", 0))

    all_types = get_all_upgrade_types()
    upgrades = get_alliance_upgrades(alliance_id)
    owned = {u["name"]: u["level"] for u in upgrades}
    balance = get_user_balance(user_id)

    items, total_pages = paginate_list(all_types, page, per_page=4)
    text = f"🛒 <b>شراء ترقية</b>\n💰 رصيدك: {balance:.0f} Liben\n\n"
    buttons = []
    for t in items:
        lvl = owned.get(t["name"], 0)
        cost = t["price"] * (lvl + 1)
        if lvl < t["max_level"]:
            text += f"{t['emoji']} <b>{t['name_ar']}</b> مستوى {lvl}→{lvl+1} | {cost:.0f} Liben\n"
            buttons.append(btn(f"{t['emoji']} شراء {t['name_ar']}", "alliance_do_buy_upgrade",
                               data={"aid": alliance_id, "upg_id": t["id"]},
                               owner=(user_id, chat_id), color="su"))
        else:
            text += f"{t['emoji']} <b>{t['name_ar']}</b> ✅ مكتمل\n"

    nav = []
    if page > 0:
        nav.append(btn("◀️", "alliance_buy_upgrade", data={"aid": alliance_id, "page": page-1}, owner=(user_id, chat_id)))
    if page < total_pages - 1:
        nav.append(btn("▶️", "alliance_buy_upgrade", data={"aid": alliance_id, "page": page+1}, owner=(user_id, chat_id)))
    nav.append(btn("🔙 رجوع", "alliance_back_main", data={}, owner=(user_id, chat_id)))

    layout = [1] * len(buttons) + ([len(nav)-1] if len(nav) > 1 else []) + [1]
    edit_ui(call, text=text, buttons=buttons + nav, layout=layout)


@register_action("alliance_do_buy_upgrade")
def do_buy_upgrade(call, data):
    user_id = call.from_user.id
    alliance_id = int(data["aid"])
    upg_id = int(data["upg_id"])

    ok, msg = purchase_alliance_upgrade(alliance_id, upg_id, user_id)
    bot.answer_callback_query(call.id, msg, show_alert=True)


# ══════════════════════════════════════════
# 🔙 رجوع للرئيسية
# ══════════════════════════════════════════

@register_action("alliance_back_main")
def back_to_main(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    alliance = get_alliance_by_user(user_id)
    if not alliance:
        edit_ui(call,
                text="🏰 <b>نظام التحالفات</b>\n\nلست في أي تحالف.\nأنشئ تحالفاً: <code>إنشاء تحالف [الاسم]</code>",
                buttons=[
                    btn("📋 قائمة التحالفات", "alliance_list", data={"page": 0}, owner=(user_id, chat_id)),
                    btn("📩 دعواتي", "alliance_my_invites", data={}, owner=(user_id, chat_id), color="su"),
                ], layout=[2])
        return
    _show_alliance_main(chat_id, user_id, chat_id, dict(alliance), edit_call=call)


# ══════════════════════════════════════════
# 💥 حل التحالف (تصويت)
# ══════════════════════════════════════════

@register_action("alliance_dissolve_start")
def dissolve_start(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    alliance = get_alliance_by_user(user_id)
    if not alliance:
        bot.answer_callback_query(call.id, "❌ لست في تحالف!")
        return
    alliance = dict(alliance)
    if alliance["leader_id"] != user_id:
        bot.answer_callback_query(call.id, "❌ فقط القائد يمكنه بدء التصويت على الحل!")
        return

    edit_ui(call,
            text=(f"💥 <b>حل تحالف {alliance['name']}</b>\n\n"
                  f"سيتم إرسال تصويت لجميع الأعضاء.\n"
                  f"إذا وافق الجميع → يُحذف التحالف\n"
                  f"إذا رفض أي عضو → تنتقل القيادة للأقوى\n\n"
                  f"هل تريد المتابعة؟"),
            buttons=[
                btn("✅ ابدأ التصويت", "alliance_dissolve_vote_send",
                    data={"aid": alliance["id"]}, owner=(user_id, chat_id), color="d"),
                btn("🔙 إلغاء", "alliance_back_main", data={}, owner=(user_id, chat_id)),
            ], layout=[2])


@register_action("alliance_dissolve_vote_send")
def dissolve_send_votes(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    alliance_id = int(data["aid"])

    alliance = get_alliance_by_id(alliance_id)
    if not alliance:
        bot.answer_callback_query(call.id, "❌ التحالف غير موجود")
        return

    from database.db_queries.advanced_war_queries import cast_dissolve_vote, clear_dissolve_votes
    clear_dissolve_votes(alliance_id)
    # القائد يصوت تلقائياً بالموافقة
    cast_dissolve_vote(alliance_id, user_id, "accept")

    sent = 0
    for member in alliance["members"]:
        member_uid = member["user_id"] if isinstance(member, dict) else member[0]
        if member_uid == user_id:
            continue
        try:
            send_ui(member_uid,
                    text=(f"🗳️ <b>تصويت: حل تحالف {alliance['name']}</b>\n\n"
                          f"القائد يطلب حل التحالف.\nهل توافق؟"),
                    buttons=[
                        btn("✅ أوافق", "alliance_dissolve_cast",
                            data={"aid": alliance_id, "vote": "accept"},
                            owner=(member_uid, None), color="su"),
                        btn("❌ أرفض", "alliance_dissolve_cast",
                            data={"aid": alliance_id, "vote": "reject"},
                            owner=(member_uid, None), color="d"),
                    ], layout=[2], owner_id=member_uid)
            sent += 1
        except Exception:
            pass

    bot.answer_callback_query(call.id, f"✅ تم إرسال التصويت لـ {sent} عضو", show_alert=True)
    try:
        bot.edit_message_text(f"🗳️ تم إرسال التصويت لـ {sent} عضو. انتظر ردودهم.",
                              call.message.chat.id, call.message.message_id)
    except Exception:
        pass


@register_action("alliance_dissolve_cast")
def dissolve_cast(call, data):
    user_id = call.from_user.id
    alliance_id = int(data["aid"])
    vote = data["vote"]

    from database.db_queries.advanced_war_queries import (
        cast_dissolve_vote, get_dissolve_votes, clear_dissolve_votes
    )
    cast_dissolve_vote(alliance_id, user_id, vote)

    alliance = get_alliance_by_id(alliance_id)
    if not alliance:
        bot.answer_callback_query(call.id, "❌ التحالف غير موجود")
        return

    total_members = len(alliance["members"])
    votes = get_dissolve_votes(alliance_id)
    total_voted = votes["accept"] + votes["reject"]

    bot.answer_callback_query(call.id, f"✅ تم تسجيل صوتك: {'موافق' if vote == 'accept' else 'رافض'}")

    if total_voted < total_members:
        return  # لم يصوت الجميع بعد

    # جميع الأعضاء صوتوا
    clear_dissolve_votes(alliance_id)

    if votes["reject"] == 0:
        # الجميع وافق → حذف التحالف
        from database.db_queries.alliances_queries import delete_alliance as _del
        _del(alliance_id)
        try:
            bot.edit_message_text("💥 تم حل التحالف بموافقة الجميع.",
                                  call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        # إشعار جميع الأعضاء
        for member in alliance["members"]:
            uid = member["user_id"] if isinstance(member, dict) else member[0]
            try:
                bot.send_message(uid, f"💥 تم حل تحالف <b>{alliance['name']}</b>.", parse_mode="HTML")
            except Exception:
                pass
    else:
        # رفض أحدهم → نقل القيادة للأقوى
        _transfer_to_strongest(alliance_id, alliance)
        try:
            bot.edit_message_text("⚠️ رُفض الحل. تم نقل القيادة للدولة الأقوى.",
                                  call.message.chat.id, call.message.message_id)
        except Exception:
            pass


def _transfer_to_strongest(alliance_id, alliance):
    """ينقل القيادة لعضو دولته الأقوى"""
    from database.db_queries.alliances_queries import transfer_leadership
    from database.db_queries.countries_queries import get_all_cities_of_country_by_country_id
    from database.db_queries.war_queries import get_city_troops

    best_uid = None
    best_power = -1

    for member in alliance["members"]:
        uid = member["user_id"] if isinstance(member, dict) else member[0]
        cid = member.get("country_id") if isinstance(member, dict) else None
        if not cid:
            continue
        cities = get_all_cities_of_country_by_country_id(cid)
        power = 0
        for city in cities:
            city_id = city["id"] if isinstance(city, dict) else city[0]
            for t in get_city_troops(city_id):
                t = dict(t)
                power += t.get("quantity", 0) * t.get("attack", 1)
        if power > best_power:
            best_power = power
            best_uid = uid

    if best_uid and best_uid != alliance["leader_id"]:
        transfer_leadership(alliance_id, alliance["leader_id"], best_uid)
