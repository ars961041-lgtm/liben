import threading
from database.connection import get_db_conn


def _table_exists(name: str) -> bool:
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
        )
        return cursor.fetchone() is not None
    except Exception:
        return False


def update_daily_bonuses():
    """يمكن إضافة أي تحديثات يومية للمكافآت هنا"""
    pass


def refresh_city_resources():
    """تحديث الموارد اليومية لكل المدن — جمع الدخل وتطبيقه على أرصدة اللاعبين"""
    if not _table_exists("city_budget") or not _table_exists("countries"):
        return
    try:
        from modules.economy.economy_service import collect_income_for_all
        collect_income_for_all()
    except Exception as e:
        print(f"[Economy] فشل جمع الدخل اليومي: {e}")


def assign_tasks_to_all_users():
    """تعيين المهام اليومية لجميع المستخدمين"""
    if not _table_exists("users") or not _table_exists("cities") or not _table_exists("daily_tasks"):
        return
    try:
        from database.db_queries.daily_tasks_queries import generate_daily_tasks_for_city
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users")
        users = cursor.fetchall()
        for user in users:
            user_id = user["id"]
            cursor.execute("SELECT id FROM cities WHERE owner_id=? LIMIT 1", (user_id,))
            city = cursor.fetchone()
            if city:
                generate_daily_tasks_for_city(user_id, city["id"])
    except Exception as e:
        print(f"[assign_tasks] {e}")


def delete_old_invites():
    """حذف الدعوات المرفوضة"""
    if not _table_exists("country_invites"):
        return
    try:
        from database.db_queries.countries_queries import delete_rejected_invites
        delete_rejected_invites()
    except Exception as e:
        print(f"[delete_invites] {e}")


def safe_execute(task):
    try:
        task()
    except Exception as e:
        err = str(e)
        if "no such table" in err or "no such column" in err:
            print(f"⚠️ تم تجاهل {task.__name__} (الجدول/العمود غير موجود)")
        else:
            import traceback
            print(f"❌ خطأ في {task.__name__}: {e}")
            traceback.print_exc()


def run_daily_tasks():
    """تشغيل كل المهام اليومية مرة كل 24 ساعة"""
    tasks = [
        delete_old_invites,
        update_daily_bonuses,
        refresh_city_resources,
        assign_tasks_to_all_users,
        _run_maintenance,
        _check_season,
        _trigger_global_event,
    ]

    for task in tasks:
        safe_execute(task)

    # جدولة التنفيذ التالي بعد 24 ساعة
    threading.Timer(86400, run_daily_tasks).start()


def _run_maintenance():
    """معالجة صيانة الجيش لكل الدول"""
    if not _table_exists("army_maintenance"):
        return
    try:
        from modules.war.maintenance_service import run_maintenance_for_all
        run_maintenance_for_all()
    except Exception as e:
        print(f"[Maintenance] {e}")


def _check_season():
    """فحص وإنهاء الموسم إذا انتهى"""
    if not _table_exists("seasons"):
        return
    try:
        from modules.progression.seasons import check_and_end_season
        check_and_end_season()
    except Exception as e:
        print(f"[Seasons] {e}")


def _trigger_global_event():
    """فرصة 30% لإطلاق حدث عالمي يومي"""
    if not _table_exists("global_events"):
        return
    try:
        import random
        if random.random() < 0.30:
            from modules.progression.global_events import trigger_random_event
            trigger_random_event()
    except Exception as e:
        print(f"[GlobalEvents daily] {e}")


# ─── تشغيل عند بدء البوت ───
run_daily_tasks()

# ─── مدقق الأحداث العالمية الدوري ───
try:
    if _table_exists("global_events"):
        from modules.progression.global_events import schedule_event_checker
        schedule_event_checker()
except Exception as e:
    print(f"[GlobalEvents] فشل التشغيل: {e}")

# ─── مُجدوِل تذكيرات الأذكار ───
try:
    from modules.azkar.azkar_reminder import start_reminder_scheduler
    start_reminder_scheduler()
except Exception as e:
    print(f"[AzkarReminder] فشل التشغيل: {e}")
