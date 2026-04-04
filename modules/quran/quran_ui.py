"""
مساعدات واجهة المستخدم للقرآن — بناء النصوص والأزرار فقط
"""
from utils.pagination import btn, paginate_list
from modules.quran.quran_service import get_available_tafseer

_B = "p"   # أزرق
_G = "su"  # أخضر
_R = "d"   # أحمر


def build_ayah_text(ayah: dict, total: int) -> str:
    """يبني نص عرض الآية."""
    return (
        f"📖 <b>{ayah['sura_name']}</b> — آية {ayah['ayah_number']}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"{ayah['text_with_tashkeel']}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"<i>آية {ayah['id']} من {total}</i>"
    )


def build_ayah_buttons(uid: int, cid: int, ayah: dict,
                       is_fav: bool, has_prev: bool, has_next: bool) -> tuple[list, list]:
    """يبني أزرار عرض الآية."""
    owner = (uid, cid)
    aid   = ayah["id"]

    nav = []
    if has_prev:
        nav.append(btn("⬅️ السابقة", "qr_prev", {"aid": aid}, color=_B, owner=owner))
    if has_next:
        nav.append(btn("➡️ التالية", "qr_next", {"aid": aid}, color=_B, owner=owner))

    fav_label = "💛 إزالة من المفضلة" if is_fav else "⭐️ المفضلة"
    action_row = [
        btn("📖 تفسير",    "qr_tafseer",  {"aid": aid}, color=_B, owner=owner),
        btn(fav_label,     "qr_fav",      {"aid": aid}, color=_G, owner=owner),
        btn("❌ إغلاق",    "qr_close",    {},            color=_R, owner=owner),
    ]

    buttons = nav + action_row
    layout  = ([len(nav)] if nav else []) + [3]
    return buttons, layout


def build_tafseer_buttons(uid: int, cid: int, ayah: dict) -> tuple[list, list]:
    """يبني أزرار اختيار التفسير."""
    owner     = (uid, cid)
    aid       = ayah["id"]
    available = get_available_tafseer(ayah)

    if not available:
        return [], []

    buttons = [
        btn(name_ar, "qr_show_tafseer",
            {"aid": aid, "col": col}, color=_B, owner=owner)
        for name_ar, col in available
    ]
    buttons.append(btn("🔙 رجوع", "qr_back_to_ayah", {"aid": aid}, color=_R, owner=owner))

    n      = len(buttons)
    layout = [2] * (n // 2) + ([1] if n % 2 else [])
    return buttons, layout


def build_search_result_text(results: list[dict], page: int, total_pages: int) -> str:
    """يبني نص نتائج البحث."""
    text = f"🔍 <b>نتائج البحث</b> ({page+1}/{total_pages})\n━━━━━━━━━━━━━━━\n\n"
    for r in results:
        text += (
            f"📖 <b>{r['sura_name']}</b> — آية {r['ayah_number']}\n"
            f"{r['text_with_tashkeel']}\n\n"
        )
    return text


def build_search_buttons(uid: int, cid: int, query: str,
                         page: int, total_pages: int,
                         results: list[dict]) -> tuple[list, list]:
    """يبني أزرار نتائج البحث."""
    owner   = (uid, cid)
    buttons = []

    # زر لكل نتيجة للانتقال إليها
    for r in results:
        buttons.append(btn(
            f"📖 {r['sura_name']} {r['ayah_number']}",
            "qr_goto_ayah",
            {"aid": r["id"]},
            color=_B, owner=owner,
        ))

    nav = []
    if page > 0:
        nav.append(btn("◀️", "qr_search_page",
                       {"q": query, "p": page - 1}, owner=owner))
    if page < total_pages - 1:
        nav.append(btn("▶️", "qr_search_page",
                       {"q": query, "p": page + 1}, owner=owner))
    nav.append(btn("❌ إغلاق", "qr_close", {}, color=_R, owner=owner))

    buttons += nav
    n_results = len(results)
    layout    = [1] * n_results + ([len(nav)] if nav else [1])
    return buttons, layout


def build_favorites_text(favs: list[dict], page: int, total_pages: int) -> str:
    text = f"⭐️ <b>مفضلتي</b> ({page+1}/{total_pages})\n━━━━━━━━━━━━━━━\n\n"
    for f in favs:
        text += (
            f"📖 <b>{f['sura_name']}</b> — آية {f['ayah_number']}\n"
            f"{f['text_with_tashkeel']}\n\n"
        )
    return text


def build_favorites_buttons(uid: int, cid: int, favs: list[dict],
                             page: int, total_pages: int) -> tuple[list, list]:
    owner   = (uid, cid)
    buttons = [
        btn(f"📖 {f['sura_name']} {f['ayah_number']}", "qr_goto_ayah",
            {"aid": f["id"]}, color=_B, owner=owner)
        for f in favs
    ]
    nav = []
    if page > 0:
        nav.append(btn("◀️", "qr_fav_page", {"p": page - 1}, owner=owner))
    if page < total_pages - 1:
        nav.append(btn("▶️", "qr_fav_page", {"p": page + 1}, owner=owner))
    nav.append(btn("❌ إغلاق", "qr_close", {}, color=_R, owner=owner))

    buttons += nav
    layout   = [1] * len(favs) + ([len(nav)] if nav else [1])
    return buttons, layout
