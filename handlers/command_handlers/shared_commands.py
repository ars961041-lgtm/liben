"""
أوامر مشتركة — تعمل في المجموعات والخاص على حد سواء.
القرآن، مركز المحتوى، التنسيق، الوقت، الإنجازات، الملف الشخصي، لوحة الإدارة، إلخ.
"""
from core.bot import bot


def handle_shared_commands(message, normalized_text: str, text: str) -> bool:
    """
    يعالج الأوامر المشتركة بين الخاص والمجموعات.
    يرجع True إذا تم التعامل مع الأمر.
    """
    from handlers.misc.time_date import today_date, today_time
    from handlers.users import send_user_profile
    from modules.quran.quran_handler import handle_quran_commands
    from modules.content_hub.hub_handler import handle_content_command
    from modules.formatting.format_handler import handle_format_command, handle_format_guide
    from modules.text_tools.replace_handler import handle_replace_command
    from handlers.group_admin.developer.admin_panel import open_admin_panel
    from handlers.group_admin.developer.dev_guide import open_dev_guide
    from handlers.command_handlers.progression_commands import (
        show_achievements, show_progress, show_influence,
        show_global_event, show_season
    )
    from modules.tickets.ticket_callbacks import handle_ticket_commands

    # ── التذاكر ──
    if handle_ticket_commands(message):
        return True

    # ── القرآن ──
    if handle_quran_commands(message):
        return True

    # ── الأذكار ──
    from modules.azkar.azkar_handler import handle_azkar_command
    if handle_azkar_command(message):
        return True

    from modules.azkar.custom_zikr import handle_custom_zikr_command
    if handle_custom_zikr_command(message):
        return True

    from modules.azkar.azkar_reminder import handle_reminder_command
    if handle_reminder_command(message):
        return True

    # ── المجلة اليومية ──
    from modules.magazine.magazine_handler import handle_magazine_command
    if handle_magazine_command(message):
        return True

    # ── دليل المميزات ──
    from handlers.features_guide import handle_features_command
    if handle_features_command(message):
        return True

    # ── /developer_gift في الخاص ──
    if normalized_text in ["/developer_gift", "developer_gift"]:
        from core.admin import is_primary_dev
        from modules.magazine.magazine_handler import open_gift_from_message
        if is_primary_dev(message.from_user.id):
            open_gift_from_message(message)
            return True

    # ── مركز المحتوى ──
    if handle_content_command(message):
        return True

    # ── إدارة ربط القنوات (مطورون فقط) ──
    from modules.content_hub.channel_admin import handle_channel_admin_command
    if handle_channel_admin_command(message):
        return True

    # ── التنسيق والاستبدال ──
    if normalized_text == "تنسيق":
        handle_format_command(message)
        return True
    if normalized_text in ["شرح تنسيق", "دليل التنسيق"]:
        handle_format_guide(message)
        return True
    if text.startswith("تعديل "):
        handle_replace_command(message)
        return True

    # ── الوقت والتاريخ ──
    if normalized_text == "اليوم":
        today_date(message)
        return True
    if normalized_text in ["كم الساعة", "كم الساعه", "الساعة كم", "الساعه كم", "الوقت"]:
        today_time(message)
        return True

    # ── لوحة الإدارة ──
    if normalized_text in ["لوحة الإدارة", "لوحة الادارة", "لوحة المطور", "/admin"]:
        open_admin_panel(message)
        return True
    if normalized_text in ["شرح المطور", "دليل المطور"]:
        open_dev_guide(message)
        return True

    # ── الإنجازات والتقدم والنفوذ والمواسم ──
    if normalized_text in ["إنجازاتي", "انجازاتي", "الإنجازات"]:
        show_achievements(message)
        return True
    if normalized_text in ["تقدمي", "تقدم"]:
        show_progress(message)
        return True
    if normalized_text in ["نفوذي", "تأثيري"]:
        show_influence(message)
        return True
    if normalized_text in ["الأحداث", "حدث", "الاحداث"]:
        show_global_event(message)
        return True
    if normalized_text in ["الموسم", "موسم"]:
        show_season(message)
        return True

    # ── الملف الشخصي ──
    if text in ["عني", "ايدي", "معلوماتي"] or text.startswith("ايدي"):
        send_user_profile(message)
        return True
    if normalized_text in ["عنه", "معلوماته"]:
        send_user_profile(message)
        return True

    # ── التصويت ──
    if normalized_text in ["إنشاء تصويت", "انشاء تصويت", "بناء تصويت"]:
        from modules.polls import open_poll_creator
        open_poll_creator(message)
        return True
    if text == "لوحة التصويت":
        from modules.polls import handle_poll_control_panel
        return handle_poll_control_panel(message)

    return False
