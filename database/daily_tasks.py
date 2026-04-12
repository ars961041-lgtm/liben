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
def run_city_progression():
    """Daily population growth, satisfaction drift, and XP awards for all cities."""
    if not _table_exists("cities"):
        return
    _safe(_do_city_progression)

def _do_city_progression():
    from modules.city.city_stats import run_city_progression_tick
    run_city_progression_tick()


@register_daily
def run_city_simulation():
    """Daily rebellion, smart migration, population upkeep, internal economy."""
    if not _table_exists("cities"):
        return
    _safe(_do_city_simulation)

def _do_city_simulation():
    from modules.city.city_simulation import run_simulation_tick
    run_simulation_tick()


@register_daily
def expire_government_decisions():
    """Expire old government decisions."""
    _safe(_do_expire_decisions)

def _do_expire_decisions():
    from modules.city.government_decisions import expire_old_decisions
    expire_old_decisions()


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


@register_daily
def check_richest_player_change():
    """Publishes a news post if the richest player has changed since yesterday."""
    _safe(_do_richest_check)

_last_richest_id: int = 0

def _do_richest_check():
    global _last_richest_id
    from database.db_queries.tops_queries import get_top_richest
    from modules.magazine.news_generator import on_richest_player_changed
    top = get_top_richest(1)
    if not top:
        return
    player = top[0]
    if player["id"] != _last_richest_id:
        _last_richest_id = player["id"]
        on_richest_player_changed(player["name"], float(player["value"]))


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
def send_azkar():
    """Sends periodic azkar to groups where azkar_enabled=1."""
    _safe(_do_send_azkar)

def _do_send_azkar():
    from modules.content_hub.azkar_sender import send_periodic_azkar
    send_periodic_azkar()


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


# ══════════════════════════════════════════════════════════════════
# ── POLITICAL WAR — INTERVAL JOB ─────────────────────────────────
# ══════════════════════════════════════════════════════════════════

@register_interval
def close_expired_polls():
    """يُغلق التصويتات التي انتهى وقتها كل 5 دقائق — بديل موثوق عن threading.Timer."""
    if not _table_exists("polls"):
        return
    _safe(_do_close_expired_polls)

def _do_close_expired_polls():
    from database.db_queries.polls_queries import get_expired_polls, close_poll
    from modules.polls.poll_closer import close_expired_poll
    for poll in get_expired_polls():
        try:
            close_expired_poll(poll)
        except Exception as e:
            print(f"[polls] خطأ في إغلاق تصويت #{poll['id']}: {e}")


@register_interval
def resolve_expired_political_war_votes():
    """يُعالج حروب التصويت التي انتهت مدتها كل 5 دقائق."""
    if not _table_exists("political_wars"):
        return
    _safe(_do_resolve_political_wars)

def _do_resolve_political_wars():
    from database.db_queries.political_war_queries import (
        get_voting_wars_expired, get_preparation_wars_ready,
    )
    from modules.war.services.political_war_service import resolve_voting, resolve_preparation

    # معالجة التصويت المنتهي
    for war in get_voting_wars_expired():
        try:
            success, msg = resolve_voting(war["id"])
            print(f"[political_war] تصويت حرب #{war['id']}: {msg}")
        except Exception as e:
            print(f"[political_war] خطأ في حرب #{war['id']}: {e}")

    # معالجة التحضير المنتهي → بدء الحرب
    for war in get_preparation_wars_ready():
        try:
            success, msg = resolve_preparation(war["id"])
            print(f"[political_war] تحضير حرب #{war['id']}: {msg}")
        except Exception as e:
            print(f"[political_war] خطأ في تحضير حرب #{war['id']}: {e}")


# ══════════════════════════════════════════════════════════════════
# ── ALLIANCE GOVERNANCE — DAILY + WEEKLY JOBS ────────────────────
# ══════════════════════════════════════════════════════════════════

@register_daily
def collect_alliance_taxes_job():
    """يجمع ضرائب التحالفات يومياً."""
    if not _table_exists("alliance_tax_config"):
        return
    _safe(_do_collect_taxes)

def _do_collect_taxes():
    from database.db_queries.alliance_governance_queries import collect_alliance_taxes
    collect_alliance_taxes()
    print("[alliance_governance] تم جمع ضرائب التحالفات.")


@register_daily
def refresh_alliance_titles_job():
    """يُعيد حساب الألقاب الأسبوعية (يُشغَّل يومياً، يتحقق داخلياً من اليوم)."""
    if not _table_exists("alliance_titles"):
        return
    _safe(_do_refresh_titles)

def _do_refresh_titles():
    from database.db_queries.alliance_governance_queries import refresh_all_titles
    refresh_all_titles()
    print("[alliance_governance] تم تحديث ألقاب التحالفات.")


@register_daily
def alliance_reputation_decay_job():
    """يُطبّق خصم السمعة الأسبوعي على التحالفات الخاملة."""
    if not _table_exists("alliance_reputation"):
        return
    _safe(_do_reputation_decay)

