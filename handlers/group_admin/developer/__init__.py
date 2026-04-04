# developer/init.py
from handlers.group_admin.admin_commands import reset_db, update_db
from handlers.group_admin.restrictions import clear_group_log, display_user_history
from handlers.group_admin.developer.dev_panel import open_dev_panel, handle_dev_input
from handlers.group_admin.developer import dev_troop_panel  # registers @register_action handlers
from handlers.group_admin.developer.dev_control_panel import open_developer_panel, handle_developer_input
from .send_preformatted import send_preformatted

DEV_COMMANDS = {
    "مسح قاعدة البيانات":  {"func": reset_db,            "needs_user": False},
    "تحديث قاعدة البيانات":{"func": update_db,            "needs_user": False},
    "شرح الازرار":          {"func": send_preformatted,    "needs_user": False},
    "سجل المستخدم":         {"func": display_user_history, "needs_user": True},
    "مسح السجل":            {"func": clear_group_log,      "needs_user": False},
    "متجر المطور":          {"func": open_dev_panel,       "needs_user": False},
    "لوحة المطور":          {"func": open_developer_panel, "needs_user": False},
}