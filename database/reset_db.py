"""
إعادة إنشاء قاعدة البيانات — حذف قسري بأي وسيلة ممكنة
"""
import os
import gc
import time

from core.config import DB_NAME
from database.connection import close_all_connections
from database.db_schema import create_all_tables
from utils.logger import log_event


def force_delete_db(path: str, retries: int = 10) -> tuple[bool, str]:
    """
    يحذف ملف DB بالقوة مهما كانت الظروف.

    الخوارزمية لكل محاولة:
    1. أغلق كل الاتصالات المسجّلة
    2. gc.collect() لتحرير أي مراجع dangling
    3. انتظر قليلاً
    4. احذف .db + -wal + -shm

    يرجع (True, رسالة) عند النجاح
    يرجع (False, رسالة) عند الفشل الكامل — لا إعادة محاولة صامتة
    """
    suffixes = ("", "-wal", "-shm")

    for i in range(1, retries + 1):
        log_event("db_delete_attempt", attempt=i, path=path)

        close_all_connections()
        gc.collect()
        time.sleep(0.3)

        all_deleted = True
        for suffix in suffixes:
            target = path + suffix
            if not os.path.exists(target):
                continue
            try:
                os.remove(target)
            except Exception as e:
                log_event("db_delete_file_error", attempt=i, file=target, error=str(e))
                all_deleted = False

        if all_deleted:
            log_event("db_delete_success", attempts=i)
            return True, "✅ تم حذف قاعدة البيانات بنجاح"

    log_event("db_delete_failed", retries=retries)
    return False, "❌ فشل حذف قاعدة البيانات رغم المحاولات"


def reset_database() -> tuple[bool, str]:
    """
    يُعيد إنشاء قاعدة البيانات كاملة.
    إما ينجح أو يفشل بوضوح — لا إعادة محاولة صامتة في الخلفية.
    """
    ok, msg = force_delete_db(DB_NAME)
    if not ok:
        return False, msg

    create_all_tables()
    log_event("db_reset_complete")
    return True, "✅ تم حذف قاعدة البيانات بنجاح"