def _do_reputation_decay():
    from database.connection import get_db_conn
    from database.db_queries.alliance_governance_queries import update_alliance_reputation
    conn = get_db_conn()
    cursor = conn.cursor()
    # التحالفات التي لم تشارك في أي حرب خلال 7 أيام
    week_ago = int(__import__("time").time()) - 7 * 86400
    cursor.execute("""
        SELECT DISTINCT a.id FROM alliances a
        LEFT JOIN political_war_members pwm ON pwm.country_id IN (
            SELECT country_id FROM alliance_members WHERE alliance_id = a.id
        ) AND pwm.joined_at > ?
        WHERE pwm.war_id IS NULL
    """, (week_ago,))
    inactive = cursor.fetchall()
    for (aid,) in inactive:
        update_alliance_reputation(aid, "weekly_decay", "خمول أسبوعي")


# ══════════════════════════════════════════════════════════════════
# ── ALLIANCE DIPLOMACY — DAILY JOBS ──────────────────────────────
# ══════════════════════════════════════════════════════════════════

@register_daily
def expire_treaties_job():
    """يُنهي المعاهدات المنتهية الصلاحية يومياً."""
    if not _table_exists("alliance_treaties"):
        return
    _safe(_do_expire_treaties)

def _do_expire_treaties():
    from database.db_queries.alliance_diplomacy_queries import expire_old_treaties
    expire_old_treaties()


@register_daily
def decay_influence_job():
    """يُطبّق تناقص النفوذ اليومي."""
    if not _table_exists("alliance_influence"):
        return
    _safe(_do_decay_influence)

def _do_decay_influence():
    from database.db_queries.alliance_diplomacy_queries import decay_influence
    decay_influence()


@register_daily
def apply_balance_rules_job():
    """يُطبّق قواعد التوازن على جميع التحالفات يومياً."""
    if not _table_exists("alliance_balance_log"):
        return
    _safe(_do_balance_rules)

def _do_balance_rules():
    from database.connection import get_db_conn
    from database.db_queries.alliance_diplomacy_queries import apply_balance_rules
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM alliances")
    for (aid,) in cursor.fetchall():
        try:
            apply_balance_rules(aid)
        except Exception:
            pass


@register_interval
def compute_intelligence_job():
    """يُحدّث بيانات الاستخبارات لجميع التحالفات كل 5 دقائق."""
    if not _table_exists("alliance_intelligence"):
        return
    _safe(_do_compute_intel)

def _do_compute_intel():
    from database.connection import get_db_conn
    from database.db_queries.alliance_diplomacy_queries import compute_intelligence
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM alliances")
    for (aid,) in cursor.fetchall():
        try:
            compute_intelligence(aid)
        except Exception:
            pass


@register_daily
def loyalty_decay_job():
    """
    يُطبّق تناقص الولاء اليومي على جميع أعضاء التحالفات.

    القواعد:
      - -1 يومياً لكل عضو (خمول عام)
      - -2 إضافية إذا تجاهل العضو حرباً في آخر 24 ساعة
      - لا تنخفض عن 0
    """
    if not _table_exists("alliance_loyalty"):
        return
    _safe(_do_loyalty_decay)

def _do_loyalty_decay():
    from database.connection import get_db_conn
    from database.db_queries.political_war_queries import update_loyalty

    conn   = get_db_conn()
    cursor = conn.cursor()

    # جلب جميع سجلات الولاء
    cursor.execute("""
        SELECT al.alliance_id, al.country_id, al.user_id, al.loyalty_score
        FROM alliance_loyalty al
    """)
    members = cursor.fetchall()

    # الدول التي تجاهلت حرباً في آخر 24 ساعة
    # (سُجّل لها حدث 'voted_neutral' أو لم تصوّت في حرب انتهت خلال 24 ساعة)
    day_ago = int(__import__("time").time()) - 86400
    cursor.execute("""
        SELECT DISTINCT pl.country_id
        FROM political_war_log pl
        JOIN political_wars pw ON pl.war_id = pw.id
        WHERE pl.event_type IN ('voted_neutral')
          AND pl.created_at >= ?
        UNION
        SELECT DISTINCT am.country_id
        FROM alliance_members am
        JOIN political_wars pw ON (
            pw.attacker_alliance_id = am.alliance_id
            OR pw.defender_alliance_id = am.alliance_id
        )
        WHERE pw.status IN ('ended','cancelled')
          AND pw.ended_at >= ?
          AND am.country_id NOT IN (
              SELECT country_id FROM political_war_members
              WHERE war_id = pw.id
          )
    """, (day_ago, day_ago))
    ignored_countries = {row[0] for row in cursor.fetchall()}

    for m in members:
        aid        = m["alliance_id"]
        cid        = m["country_id"]
        uid        = m["user_id"]
        score      = float(m["loyalty_score"])

        if score <= 0:
            continue   # لا داعي لتحديث من هو عند الصفر

        # -1 يومياً للجميع
        delta = -1.0
        # -2 إضافية لمن تجاهل حرباً
        if cid in ignored_countries:
            delta -= 2.0

        update_loyalty(aid, cid, uid, delta)


@register_daily
def recalc_influence_job():
    """يُعيد حساب النفوذ بناءً على فارق القوة يومياً."""
    if not _table_exists("alliance_influence"):
        return
    _safe(_do_recalc_influence)

def _do_recalc_influence():
    from database.connection import get_db_conn
    from modules.alliances.diplomacy_service import recalc_influence_from_power
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM alliances")
    for (aid,) in cursor.fetchall():
        try:
            recalc_influence_from_power(aid)
        except Exception:
            pass
