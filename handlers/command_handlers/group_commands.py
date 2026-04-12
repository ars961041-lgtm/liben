"""
أوامر المجموعات فقط.
الكتم، الحظر، التقييد، إدارة المجموعة، الألعاب، البنك، الحرب، الدول، إلخ.
"""
from core.bot import bot
from core.admin import is_any_dev
from handlers.group_admin.restrictions import get_target_user
from database.db_queries.group_features_queries import is_feature_enabled


def handle_group_commands(message, normalized_text: str, text: str) -> bool:
    """
    يعالج الأوامر المخصصة للمجموعات فقط.
    يرجع True إذا تم التعامل مع الأمر.
    """
    from handlers.group_admin.admin_commands import (
        custom_title, pin_message, delete_message, set_group_bio, set_group_name
    )
    from handlers.group_admin.developer import DEV_COMMANDS
    from handlers.group_admin.permissions import is_developer
    from handlers.group_admin.restrictions import get_target_user
    from handlers.group_admin.promote import handle_promote_command
    from handlers.group_admin.promote.promote_handler import handle_edit_command
    from handlers.games.games_handler import games_command
    from handlers.games.entertainment_games import entertainment_games_command
    from handlers.tops.tops_handler import top_commands
    from modules.bank.commands.bank_commands import bank_commands
    from modules.country.country_commands import country_commands
    from modules.country.city_commands import city_commands
    from modules.country.daily_tasks_commands import daily_tasks_commands
    from modules.war.handlers.advanced_war_handler import handle_war_text_commands
    from modules.alliances.alliance_commands import alliance_commands
    from handlers.command_handlers.progression_commands import collect_city_income
    from handlers.command_handlers.mute_commands import (
        handle_global_mute_cmd, handle_global_unmute_cmd
    )

    uid = message.from_user.id
    cid = message.chat.id

    # ── رابط المجموعة ──
    if normalized_text in ("الرابط", "رابط القروب"):
        _send_group_link(message)
        return True

    # ── معلومات المستخدم المُشار إليه ──
    if normalized_text in ("دولته", "تحالفه", "مدينته"):
        if not message.reply_to_message or not message.reply_to_message.from_user:
            bot.reply_to(message, "↩️ رد على رسالة المستخدم أولاً.")
            return True
        target_id = message.reply_to_message.from_user.id
        if normalized_text == "دولته":
            from database.db_queries.countries_queries import get_user_country_name
            name = get_user_country_name(target_id)
            bot.reply_to(message, f"🏳️ الدولة: {name}" if name else "لا يوجد")
        elif normalized_text == "تحالفه":
            from database.db_queries.alliances_queries import get_alliance_by_user
            alliance = get_alliance_by_user(target_id)
            name = alliance.get("name") if alliance else None
            bot.reply_to(message, f"🤝 التحالف: {name}" if name else "لا يوجد")
        elif normalized_text == "مدينته":
            from database.db_queries.cities_queries import get_user_city
            city = get_user_city(target_id)
            name = city["name"] if city else None
            bot.reply_to(message, f"🏙 المدينة: {name}" if name else "لا يوجد")
        return True

    # ── الصياح ──
    if normalized_text == "صيح":
        from handlers.shout_handler import handle_shout
        return handle_shout(message)

    # ── الهمسات ──
    from modules.whispers.whisper_handler import handle_whisper_command, WHISPER_TRIGGERS
    lower_text = normalized_text.lower()
    if any(lower_text.startswith(t) for t in WHISPER_TRIGGERS):
        return handle_whisper_command(message)

    # ── لوحة تحكم ميزات المجموعة ──
    if normalized_text in ["الأوامر", "الاوامر"]:
        from handlers.group_admin.group_features import handle_features_control
        return handle_features_control(message)

    # ── /developer_gift — للمطور الأساسي فقط، في أي مجموعة ──
    if normalized_text in ["/developer_gift", "هدية", "developer_gift"]:
        from core.admin import is_primary_dev
        from modules.magazine.magazine_handler import open_gift_from_message
        if not is_primary_dev(uid):
            bot.reply_to(message, "❌ هذا الأمر للمطور الأساسي فقط.")
            return True
        open_gift_from_message(message)
        return True

    # ── أوامر المطور (كتم عالمي، متجر، لوحة) ──
    if is_any_dev(uid):
        if normalized_text.startswith("كتم عالمي"):
            handle_global_mute_cmd(message)
            return True
        if normalized_text.startswith("رفع كتم عالمي"):
            handle_global_unmute_cmd(message)
            return True
        if normalized_text in ["تحديث جروب البوت", "تعيين جروب البوت"]:
            _set_dev_group(message)
            return True
        if normalized_text in ["متجر المطورين", "متجر المطور", "dev store"]:
            from handlers.group_admin.developer.dev_store import open_dev_store
            open_dev_store(message)
            return True
        if normalized_text in ["إدارة الأذكار", "ادارة الأذكار", "azkar admin"]:
            from modules.azkar.azkar_handler import open_azkar_admin
            open_azkar_admin(message)
            return True
        if normalized_text in ["إنشاء منشور", "انشاء منشور", "new post"]:
            from modules.post_creator import open_post_creator
            open_post_creator(message)
            return True

    # ── قوائم الإجراءات التأديبية (مشرفون / مطورون) ──
    if normalized_text in ("المكتومين", "المكتومون"):
        from handlers.group_admin.moderation_list import show_moderation_list
        show_moderation_list(message, "muted")
        return True
    if normalized_text in ("المحظورين", "المحظورون"):
        from handlers.group_admin.moderation_list import show_moderation_list
        show_moderation_list(message, "banned")
        return True
    if normalized_text in ("المقيدين", "المقيدون"):
        from handlers.group_admin.moderation_list import show_moderation_list
        show_moderation_list(message, "restricted")
        return True
    if normalized_text in ("مكتومين سورس", "كتم عالمي قائمة"):
        from handlers.group_admin.moderation_list import show_moderation_list
        show_moderation_list(message, "global_muted")
        return True

    # ── قوانين المجموعة ──
    from modules.rules import handle_rules_command
    if handle_rules_command(message):
        return True
        if text.startswith("اضف "):
            from modules.content_hub.hub_handler import handle_add_content_command
            if handle_add_content_command(message):
                return True

    # ── ترقية / تعديل مشرف ──
    if normalized_text in ["/promote", "رفع مشرف"]:
        from handlers.group_admin.restrictions import promote_admin
        promote_admin(message)
        return True
    if normalized_text in ["/edit_admin", "تعديل مشرف"]:
        handle_edit_command(message)
        return True

    # ── البنك ──
    if is_feature_enabled(cid, "enable_games"):
        if bank_commands(message):
            return True

    # ── الإحصائيات والتحليلات ──
    if is_feature_enabled(cid, "enable_games"):
        from handlers.analytics_handler import analytics_commands
        if analytics_commands(message):
            return True

    # ── الألعاب ──
    if is_feature_enabled(cid, "enable_games"):
        if games_command(message):
            return True
        if entertainment_games_command(message):
            return True

    # ── التوبات ──
    if is_feature_enabled(cid, "enable_games"):
        if top_commands(message):
            return True

    # ── الدولة والمدن ──
    if is_feature_enabled(cid, "enable_games"):
        if country_commands(message):   return True
        if city_commands(message):      return True
        if daily_tasks_commands(message): return True
        if normalized_text in ["دخل", "دخل مدينتي", "جمع الدخل", "اقتصادي"]:
            collect_city_income(message)
            return True
        if normalized_text in ("ترتيبات", "تصنيفات", "ترتيب المدن", "ترتيب الدول"):
            from handlers.rankings_handler import handle_rankings_command
            handle_rankings_command(message)
            return True
        if normalized_text in ("اقتصاد مدينتي", "سكان مدينتي", "حالة مدينتي", "مدينة"):
            if city_commands(message):
                return True
        if normalized_text in ("قرار حكومي", "قرارات الدولة", "قراراتي"):
            from handlers.government_handler import handle_government_command
            handle_government_command(message)
            return True

    # ── التحالفات ──
    if is_feature_enabled(cid, "enable_games"):
        if alliance_commands(message):
            return True

    # ── الحرب ──
    if is_feature_enabled(cid, "enable_games"):
        if handle_war_text_commands(message):
            return True

    # ── الحرب السياسية ──
    if is_feature_enabled(cid, "enable_games"):
        if normalized_text in ("الحرب السياسية", "حرب سياسية", "political war", "/political_war"):
            from modules.war.handlers.political_war_handler import open_political_war_menu
            open_political_war_menu(message)
            return True
        if normalized_text in ("سجل الحروب السياسية", "تاريخ الحروب", "سجل الحروب"):
            from modules.war.political_history import open_political_history
            open_political_history(message)
            return True

    # ── أوامر إدارة المجموعة ──
    if is_feature_enabled(cid, "enable_admin"):
        if normalized_text == "مسح":
            delete_message(message)
            return True
        if normalized_text == "تثبيت":
            pin_message(message)
            return True
        if normalized_text == "لقبي":
            custom_title(message)
            return True
        if normalized_text == "تعيين اسم المجموعة":
            set_group_name(message)
            return True
        if normalized_text == "تعيين بايو المجموعة":
            set_group_bio(message)
            return True

        # ── تفعيل / إيقاف الاقتباسات التلقائية ──
        if normalized_text in ("تفعيل الاقتباسات", "إيقاف الاقتباسات"):
            from handlers.group_admin.permissions import is_admin as _is_admin
            if not _is_admin(message):
                bot.reply_to(message, "❌ هذا الأمر للمشرفين فقط.")
                return True
            enable = normalized_text == "تفعيل الاقتباسات"
            from modules.content_hub.quotes_sender import toggle_quotes
            ok = toggle_quotes(cid, enable)
            if ok:
                status = "✅ تم تفعيل الاقتباسات التلقائية." if enable else "❌ تم إيقاف الاقتباسات التلقائية."
            else:
                status = "⚠️ تعذّر تحديث الإعداد، تأكد أن المجموعة مسجّلة."
            bot.reply_to(message, status)
            return True

        # ── تفعيل / إيقاف الأذكار التلقائية ──
        if normalized_text in ("تفعيل الأذكار", "إيقاف الأذكار"):
            from handlers.group_admin.permissions import is_admin as _is_admin
            if not _is_admin(message):
                bot.reply_to(message, "❌ هذا الأمر للمشرفين فقط.")
                return True
            enable = normalized_text == "تفعيل الأذكار"
            from modules.content_hub.azkar_sender import toggle_azkar
            ok = toggle_azkar(cid, enable)
            if ok:
                status = "✅ تم تفعيل الأذكار التلقائية." if enable else "❌ تم إيقاف الأذكار التلقائية."
            else:
                status = "⚠️ تعذّر تحديث الإعداد، تأكد أن المجموعة مسجّلة."
            bot.reply_to(message, status)
            return True

        # ── تفعيل / تعطيل الهمسات ──
        if normalized_text in ("تفعيل الهمسات", "تعطيل الهمسات"):
            from handlers.group_admin.permissions import is_admin as _is_admin
            if not _is_admin(message):
                bot.reply_to(message, "❌ هذا الأمر للمشرفين فقط.")
                return True
            enable = normalized_text == "تفعيل الهمسات"
            from database.db_queries.group_features_queries import set_feature
            set_feature(cid, "enable_whispers", enable)
            status = "✅ تم تفعيل الهمسات في هذه المجموعة." if enable else "❌ تم تعطيل الهمسات في هذه المجموعة."
            bot.reply_to(message, status)
            return True

    # ── أوامر الكتم/الحظر (prefix-based) ──
    if is_feature_enabled(cid, "enable_admin"):
        from handlers.replies import commands as _punishment_cmds
        for command_name, func in _punishment_cmds.items():
            if normalized_text.startswith(command_name):
                rest = normalized_text[len(command_name):]
                if rest and not rest.startswith(" "):
                    continue
                if "عالمي" in normalized_text:
                    continue
                # تفويض التحقق الكامل لـ handle_punishment — لا نتحقق هنا
                func(message)
                return True

    # ── أوامر المطور (DEV_COMMANDS) ──
    if normalized_text in DEV_COMMANDS:
        if is_developer(message):
            cmd_info   = DEV_COMMANDS[normalized_text]
            func       = cmd_info["func"]
            needs_user = cmd_info.get("needs_user", False)
            if needs_user:
                target_uid, _ = get_target_user(message)
                if not target_uid:
                    bot.reply_to(message, "حدد المستخدم بالرد أو الايدي أو اليوزر")
                    return True
                func(message, target_uid)
            else:
                func(message)
        return True

    return False


