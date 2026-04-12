"""
استعلامات نظام التصويت المتقدم.
Race-condition safe: كل عملية تصويت تستخدم BEGIN IMMEDIATE transaction.
votes_count محفوظ في poll_options كـ denormalized counter للأداء.
"""
import time
import threading
from ..connection import get_db_conn

# per-poll lock to serialize concurrent votes on the same poll
_vote_locks: dict[int, threading.Lock] = {}
_vote_locks_meta = threading.Lock()


def _get_vote_lock(poll_id: int) -> threading.Lock:
    with _vote_locks_meta:
        if poll_id not in _vote_locks:
            _vote_locks[poll_id] = threading.Lock()
        return _vote_locks[poll_id]


def _err(fn, e):
    print(f"Error in {fn}: {e}")


# ══════════════════════════════════════════
# إنشاء / تحديث
# ══════════════════════════════════════════

def create_poll(chat_id: int, question: str, poll_type: str,
                allow_change: bool, is_hidden: bool, created_by: int,
                question_media_id: str = None, question_media_type: str = None,
                description: str = None,
                description_media_id: str = None, description_media_type: str = None,
                end_time: int = None,
                max_vote_changes: int = 0,
                lock_before_end: int = 0,
                show_voters: bool = False) -> int | None:
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO polls
                (chat_id, question, question_media_id, question_media_type,
                 description, description_media_id, description_media_type,
                 poll_type, allow_change, max_vote_changes, lock_before_end,
                 is_hidden, show_voters, end_time, created_by, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (chat_id, question, question_media_id, question_media_type,
              description, description_media_id, description_media_type,
              poll_type, int(allow_change), max_vote_changes, lock_before_end,
              int(is_hidden), int(show_voters),
              end_time, created_by, int(time.time())))
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        _err("create_poll", e)
        return None


def add_poll_option(poll_id: int, text: str) -> int | None:
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO poll_options (poll_id, text) VALUES (?,?)",
            (poll_id, text)
        )
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        _err("add_poll_option", e)
        return None


def set_poll_message_id(poll_id: int, message_id: int):
    try:
        conn = get_db_conn()
        conn.execute("UPDATE polls SET message_id=? WHERE id=?", (message_id, poll_id))
        conn.commit()
    except Exception as e:
        _err("set_poll_message_id", e)


def close_poll(poll_id: int):
    try:
        conn = get_db_conn()
        conn.execute("UPDATE polls SET is_closed=1 WHERE id=?", (poll_id,))
        conn.commit()
    except Exception as e:
        _err("close_poll", e)


def reopen_poll(poll_id: int):
    try:
        conn = get_db_conn()
        conn.execute("UPDATE polls SET is_closed=0 WHERE id=?", (poll_id,))
        conn.commit()
    except Exception as e:
        _err("reopen_poll", e)


def delete_poll(poll_id: int):
    try:
        conn = get_db_conn()
        conn.execute("DELETE FROM polls WHERE id=?", (poll_id,))
        conn.commit()
    except Exception as e:
        _err("delete_poll", e)


def extend_poll_time(poll_id: int, extra_seconds: int):
    try:
        conn = get_db_conn()
        poll = get_poll(poll_id)
        if not poll:
            return
        base    = poll["end_time"] or int(time.time())
        new_end = base + extra_seconds
        conn.execute("UPDATE polls SET end_time=?, is_closed=0 WHERE id=?", (new_end, poll_id))
        conn.commit()
    except Exception as e:
        _err("extend_poll_time", e)


# ══════════════════════════════════════════
# قراءة
# ══════════════════════════════════════════

def get_poll(poll_id: int) -> dict | None:
    try:
        conn = get_db_conn()
        row = conn.execute("SELECT * FROM polls WHERE id=?", (poll_id,)).fetchone()
        return dict(row) if row else None
    except Exception as e:
        _err("get_poll", e)
        return None


def get_poll_by_message(chat_id: int, message_id: int) -> dict | None:
    try:
        conn = get_db_conn()
        row = conn.execute(
            "SELECT * FROM polls WHERE chat_id=? AND message_id=?",
            (chat_id, message_id)
        ).fetchone()
        return dict(row) if row else None
    except Exception as e:
        _err("get_poll_by_message", e)
        return None


