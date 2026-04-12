# political war handler

"""
معالج الحرب السياسية — واجهة المستخدم
Political War Handler — UI & Callbacks
"""
from core.bot import bot
from utils.pagination import btn, send_ui, edit_ui, register_action, paginate_list, grid
from database.db_queries.countries_queries import get_country_by_owner, get_all_countries
from database.db_queries.alliances_queries import (
    get_alliance_by_country, get_alliance_by_id, get_all_active_alliances,
)
from database.db_queries.political_war_queries import (
    get_political_war, get_active_political_wars, get_war_votes,
    get_vote_summary, get_war_members, get_total_side_power,
    get_wars_for_country, get_war_log, get_user_vote, is_country_in_war,
    get_alliance_loyalty_board,
)
from modules.war.services.political_war_service import (
    declare_war, vote_on_war, withdraw_country_from_war,
    resolve_war_outcome, get_war_status_text,
)
from utils.helpers import get_lines
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME


def _back_btn(user_id, chat_id):
    return btn("🔙 رجوع", "pol_war_main", data={}, owner=(user_id, chat_id))


# ══════════════════════════════════════════
# 🏠 القائمة الرئيسية
# ══════════════════════════════════════════

def open_political_war_menu(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    country = get_country_by_owner(user_id)
    if not country:
        from core.personality import send_with_delay, no_country_msg
        send_with_delay(chat_id, no_country_msg(), delay=0.4,
                        reply_to=message.message_id)
        return

    country = dict(country)
    active_wars = get_active_political_wars()
    my_wars = get_wars_for_country(country["id"], limit=3)
    in_war = is_country_in_war(country["id"])

    status = f"⚔️ في حرب نشطة" if in_war else "☮️ لا توجد حرب نشطة"

    buttons = [
        btn("⚔️ إعلان حرب", "pol_war_declare_type", data={},
            owner=(user_id, chat_id), color="d"),
        btn("🗳️ الحروب النشطة", "pol_war_active_list", data={"page": 0},
            owner=(user_id, chat_id), color="p"),
        btn("📜 سجل حروبي", "pol_war_my_history", data={"page": 0},
            owner=(user_id, chat_id), color="p"),
        btn("🚪 الانسحاب من حرب", "pol_war_withdraw_list", data={},
            owner=(user_id, chat_id), color="su"),
        btn("🏅 لوحة الولاء", "pol_war_loyalty", data={},
            owner=(user_id, chat_id), color="p"),
    ]

    send_ui(
        chat_id=chat_id,
        text=(
            f"⚔️ <b>نظام الحرب السياسية</b>\n"
            f"{get_lines()}\n"
            f"🏳️ دولتك: <b>{country['name']}</b>\n"
            f"📌 {status}\n"
            f"🌐 حروب نشطة: {len(active_wars)}\n\n"
            f"الحروب السياسية أحداث منظمة تشمل التصويت وتوازن القوى."
        ),
        buttons=buttons,
        layout=[2, 2, 1],
        owner_id=user_id,
        reply_to=message.message_id,
    )


@register_action("pol_war_main")
def back_to_main(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!")
        return
    country = dict(country)
    active_wars = get_active_political_wars()
    in_war = is_country_in_war(country["id"])
    status = "⚔️ في حرب نشطة" if in_war else "☮️ لا توجد حرب نشطة"

    buttons = [
        btn("⚔️ إعلان حرب", "pol_war_declare_type", data={},
            owner=(user_id, chat_id), color="d"),
        btn("🗳️ الحروب النشطة", "pol_war_active_list", data={"page": 0},
            owner=(user_id, chat_id), color="p"),
        btn("📜 سجل حروبي", "pol_war_my_history", data={"page": 0},
            owner=(user_id, chat_id), color="p"),
        btn("🚪 الانسحاب من حرب", "pol_war_withdraw_list", data={},
            owner=(user_id, chat_id), color="su"),
    ]
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=(
                f"⚔️ <b>نظام الحرب السياسية</b>\n"
                f"{get_lines()}\n"
                f"🏳️ دولتك: <b>{country['name']}</b>\n"
                f"📌 {status}\n"
                f"🌐 حروب نشطة: {len(active_wars)}\n\n"
                f"الحروب السياسية أحداث منظمة تشمل التصويت وتوازن القوى."
            ),
            buttons=buttons, layout=[2, 2])


# ══════════════════════════════════════════
# ⚔️ إعلان الحرب — اختيار النوع
# ══════════════════════════════════════════

@register_action("pol_war_declare_type")
def show_declare_type(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!")
        return

    alliance = get_alliance_by_country(dict(country)["id"])

    buttons = [
        btn("🏳️ دولة ضد دولة", "pol_war_declare_dtype",
            data={"wtype": "country_vs_country"}, owner=(user_id, chat_id), color="d"),
    ]
    if alliance:
        buttons += [
            btn("🏰 تحالف ضد تحالف", "pol_war_declare_dtype",
                data={"wtype": "alliance_vs_alliance"}, owner=(user_id, chat_id), color="d"),
            btn("🌐 هجين (تحالف ضد دولة)", "pol_war_declare_dtype",
                data={"wtype": "hybrid"}, owner=(user_id, chat_id), color="su"),
        ]
    buttons.append(_back_btn(user_id, chat_id))

    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=(
                "⚔️ <b>إعلان حرب سياسية</b>\n\n"
                "اختر نوع الحرب:\n"
                "• <b>دولة ضد دولة</b>: هجوم مباشر على دولة أخرى\n"
                "• <b>تحالف ضد تحالف</b>: حرب بين تحالفين كاملين\n"
                "• <b>هجين</b>: تحالفك ضد دولة مستقلة"
            ),
            buttons=buttons, layout=[1] * len(buttons))


@register_action("pol_war_declare_dtype")
def show_declare_dectype(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    wtype = data.get("wtype", "country_vs_country")

    buttons = [
        btn("⚔️ هجومية", "pol_war_declare_target",
            data={"wtype": wtype, "dtype": "offensive"}, owner=(user_id, chat_id), color="d"),
        btn("🛡️ دفاعية", "pol_war_declare_target",
            data={"wtype": wtype, "dtype": "defensive"}, owner=(user_id, chat_id), color="su"),
        _back_btn(user_id, chat_id),
    ]

    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=(
                "⚔️ <b>نوع الإعلان</b>\n\n"
                "• <b>هجومية</b>: أنت البادئ — المشاركة اختيارية للحلفاء لكن الانتصار يُكافأ\n"
                "• <b>دفاعية</b>: ردّ على تهديد — عقوبة أعلى على تجاهل الدعم"
            ),
            buttons=buttons, layout=[2, 1])


@register_action("pol_war_declare_target")
def show_declare_target(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    wtype = data.get("wtype", "country_vs_country")
    dtype = data.get("dtype", "offensive")
    page = int(data.get("page", 0))

    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!")
        return
    my_country_id = dict(country)["id"]

    bot.answer_callback_query(call.id)

    if wtype == "alliance_vs_alliance":
        # عرض قائمة التحالفات
        alliances = get_all_active_alliances(
            exclude_id=get_alliance_by_country(my_country_id)["id"]
            if get_alliance_by_country(my_country_id) else None
        )
        items, total = paginate_list(alliances, page, per_page=6)
        buttons = [
            btn(f"🏰 {a['name']} (قوة: {a['power']:.0f})", "pol_war_confirm_declare",
                data={"wtype": wtype, "dtype": dtype, "target_id": a["id"]},
                owner=(user_id, chat_id), color="d")
            for a in items
        ]
        nav = []
        if page > 0:
            nav.append(btn("◀️", "pol_war_declare_target",
                           data={"wtype": wtype, "dtype": dtype, "page": page - 1},
                           owner=(user_id, chat_id)))
        if page < total - 1:
            nav.append(btn("▶️", "pol_war_declare_target",
                           data={"wtype": wtype, "dtype": dtype, "page": page + 1},
                           owner=(user_id, chat_id)))
        nav.append(_back_btn(user_id, chat_id))
        layout = grid(len(items), 1) + [len(nav)]
        edit_ui(call, text="🏰 <b>اختر التحالف الهدف:</b>",
                buttons=buttons + nav, layout=layout)
    else:
        # عرض قائمة الدول
        all_countries = [dict(c) for c in get_all_countries() if c["id"] != my_country_id]
        items, total = paginate_list(all_countries, page, per_page=6)
        buttons = [
            btn(f"🏳️ {c['name']}", "pol_war_confirm_declare",
                data={"wtype": wtype, "dtype": dtype, "target_id": c["id"]},
                owner=(user_id, chat_id), color="d")
            for c in items
        ]
        nav = []
        if page > 0:
            nav.append(btn("◀️", "pol_war_declare_target",
                           data={"wtype": wtype, "dtype": dtype, "page": page - 1},
                           owner=(user_id, chat_id)))
        if page < total - 1:
            nav.append(btn("▶️", "pol_war_declare_target",
                           data={"wtype": wtype, "dtype": dtype, "page": page + 1},
                           owner=(user_id, chat_id)))
        nav.append(_back_btn(user_id, chat_id))
        layout = grid(len(items), 2) + [len(nav)]
        edit_ui(call, text="🏳️ <b>اختر الدولة الهدف:</b>",
                buttons=buttons + nav, layout=layout)


@register_action("pol_war_confirm_declare")
def confirm_declare(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    wtype = data.get("wtype", "country_vs_country")
    dtype = data.get("dtype", "offensive")
    target_id = data.get("target_id")

    wtype_ar = {
        "country_vs_country": "دولة ضد دولة",
        "alliance_vs_alliance": "تحالف ضد تحالف",
        "hybrid": "هجين",
    }.get(wtype, wtype)
    dtype_ar = {"offensive": "هجومية", "defensive": "دفاعية"}.get(dtype, dtype)

    from modules.war.services.political_war_service import WAR_DECLARATION_COST
    buttons = [
        btn("✅ تأكيد الإعلان", "pol_war_do_declare",
            data={"wtype": wtype, "dtype": dtype, "target_id": target_id},
            owner=(user_id, chat_id), color="d"),
        _back_btn(user_id, chat_id),
    ]
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=(
                f"⚔️ <b>تأكيد إعلان الحرب</b>\n"
                f"{get_lines()}\n"
                f"📋 النوع: {wtype_ar}\n"
                f"📌 الإعلان: {dtype_ar}\n"
                f"💰 التكلفة: {WAR_DECLARATION_COST} {CURRENCY_ARABIC_NAME}\n\n"
                f"سيُفتح التصويت لمدة 24 ساعة لأعضاء تحالفك.\n"
                f"هل تؤكد؟"
            ),
            buttons=buttons, layout=[1, 1])


@register_action("pol_war_do_declare")
def do_declare(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    wtype = data.get("wtype", "country_vs_country")
    dtype = data.get("dtype", "offensive")
    target_id = data.get("target_id")

    target_country_id = target_id if wtype in ("country_vs_country", "hybrid") else None
    target_alliance_id = target_id if wtype == "alliance_vs_alliance" else None

    success, msg, war_id = declare_war(
        user_id=user_id,
        war_type=wtype,
        declaration_type=dtype,
        target_country_id=target_country_id,
        target_alliance_id=target_alliance_id,
    )

    bot.answer_callback_query(call.id, "✅ تم!" if success else "❌ فشل")

    if success and war_id:
        buttons = [
            btn("🗳️ عرض التصويت", "pol_war_view", data={"war_id": war_id},
                owner=(user_id, chat_id), color="p"),
            _back_btn(user_id, chat_id),
        ]
        edit_ui(call, text=msg, buttons=buttons, layout=[1, 1])
    else:
        edit_ui(call, text=msg, buttons=[_back_btn(user_id, chat_id)], layout=[1])


# ══════════════════════════════════════════
# 🗳️ عرض الحرب والتصويت
# ══════════════════════════════════════════

@register_action("pol_war_view")
def view_war(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    war_id = data.get("war_id")

    if not war_id:
        bot.answer_callback_query(call.id, "❌ معرّف الحرب مفقود")
        return

    war = get_political_war(war_id)
    if not war:
        bot.answer_callback_query(call.id, "❌ الحرب غير موجودة")
        return

    status_text = get_war_status_text(war_id)
    country = get_country_by_owner(user_id)
    my_country_id = dict(country)["id"] if country else None

    buttons = []

    # ── مرحلة التصويت ──
    if war["status"] == "voting" and my_country_id:
        existing_vote = get_user_vote(war_id, my_country_id)
        if not existing_vote:
            buttons += [
                btn("✅ دعم", "pol_war_vote",
                    data={"war_id": war_id, "vote": "support"},
                    owner=(user_id, chat_id), color="su"),
                btn("❌ رفض", "pol_war_vote",
                    data={"war_id": war_id, "vote": "reject"},
                    owner=(user_id, chat_id), color="d"),
                btn("⚪ محايد", "pol_war_vote",
                    data={"war_id": war_id, "vote": "neutral"},
                    owner=(user_id, chat_id), color="p"),
            ]
        else:
            vote_ar = {"support": "✅ دعم", "reject": "❌ رفض",
                       "neutral": "⚪ محايد"}.get(existing_vote["vote"], existing_vote["vote"])
            changes_used = int(existing_vote.get("vote_change_count") or 0)
            changes_left = max(0, 2 - changes_used)
            change_label = f"صوّتت: {vote_ar} | تغيير ({changes_left} متبقي)"
            buttons.append(btn(change_label, "pol_war_vote_change",
                               data={"war_id": war_id}, owner=(user_id, chat_id), color="p"))
        buttons.append(btn("📊 تفاصيل التصويت", "pol_war_vote_detail",
                           data={"war_id": war_id}, owner=(user_id, chat_id), color="p"))

    # ── مرحلة التحضير ──
    if war["status"] == "preparation" and my_country_id:
        members = get_war_members(war_id)
        if any(m["country_id"] == my_country_id for m in members):
            buttons.append(btn("🚪 انسحاب (قبل البدء)", "pol_war_withdraw_confirm",
                               data={"war_id": war_id}, owner=(user_id, chat_id), color="su"))

    # ── مرحلة الحرب النشطة ──
    if war["status"] == "active" and my_country_id:
        members = get_war_members(war_id)
        if any(m["country_id"] == my_country_id for m in members):
            buttons.append(btn("🚪 انسحاب ⚠️", "pol_war_withdraw_confirm",
                               data={"war_id": war_id}, owner=(user_id, chat_id), color="d"))

    buttons += [
        btn("👥 الأعضاء", "pol_war_members", data={"war_id": war_id},
            owner=(user_id, chat_id), color="p"),
        btn("📋 السجل", "pol_war_log", data={"war_id": war_id, "page": 0},
            owner=(user_id, chat_id), color="p"),
        _back_btn(user_id, chat_id),
    ]

    bot.answer_callback_query(call.id)
    n_vote_btns = 3 if (war["status"] == "voting" and not get_user_vote(war_id, my_country_id or 0)) else 0
    layout = ([3] if n_vote_btns == 3 else []) + [1] * (len(buttons) - n_vote_btns)
    edit_ui(call, text=status_text, buttons=buttons, layout=layout)


@register_action("pol_war_vote_change")
def vote_change(call, data):
    """يعرض أزرار تغيير التصويت مع عداد التغييرات المتبقية."""
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    war_id  = data.get("war_id")

    # جلب عدد التغييرات المتبقية
    country = get_country_by_owner(user_id)
    changes_left = "؟"
    locked_msg   = ""
    if country:
        existing = get_user_vote(war_id, dict(country)["id"])
        if existing:
            used = int(existing.get("vote_change_count") or 0)
            changes_left = max(0, 2 - used)
            war = get_political_war(war_id)
            if war:
                time_left = war["voting_ends_at"] - int(__import__("time").time())
                if time_left <= 60:
                    locked_msg = "\n\n🔒 <b>التصويت مقفل</b> — آخر 60 ثانية."

    if locked_msg:
        bot.answer_callback_query(call.id, "🔒 التصويت مقفل في آخر 60 ثانية!", show_alert=True)
        return

    if changes_left == 0:
        bot.answer_callback_query(call.id, "⛔ وصلت للحد الأقصى لتغيير التصويت (2 مرات).", show_alert=True)
        return

    buttons = [
        btn("✅ دعم",   "pol_war_vote", data={"war_id": war_id, "vote": "support"},
            owner=(user_id, chat_id), color="su"),
        btn("❌ رفض",   "pol_war_vote", data={"war_id": war_id, "vote": "reject"},
            owner=(user_id, chat_id), color="d"),
        btn("⚪ محايد", "pol_war_vote", data={"war_id": war_id, "vote": "neutral"},
            owner=(user_id, chat_id), color="p"),
        btn("🔙 رجوع",  "pol_war_view", data={"war_id": war_id}, owner=(user_id, chat_id)),
    ]
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=f"🗳️ <b>تغيير تصويتك</b>\n⚠️ تغييرات متبقية: {changes_left}/2",
            buttons=buttons, layout=[3, 1])


@register_action("pol_war_vote_detail")
def vote_detail(call, data):
    """يعرض تفاصيل التصويت الكاملة: ثلاثة أشرطة + وزن كل دولة."""
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    war_id  = data.get("war_id")

    votes   = get_war_votes(war_id)
    summary = get_vote_summary(war_id)

    def bar(pct):
        f = int(pct / 10)
        return f"{'█'*f}{'░'*(10-f)}"

    s_pct = summary["support_pct"]
    r_pct = summary["reject_pct"]
    n_pct = summary["neutral_pct"]
    thr   = summary["threshold_pct"]

    text = (
        f"📊 <b>تفاصيل التصويت — حرب #{war_id}</b>\n"
        f"{get_lines()}\n"
        f"🟢 دعم    [{bar(s_pct)}] {s_pct:.1f}%\n"
        f"🔴 رفض   [{bar(r_pct)}] {r_pct:.1f}%\n"
        f"🟡 محايد [{bar(n_pct)}] {n_pct:.1f}%\n"
        f"{get_lines()}\n"
        f"🎯 العتبة: {thr:.0f}%  |  "
        f"{'🟢 سيبدأ' if summary['passes'] else '🔴 لن يبدأ'}\n"
        f"📊 الأوزان: دعم {summary['support']:.1f} / رفض {summary['reject']:.1f} "
        f"/ محايد {summary['neutral']:.1f}  ({summary['count']} صوت)\n"
        f"{get_lines()}\n"
        f"<b>تصويت كل دولة:</b>\n"
    )

    vote_icon = {"support": "🟢", "reject": "🔴", "neutral": "🟡"}
    for v in votes:
        icon    = vote_icon.get(v["vote"], "•")
        changes = int(v.get("vote_change_count") or 0)
        change_note = f" (غيّر {changes}×)" if changes > 0 else ""
        text += f"{icon} {v['country_name']} — وزن: {v['vote_weight']:.1f}{change_note}\n"

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text,
            buttons=[btn("🔙", "pol_war_view", data={"war_id": war_id},
                         owner=(user_id, chat_id))],
            layout=[1])


@register_action("pol_war_vote")
def cast_vote(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    war_id = data.get("war_id")
    vote = data.get("vote", "neutral")

    success, msg = vote_on_war(user_id, war_id, vote)
    bot.answer_callback_query(call.id, "✅ تم تسجيل تصويتك" if success else "❌ فشل")

    buttons = [
        btn("🔄 تحديث", "pol_war_view", data={"war_id": war_id},
            owner=(user_id, chat_id), color="p"),
        _back_btn(user_id, chat_id),
    ]
    edit_ui(call, text=msg, buttons=buttons, layout=[1, 1])


# ══════════════════════════════════════════
# 📋 قوائم الحروب
# ══════════════════════════════════════════

@register_action("pol_war_active_list")
def show_active_wars(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    page = int(data.get("page", 0))

    wars = get_active_political_wars()
    if not wars:
        bot.answer_callback_query(call.id)
        edit_ui(call, text="🕊️ لا توجد حروب سياسية نشطة حالياً.",
                buttons=[_back_btn(user_id, chat_id)], layout=[1])
        return

    items, total = paginate_list(wars, page, per_page=5)
    status_ar = {"voting": "🗳️ تصويت", "active": "⚔️ نشطة"}
    text = f"🌐 <b>الحروب السياسية النشطة</b> (صفحة {page+1}/{total})\n{get_lines()}\n"

    buttons = []
    for w in items:
        s = status_ar.get(w["status"], w["status"])
        wtype_ar = {"country_vs_country": "دولة/دولة",
                    "alliance_vs_alliance": "تحالف/تحالف",
                    "hybrid": "هجين"}.get(w["war_type"], "")
        text += f"\n#{w['id']} {s} — {wtype_ar}"
        buttons.append(btn(f"#{w['id']} {s} {wtype_ar}", "pol_war_view",
                           data={"war_id": w["id"]}, owner=(user_id, chat_id), color="p"))

    nav = []
    if page > 0:
        nav.append(btn("◀️", "pol_war_active_list", data={"page": page - 1},
                       owner=(user_id, chat_id)))
    if page < total - 1:
        nav.append(btn("▶️", "pol_war_active_list", data={"page": page + 1},
                       owner=(user_id, chat_id)))
    nav.append(_back_btn(user_id, chat_id))

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons + nav,
            layout=[1] * len(buttons) + [len(nav)])


@register_action("pol_war_my_history")
def show_my_history(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    page = int(data.get("page", 0))

    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!")
        return

    wars = get_wars_for_country(dict(country)["id"], limit=20)
    if not wars:
        bot.answer_callback_query(call.id)
        edit_ui(call, text="📜 لا يوجد سجل حروب لدولتك.",
                buttons=[_back_btn(user_id, chat_id)], layout=[1])
        return

    items, total = paginate_list(wars, page, per_page=5)
    status_ar = {"voting": "🗳️", "active": "⚔️", "ended": "🏁", "cancelled": "❌"}
    text = f"📜 <b>سجل حروبي</b> (صفحة {page+1}/{total})\n{get_lines()}\n"

    buttons = []
    for w in items:
        s = status_ar.get(w["status"], "")
        text += f"\n{s} #{w['id']} — {w['war_type']}"
        buttons.append(btn(f"{s} #{w['id']}", "pol_war_view",
                           data={"war_id": w["id"]}, owner=(user_id, chat_id), color="p"))

    nav = []
    if page > 0:
        nav.append(btn("◀️", "pol_war_my_history", data={"page": page - 1},
                       owner=(user_id, chat_id)))
    if page < total - 1:
        nav.append(btn("▶️", "pol_war_my_history", data={"page": page + 1},
                       owner=(user_id, chat_id)))
    nav.append(_back_btn(user_id, chat_id))

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=buttons + nav,
            layout=[1] * len(buttons) + [len(nav)])


# ══════════════════════════════════════════
# 👥 أعضاء الحرب
# ══════════════════════════════════════════

@register_action("pol_war_members")
def show_war_members(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    war_id = data.get("war_id")

    att = get_war_members(war_id, "attacker")
    dfd = get_war_members(war_id, "defender")
    att_power = get_total_side_power(war_id, "attacker")
    def_power = get_total_side_power(war_id, "defender")

    def fmt_side(members, label):
        if not members:
            return f"{label}: لا أحد\n"
        lines = f"{label} (قوة: {sum(m['power_contributed'] for m in members):.0f}):\n"
        for m in members:
            lines += f"  • {m['country_name']} — {m['power_contributed']:.0f}\n"
        return lines

    text = (
        f"👥 <b>أعضاء الحرب #{war_id}</b>\n{get_lines()}\n"
        f"{fmt_side(att, '⚔️ المهاجمون')}\n"
        f"{fmt_side(dfd, '🛡️ المدافعون')}"
    )

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text,
            buttons=[btn("🔙 رجوع للحرب", "pol_war_view",
                         data={"war_id": war_id}, owner=(user_id, chat_id))],
            layout=[1])


# ══════════════════════════════════════════
# 📋 سجل الأحداث
# ══════════════════════════════════════════

@register_action("pol_war_log")
def show_war_log(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    war_id = data.get("war_id")
    page = int(data.get("page", 0))

    logs = get_war_log(war_id, limit=50)
    if not logs:
        bot.answer_callback_query(call.id)
        edit_ui(call, text="📋 لا يوجد سجل لهذه الحرب.",
                buttons=[btn("🔙", "pol_war_view", data={"war_id": war_id},
                             owner=(user_id, chat_id))], layout=[1])
        return

    items, total = paginate_list(logs, page, per_page=8)
    event_ar = {
        "declared": "📣 إعلان حرب",
        "voted_support": "✅ صوّت بالدعم",
        "voted_reject": "❌ صوّت بالرفض",
        "voted_neutral": "⚪ صوّت محايداً",
        "war_started": "⚔️ بدأت الحرب",
        "war_ended": "🏁 انتهت الحرب",
        "withdrew_before": "🚪 انسحب قبل البدء",
        "withdrew_after": "⚠️ انسحب بعد البدء",
        "joined_late": "➕ انضم متأخراً",
        "cancelled": "❌ أُلغيت الحرب",
    }

    text = f"📋 <b>سجل الحرب #{war_id}</b> (صفحة {page+1}/{total})\n{get_lines()}\n"
    for log in items:
        ev = event_ar.get(log["event_type"], log["event_type"])
        name = log.get("country_name") or "النظام"
        text += f"\n{ev} — {name}"

    nav = []
    if page > 0:
        nav.append(btn("◀️", "pol_war_log",
                       data={"war_id": war_id, "page": page - 1},
                       owner=(user_id, chat_id)))
    if page < total - 1:
        nav.append(btn("▶️", "pol_war_log",
                       data={"war_id": war_id, "page": page + 1},
                       owner=(user_id, chat_id)))
    nav.append(btn("🔙", "pol_war_view", data={"war_id": war_id},
                   owner=(user_id, chat_id)))

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text, buttons=nav, layout=[len(nav)])


# ══════════════════════════════════════════
# 🚪 الانسحاب
# ══════════════════════════════════════════

@register_action("pol_war_withdraw_list")
def show_withdraw_list(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!")
        return
    my_country_id = dict(country)["id"]

    active = get_active_political_wars()
    my_wars = []
    for w in active:
        members = get_war_members(w["id"])
        if any(m["country_id"] == my_country_id for m in members):
            my_wars.append(w)

    if not my_wars:
        bot.answer_callback_query(call.id)
        edit_ui(call, text="🚪 لست مشاركاً في أي حرب سياسية نشطة.",
                buttons=[_back_btn(user_id, chat_id)], layout=[1])
        return

    buttons = [
        btn(f"🚪 الانسحاب من حرب #{w['id']}", "pol_war_withdraw_confirm",
            data={"war_id": w["id"]}, owner=(user_id, chat_id), color="d")
        for w in my_wars
    ]
    buttons.append(_back_btn(user_id, chat_id))

    bot.answer_callback_query(call.id)
    edit_ui(call, text="🚪 <b>الانسحاب من حرب</b>\n\nاختر الحرب التي تريد الانسحاب منها:",
            buttons=buttons, layout=[1] * len(buttons))


@register_action("pol_war_withdraw_confirm")
def confirm_withdraw(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    war_id = data.get("war_id")

    war = get_political_war(war_id)
    if not war:
        bot.answer_callback_query(call.id, "❌ الحرب غير موجودة")
        return

    warning = ""
    if war["status"] == "active":
        warning = "\n\n⚠️ <b>تحذير:</b> الانسحاب بعد بدء الحرب يُخصم نقاط من سمعتك!"

    buttons = [
        btn("✅ تأكيد الانسحاب", "pol_war_do_withdraw",
            data={"war_id": war_id}, owner=(user_id, chat_id), color="d"),
        btn("🔙 إلغاء", "pol_war_view",
            data={"war_id": war_id}, owner=(user_id, chat_id)),
    ]
    bot.answer_callback_query(call.id)
    edit_ui(call,
            text=f"🚪 <b>تأكيد الانسحاب من الحرب #{war_id}</b>{warning}\n\nهل أنت متأكد؟",
            buttons=buttons, layout=[1, 1])


@register_action("pol_war_do_withdraw")
def do_withdraw(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    war_id = data.get("war_id")

    success, msg = withdraw_country_from_war(user_id, war_id)
    bot.answer_callback_query(call.id, "✅ تم" if success else "❌ فشل")
    edit_ui(call, text=msg,
            buttons=[_back_btn(user_id, chat_id)], layout=[1])


# ══════════════════════════════════════════
# 🏅 لوحة الولاء
# ══════════════════════════════════════════

@register_action("pol_war_loyalty")
def show_loyalty_board(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    country = get_country_by_owner(user_id)
    if not country:
        bot.answer_callback_query(call.id, "❌ لا تملك دولة!")
        return
    from database.db_queries.alliances_queries import get_alliance_by_country
    alliance = get_alliance_by_country(dict(country)["id"])
    if not alliance:
        bot.answer_callback_query(call.id, "❌ لست في تحالف!")
        return

    board = get_alliance_loyalty_board(alliance["id"])
    text = f"🏅 <b>لوحة الولاء — {alliance['name']}</b>\n{get_lines()}\n"
    for entry in board:
        score = entry["loyalty_score"]
        label = entry["label"]
        text += f"{label} {entry['country_name']}: {score:.0f}/100\n"

    if not board:
        text += "لا توجد بيانات ولاء بعد."

    bot.answer_callback_query(call.id)
    edit_ui(call, text=text,
            buttons=[_back_btn(user_id, chat_id)], layout=[1])
