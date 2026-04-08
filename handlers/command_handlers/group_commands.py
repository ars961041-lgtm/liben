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

    # ── لوحة تحكم ميزات المجموعة ──
    if normalized_text == "الأوامر":
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
        if normalized_text in ["لوحة المطور", "dev panel"]:
            from handlers.group_admin.developer.dev_control_panel import open_developer_panel
            open_developer_panel(message)
            return True
        if normalized_text in ["إدارة الأذكار", "ادارة الأذكار", "azkar admin"]:
            from modules.azkar.azkar_handler import open_azkar_admin
            open_azkar_admin(message)
            return True
        if normalized_text in ["إنشاء منشور", "انشاء منشور", "new post"]:
            from modules.post_creator import open_post_creator
            open_post_creator(message)
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
    if is_feature_enabled(cid, "feat_games"):
        if bank_commands(message):
            return True

    # ── الألعاب ──
    if is_feature_enabled(cid, "feat_games"):
        if games_command(message):
            return True
        if entertainment_games_command(message):
            return True

    # ── التوبات ──
    if is_feature_enabled(cid, "feat_games"):
        if top_commands(message):
            return True

    # ── الدولة والمدن ──
    if is_feature_enabled(cid, "feat_games"):
        if country_commands(message):   return True
        if city_commands(message):      return True
        if daily_tasks_commands(message): return True
        if normalized_text in ["دخل", "دخل مدينتي", "جمع الدخل", "اقتصادي"]:
            collect_city_income(message)
            return True

    # ── التحالفات ──
    if is_feature_enabled(cid, "feat_games"):
        if alliance_commands(message):
            return True

    # ── الحرب ──
    if is_feature_enabled(cid, "feat_games"):
        if handle_war_text_commands(message):
            return True

    # ── أوامر إدارة المجموعة ──
    if is_feature_enabled(cid, "feat_admin"):
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

    # ── أوامر الكتم/الحظر (prefix-based) ──
    if is_feature_enabled(cid, "feat_admin"):
        from handlers.replies import commands as _punishment_cmds
        for command_name, func in _punishment_cmds.items():
            if normalized_text.startswith(command_name):
                rest = normalized_text[len(command_name):]
                if rest and not rest.startswith(" "):
                    continue
                if "عالمي" in normalized_text:
                    continue
                target_uid, _ = get_target_user(message)
                if not target_uid:
                    bot.reply_to(message, "❌ حدد المستخدم بالرد أو الآيدي أو اليوزر.")
                    return True
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
