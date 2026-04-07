"""
أوامر الخاص فقط (PM).
"""
from core.bot import bot


def handle_private_commands(message) -> bool:
    """
    يعالج الأوامر المخصصة للخاص فقط.
    يرجع True إذا تم التعامل مع الأمر.
    """
    # متابعة التذاكر المفتوحة
    from modules.tickets.ticket_handler import handle_user_followup
    if handle_user_followup(message):
        return True

    return False
