"""
منطق أعمال نظام القرآن — بدون تفاعل مع البوت
"""
import re
from typing import Optional
from modules.quran import quran_db as db

# ══════════════════════════════════════════
# تطبيع النص العربي (المطلوب بالضبط)
# ══════════════════════════════════════════

TASHKEEL_PATTERN = re.compile(r'[\u0617-\u061A\u064B-\u0652\u0670\u0640]')


def remove_tashkeel(text: str) -> str:
    if not text:
        return text
    return TASHKEEL_PATTERN.sub('', text)


def normalize_text(text: str) -> str:
    text = remove_tashkeel(text)
    return text.strip().lower()


# ══════════════════════════════════════════
# التلاوة
# ══════════════════════════════════════════

def get_current_ayah(user_id: int) -> Optional[dict]:
    """يرجع الآية الحالية للمستخدم (أو الأولى إذا لم يبدأ بعد)."""
    progress = db.get_progress(user_id)
    if progress:
        ayah = db.get_ayah(progress["last_ayah_id"])
        return ayah
    # لا يوجد تقدم — ابدأ من الأولى
    return db.get_first_ayah()


def navigate(user_id: int, direction: str) -> Optional[dict]:
    """
    direction: 'next' | 'prev'
    يرجع الآية الجديدة أو None إذا لم توجد.
    """
    progress = db.get_progress(user_id)
    current_id = progress["last_ayah_id"] if progress else (
        db.get_first_ayah() or {"id": 0}
    )["id"]

    if direction == "next":
        ayah = db.get_next_ayah(current_id)
    else:
        ayah = db.get_prev_ayah(current_id)

    return ayah


def save_position(user_id: int, ayah_id: int, message_id: int = None):
    db.save_progress(user_id, ayah_id, message_id)


def reset_user(user_id: int):
    db.reset_progress(user_id)


# ══════════════════════════════════════════
# المفضلة
# ══════════════════════════════════════════

def toggle_favorite(user_id: int, ayah_id: int) -> tuple[bool, str]:
    """
    يضيف أو يزيل من المفضلة.
    يرجع (is_now_favorite, message)
    """
    if db.is_favorite(user_id, ayah_id):
        db.remove_favorite(user_id, ayah_id)
        return False, "تمت إزالة الآية من المفضلة."
    else:
        db.add_favorite(user_id, ayah_id)
        return True, "تمت إضافة الآية إلى المفضلة ⭐️"


def get_user_favorites(user_id: int) -> list[dict]:
    return db.get_favorites(user_id)


# ══════════════════════════════════════════
# البحث
# ══════════════════════════════════════════

def search(query: str) -> list[dict]:
    """يبحث بعد تطبيع النص."""
    normalized = normalize_text(query)
    if len(normalized) < 2:
        return []
    return db.search_ayat(normalized)


# ══════════════════════════════════════════
# التفسير
# ══════════════════════════════════════════

def get_available_tafseer(ayah: dict) -> list[tuple[str, str]]:
    """
    يرجع قائمة التفاسير المتاحة للآية.
    كل عنصر: (اسم_عربي, اسم_العمود)
    """
    available = []
    for name_ar, col in db.TAFSEER_TYPES.items():
        if ayah.get(col):
            available.append((name_ar, col))
    return available


# ══════════════════════════════════════════
# إدارة المحتوى (للمطورين)
# ══════════════════════════════════════════

def add_ayah(sura_name: str, ayah_number: int, text_with: str) -> int:
    text_without = normalize_text(text_with)
    return db.insert_ayah(sura_name, ayah_number, text_with, text_without)


def edit_ayah(ayah_id: int, new_text: str) -> bool:
    text_without = normalize_text(new_text)
    return db.update_ayah_text(ayah_id, new_text, text_without)


def edit_tafseer(ayah_id: int, tafseer_col: str, content: str) -> bool:
    return db.update_tafseer(ayah_id, tafseer_col, content)


def bulk_add_ayat(sura_name: str, start_number: int, raw_text: str) -> int:
    """
    يضيف آيات متعددة مفصولة بـ BULK_SEPARATOR.
    يرجع عدد الآيات المضافة.
    """
    items = [i.strip() for i in raw_text.split(db.BULK_SEPARATOR) if i.strip()]
    added = 0
    for i, text in enumerate(items):
        ayah_num = start_number + i
        result   = add_ayah(sura_name, ayah_num, text)
        if result:
            added += 1
    return added
