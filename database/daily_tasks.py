"""
database/daily_tasks.py

Registers all daily and interval jobs with the unified scheduler.
No threads are created here — core/scheduler.py owns the threads.

Daily jobs  (midnight Yemen time):
  - reset_daily_tasks      — clear stale tasks/pool from previous day
  - assign_tasks_to_all_cities — pre-generate tasks for all cities
  - refresh_city_resources — collect income for all countries
  - run_maintenance_for_all — army maintenance deductions
  - check_and_end_season   — end season if expired
  - delete_rejected_invites — clean up old country invites
  - trigger_global_event   — 30% chance to fire a world event

Interval jobs (every 5 minutes):
  - fire_azkar_reminders   — send due azkar reminders
  - fire_khatmah_reminders — send due khatmah reminders
  - check_global_event     — hourly event trigger (self-throttled)
"""

import time
from database.connection import get_db_conn
from core.scheduler import register_daily, register_interval


# ══════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════

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


def _safe(fn):
    """Wraps a job so missing tables are silently skipped."""
    try:
        fn()
    except Exception as e:
        err = str(e)
        if "no such table" in err or "no such column" in err:
            print(f"⚠️ [daily_tasks] تجاهل {fn.__name__} (جدول/عمود غير موجود)")
        else:
            import traceback
            print(f"❌ [daily_tasks] خطأ في {fn.__name__}: {e}")
            traceback.print_exc()


# ══════════════════════════════════════════════════════════════════
# ── DAILY JOBS ────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════

@register_daily
def reset_daily_tasks():
    if not _table_exists("daily_tasks"):
        return
    _safe(_do_reset_daily_tasks)

def _do_reset_daily_tasks():
    from database.db_queries.daily_tasks_queries import reset_daily_tasks as _reset
    _reset()


@register_daily
def assign_tasks_to_all_cities():
    if not _table_exists("cities") or not _table_exists("daily_tasks"):
        return
    _safe(_do_assign_tasks)

def _do_assign_tasks():
    from database.db_queries.daily_tasks_queries import generate_daily_tasks_for_city
    conn   = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM cities")
    for city in cursor.fetchall():
        generate_daily_tasks_for_city(city["id"])


@register_daily
def refresh_city_resources():
    if not _table_exists("city_budget") or not _table_exists("countries"):
        return
    _safe(_do_refresh_resources)

def _do_refresh_resources():
    from modules.economy.economy_service import collect_income_for_all
    collect_income_for_all()


@register_daily
def run_army_maintenance():
    if not _table_exists("army_maintenance"):
        return
    _safe(_do_maintenance)

def _do_maintenance():
    from modules.war.maintenance_service import run_maintenance_for_all
    run_maintenance_for_all()


@register_daily
def check_season():
    if not _table_exists("seasons"):
        return
    _safe(_do_check_season)

def _do_check_season():
    from modules.progression.seasons import check_and_end_season
    check_and_end_season()


@register_daily
def delete_old_invites():
    if not _table_exists("country_invites"):
        return
    _safe(_do_delete_invites)

def _do_delete_invites():
    from database.db_queries.countries_queries import delete_rejected_invites
    delete_rejected_invites()


@register_daily
def trigger_daily_global_event():
    """30% chance to fire a world event at midnight."""
    if not _table_exists("global_events"):
        return
    _safe(_do_daily_event)

def _do_daily_event():
    import random
    if random.random() < 0.30:
        from modules.progression.global_events import trigger_random_event
        trigger_random_event()


@register_daily
def publish_magazine_rankings():
    """Publishes weekly rankings on Monday and monthly rankings on the 1st."""
    _safe(_do_weekly_rankings)
    _safe(_do_monthly_rankings)

def _do_weekly_rankings():
    from modules.magazine.rankings import maybe_publish_weekly
    maybe_publish_weekly()

def _do_monthly_rankings():
    from modules.magazine.rankings import maybe_publish_monthly
    maybe_publish_monthly()


# ══════════════════════════════════════════════════════════════════
# ── INTERVAL JOBS (every 5 minutes) ──────────────────────────────
# ══════════════════════════════════════════════════════════════════

@register_interval
def send_quotes():
    """Sends periodic quotes to groups where quotes_enabled=1."""
    _safe(_do_send_quotes)

def _do_send_quotes():
    from modules.content_hub.quotes_sender import send_periodic_quotes
    send_periodic_quotes()


@register_interval
def fire_azkar_reminders():
    """Sends azkar reminders whose local time matches now (±5 min window)."""
    if not _table_exists("azkar_reminders"):
        return
    _safe(_do_azkar_reminders)

def _do_azkar_reminders():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    from database.db_queries.azkar_queries import get_due_reminders
    from modules.azkar.azkar_reminder import _fire_reminder
    for r in get_due_reminders(now.hour, now.minute):
        _fire_reminder(r)