def _send_group_link(message):
    """يرسل رابط دعوة المجموعة مع معلومات المرسل."""
    from utils.keyboards import ui_btn, build_keyboard

    cid        = message.chat.id
    user       = message.from_user
    first_name = user.first_name or ""
    uid        = user.id
    group_name = message.chat.title or "المجموعة"

    try:
        invite_link = bot.export_chat_invite_link(cid)
    except Exception:
        invite_link = None

    sender_line = f"<a href='tg://user?id={uid}'>{first_name}</a> (<code>{uid}</code>)"

    if invite_link:
        text = (
            f"🔗 <b>رابط المجموعة</b>\n\n"
            f"👤 الطالب: {sender_line}\n"
            f"👥 المجموعة: <b>{group_name}</b>\n\n"
            f"<code>{invite_link}</code>"
        )
        buttons = [ui_btn("🔗 رابط المجموعة", url=invite_link)]
        markup  = build_keyboard(buttons, [1])
    else:
        text = (
            f"⚠️ تعذّر جلب رابط المجموعة.\n\n"
            f"👤 الطالب: {sender_line}\n"
            f"👥 المجموعة: <b>{group_name}</b>\n\n"
            f"تأكد أن البوت يملك صلاحية <b>دعوة المستخدمين</b>."
        )
        markup = None

    bot.send_message(cid, text, parse_mode="HTML", reply_markup=markup)


def _set_dev_group(message):
    from core.admin import set_const
    group_id = str(message.chat.id)
    set_const("dev_group_id", group_id)
    try:
        import modules.tickets.ticket_handler as _th
        _th.DEV_GROUP_ID = int(group_id)
    except Exception:
        pass
    bot.reply_to(message,
                 f"✅ تم تعيين هذه المجموعة كجروب البوت الرئيسي\nID: <code>{group_id}</code>",
                 parse_mode="HTML")
