from database.db_schema.banks import create_banks_tables
from database.db_schema.user_timezone import create_user_timezone_table
from database.db_schema.daily_tasks import create_daily_tasks_pool_table
from .users import create_users_table
from .groups import create_groups_tables
from .countries import create_countries_tables
from .economy import create_economy_tables
from .assets import create_asset_tables
from .war import create_war_tables
from .alliances import create_alliance_tables
from .advanced_war import create_advanced_war_tables
from .live_battle import create_live_battle_tables
from .war_economy import create_war_economy_tables
from .war_balance import create_war_balance_tables
from .war_extensions import create_war_extension_tables
from .progression import create_progression_tables

def create_all_tables():
    # users أولاً — جميع الجداول الأخرى تعتمد على users(user_id) كـ FK
    create_users_table()

    # admin_system بعد users مباشرةً لأن bot_developers يرجع إلى users(user_id)
    from database.db_schema.admin_system import create_admin_tables
    create_admin_tables()
    create_user_timezone_table()
    create_banks_tables()
    create_groups_tables()
    create_economy_tables()
    create_countries_tables()
    create_asset_tables()
    create_war_tables()
    create_alliance_tables()
    create_advanced_war_tables()
    create_live_battle_tables()
    create_war_economy_tables()
    create_war_balance_tables()
    create_war_extension_tables()
    create_progression_tables()
    # daily_tasks آخراً لأنه يعتمد على cities(id) كـ FK
    create_daily_tasks_pool_table()

    from modules.tickets.ticket_db import create_ticket_tables
    create_ticket_tables()

    from modules.magazine.magazine_db import create_magazine_tables
    create_magazine_tables()

    from database.db_schema.azkar import create_azkar_tables
    create_azkar_tables()

    from modules.azkar.seed_azkar import seed as seed_azkar
    seed_azkar()

    from modules.rules.rules_db import create_rules_table
    create_rules_table()

    from modules.quran.quran_db import create_tables as create_quran_tables
    create_quran_tables()

    from database.db_schema.whispers import create_whispers_table
    create_whispers_table()

    # تسجيل معالجات أزرار الهمسات
    import modules.whispers.whisper_handler  # noqa: F401 — registers @register_action

    print("✅ تم إنشاء جميع جداول قاعدة البيانات بنجاح.")