@register_interval
def fire_khatmah_reminders():
    """Sends khatmah reminders whose local time matches now."""
    if not _table_exists("khatma_reminders"):
        return
    _safe(_do_khatmah_reminders)

def _do_khatmah_reminders():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    from modules.quran.khatmah_reminder import fire_due_reminders
    fire_due_reminders(now.hour, now.minute)


# ── Global event checker — self-throttled to once per hour ───────
_last_event_check: float = 0.0
_EVENT_CHECK_INTERVAL = 3600   # 1 hour

@register_interval
def check_global_event():
    """Checks whether to trigger a new global event. Runs at most once per hour."""
    global _last_event_check
    if not _table_exists("global_events"):
        return
    now = time.time()
    if now - _last_event_check < _EVENT_CHECK_INTERVAL:
        return
    _last_event_check = now
    _safe(_do_check_event)

def _do_check_event():
    import random
    if random.random() < 0.30:
        from modules.progression.global_events import trigger_random_event
        trigger_random_event()


# ══════════════════════════════════════════════════════════════════
# ── WHISPERS CLEANUP ──────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════

@register_daily
def cleanup_old_whispers():
    """يحذف الهمسات غير المقروءة الأقدم من 3 أيام، والمقروءة الأقدم من يوم."""
    if not _table_exists("whispers"):
        return
    _safe(_do_cleanup_whispers)

def _do_cleanup_whispers():
    from database.db_queries.whispers_queries import delete_old_whispers, delete_read_whispers
    delete_old_whispers(days=1)    # حذف الهمسات غير المقروءة بعد 24 ساعة
    delete_read_whispers(days=1)   # حذف الهمسات المقروءة بعد 24 ساعة


# ══════════════════════════════════════════════════════════════════
# ── SURAH AL-KAHF FRIDAY REMINDER ────────────────────────────────
# ══════════════════════════════════════════════════════════════════

_kahf_last_sent_date: str = ""   # "YYYY-MM-DD" of last Friday sent

_KAHF_MESSAGE = (
    "📖 <b>تذكير بفضل سورة الكهف</b>\n"
    "─────────────────────\n\n"
    "عن أبي سعيد الخدري رضي الله عنه أن النبي ﷺ قال:\n"
    "<i>«مَن قرأ سورةَ الكهفِ في يومِ الجمعةِ، أضاءَ له من النورِ ما بينَ الجمعتين»</i>\n\n"
    "📌 اكتب <b>قراءة سورة</b> واختر سورة الكهف لقراءتها والحصول على الأجر."
)

@register_interval
def send_kahf_friday_reminder():
    """
    يرسل تذكير سورة الكهف كل جمعة الساعة 7:00 صباحاً بتوقيت اليمن.
    يُشغَّل من المُجدوِل كل 5 دقائق — يُرسَل مرة واحدة فقط في الجمعة.
    """
    global _kahf_last_sent_date
    from datetime import datetime, timezone, timedelta

    _YEMEN_TZ = timezone(timedelta(hours=3))
    now = datetime.now(_YEMEN_TZ)

    # الجمعة = weekday() == 4، الساعة 7 صباحاً
    if now.weekday() != 4 or now.hour != 7:
        return

    today = now.strftime("%Y-%m-%d")
    if _kahf_last_sent_date == today:
        return   # أُرسِل بالفعل هذه الجمعة

    _kahf_last_sent_date = today
    _safe(_do_send_kahf_reminder)

def _do_send_kahf_reminder():
    from core.bot import bot
    conn   = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT group_id FROM groups")
    groups = [row["group_id"] for row in cursor.fetchall()]

    sent = 0
    for tg_group_id in groups:
        try:
            bot.send_message(tg_group_id, _KAHF_MESSAGE, parse_mode="HTML")
            sent += 1
        except Exception:
            pass   # المجموعة حجبت البوت أو حُذفت — تجاهل صامت

    print(f"[KahfReminder] أُرسِل تذكير الكهف لـ {sent} مجموعة")


# ══════════════════════════════════════════════════════════════════
# Public entry point — called once from main.py
# ══════════════════════════════════════════════════════════════════

def run_daily_tasks():
    """
    Called once at bot startup from main.py.
    The @register_daily / @register_interval decorators above have already
    registered all jobs with the scheduler when this module was imported.
    This function just confirms startup and runs the first daily cycle
    immediately so tasks are ready on day-one without waiting for midnight.
    """
    print("[Scheduler] Daily and interval jobs registered.")

    # Seed default content into content DB if tables are empty
    try:
        from modules.content_hub.seed_content import seed_default_content
        seed_default_content()
    except Exception as e:
        print(f"[ContentSeed] {e}")

    # Run daily jobs once immediately at startup so the bot is ready
    # without waiting for the first midnight.
    _safe(reset_daily_tasks)
    _safe(assign_tasks_to_all_cities)
    _safe(refresh_city_resources)
    _safe(check_season)
    _safe(delete_old_invites)
    _safe(cleanup_old_whispers)