def get_poll_options(poll_id: int) -> list[dict]:
    """يرجع الخيارات مع votes_count المحفوظ — لا حاجة لـ COUNT(*) في كل مرة."""
    try:
        conn = get_db_conn()
        rows = conn.execute(
            "SELECT * FROM poll_options WHERE poll_id=? ORDER BY id", (poll_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        _err("get_poll_options", e)
        return []


def get_user_vote(poll_id: int, user_id: int) -> dict | None:
    try:
        conn = get_db_conn()
        row = conn.execute(
            "SELECT * FROM poll_votes WHERE poll_id=? AND user_id=?",
            (poll_id, user_id)
        ).fetchone()
        return dict(row) if row else None
    except Exception as e:
        _err("get_user_vote", e)
        return None


def get_total_votes(poll_id: int) -> int:
    """يحسب المجموع من votes_count المخزّن — O(options) بدلاً من COUNT(*)."""
    try:
        conn = get_db_conn()
        row = conn.execute(
            "SELECT COALESCE(SUM(votes_count), 0) as t FROM poll_options WHERE poll_id=?",
            (poll_id,)
        ).fetchone()
        return int(row["t"]) if row else 0
    except Exception as e:
        _err("get_total_votes", e)
        return 0


def get_option_voters(option_id: int, limit: int = 20) -> list[int]:
    """يرجع user_id الذين صوتوا لخيار معين — مع LIMIT لتجنب الاستعلامات الثقيلة."""
    try:
        conn = get_db_conn()
        rows = conn.execute(
            "SELECT user_id FROM poll_votes WHERE option_id=? ORDER BY voted_at LIMIT ?",
            (option_id, limit)
        ).fetchall()
        return [r["user_id"] for r in rows]
    except Exception as e:
        _err("get_option_voters", e)
        return []


def get_latest_poll_by_creator(chat_id: int, user_id: int) -> dict | None:
    """يرجع آخر تصويت أنشأه المستخدم في هذه المحادثة."""
    try:
        conn = get_db_conn()
        row = conn.execute(
            "SELECT * FROM polls WHERE chat_id=? AND created_by=? ORDER BY id DESC LIMIT 1",
            (chat_id, user_id)
        ).fetchone()
        return dict(row) if row else None
    except Exception as e:
        _err("get_latest_poll_by_creator", e)
        return None


def get_expired_polls() -> list[dict]:   
    """يرجع التصويتات التي انتهى وقتها ولم تُغلق — يُستدعى من المُجدوِل."""
    try:
        now  = int(time.time())
        conn = get_db_conn()
        rows = conn.execute(
            "SELECT * FROM polls WHERE is_closed=0 AND end_time IS NOT NULL AND end_time <= ?",
            (now,)
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        _err("get_expired_polls", e)
        return []


# ══════════════════════════════════════════
# التصويت — thread-safe مع BEGIN IMMEDIATE
# ══════════════════════════════════════════

def cast_vote(poll_id: int, user_id: int, option_id: int) -> tuple[bool, str]:
    """
    يسجّل صوتاً أو يغيّره بشكل آمن تحت حمل عالٍ.

    الحماية من race conditions:
    - per-poll threading.Lock يمنع التنفيذ المتزامن لنفس التصويت
    - BEGIN IMMEDIATE يقفل DB للكتابة حتى COMMIT

    يرجع (True, "new"|"changed"|"same") أو (False, سبب_الرفض).
    """
    lock = _get_vote_lock(poll_id)
    with lock:
        return _cast_vote_locked(poll_id, user_id, option_id)


def _cast_vote_locked(poll_id: int, user_id: int, option_id: int) -> tuple[bool, str]:
    try:
        conn = get_db_conn()

        # قراءة التصويت داخل transaction لضمان consistency
        conn.execute("BEGIN IMMEDIATE")

        poll_row = conn.execute("SELECT * FROM polls WHERE id=?", (poll_id,)).fetchone()
        if not poll_row:
            conn.execute("ROLLBACK")
            return False, "not_found"

        poll = dict(poll_row)

        if poll["is_closed"]:
            conn.execute("ROLLBACK")
            return False, "closed"

        # فحص انتهاء الوقت
        now = int(time.time())
        if poll["end_time"] and now > poll["end_time"]:
            conn.execute("UPDATE polls SET is_closed=1 WHERE id=?", (poll_id,))
            conn.execute("COMMIT")
            return False, "closed"

        # فحص قفل آخر X ثانية
        lock_secs = poll.get("lock_before_end", 0)
        if lock_secs and poll["end_time"]:
            if poll["end_time"] - now <= lock_secs:
                conn.execute("ROLLBACK")
                return False, "locked"

        # التحقق من وجود الخيار في هذا التصويت
        opt_row = conn.execute(
            "SELECT id FROM poll_options WHERE id=? AND poll_id=?",
            (option_id, poll_id)
        ).fetchone()
        if not opt_row:
            conn.execute("ROLLBACK")
            return False, "invalid_option"

        existing = conn.execute(
            "SELECT * FROM poll_votes WHERE poll_id=? AND user_id=?",
            (poll_id, user_id)
        ).fetchone()

        if existing:
            existing = dict(existing)
            if existing["option_id"] == option_id:
                conn.execute("ROLLBACK")
                return True, "same"

            if not poll["allow_change"]:
                conn.execute("ROLLBACK")
                return False, "no_change"

            # فحص حد تغيير الصوت
            max_changes = poll.get("max_vote_changes", 0)
            if max_changes and existing["change_count"] >= max_changes:
                conn.execute("ROLLBACK")
                return False, "change_limit"

            # تغيير الصوت
            conn.execute(
                "UPDATE poll_votes SET option_id=?, voted_at=?, change_count=change_count+1 "
                "WHERE poll_id=? AND user_id=?",
                (option_id, now, poll_id, user_id)
            )
            conn.execute(
                "UPDATE poll_options SET votes_count = votes_count - 1 WHERE id=?",
                (existing["option_id"],)
            )
            conn.execute(
                "UPDATE poll_options SET votes_count = votes_count + 1 WHERE id=?",
                (option_id,)
            )
            conn.execute("COMMIT")
            return True, "changed"

        else:
            conn.execute(
                "INSERT INTO poll_votes (poll_id, user_id, option_id, voted_at, change_count) "
                "VALUES (?,?,?,?,0)",
                (poll_id, user_id, option_id, now)
            )
            conn.execute(
                "UPDATE poll_options SET votes_count = votes_count + 1 WHERE id=?",
                (option_id,)
            )
            conn.execute("COMMIT")
            return True, "new"

    except Exception as e:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        _err("cast_vote", e)
        return False, "error"
