"""
tops_builder.py — بناء رسائل التوب بتنسيق ثابت ومحاذاة صحيحة.
"""
import re
from utils.helpers import get_lines

# ── ثوابت ──
MEDALS      = ["🥇", "🥈", "🥉"]
LTR_MARK    = "\u200e"   # يجبر اتجاه النص من اليسار لليمين
_MAX_NAME   = 20         # أقصى طول للاسم قبل القطع
_TOP_LIMIT  = 10         # الحد الافتراضي للعرض


# ══════════════════════════════════════════
# تنظيف الأسماء
# ══════════════════════════════════════════

# أحرف غير مرئية / تحكم شائعة في أسماء تيليغرام
_INVISIBLE = re.compile(
    r"[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u206a-\u206f\uFEFF\u00ad]"
)


def _clean_name(name) -> str:
    """يُنظّف الاسم ويُعيد '—' إذا كان فارغاً أو غير مرئي."""
    if not name:
        return "—"
    name = str(name)
    name = _INVISIBLE.sub("", name)   # أزل أحرف التحكم
    name = " ".join(name.split())     # اضغط المسافات المتعددة
    if not name.strip():
        return "—"
    # اقطع الأسماء الطويلة جداً
    if len(name) > _MAX_NAME:
        name = name[:_MAX_NAME].rstrip() + "…"
    return name


# ══════════════════════════════════════════
# تطبيع الصفوف
# ══════════════════════════════════════════

def _normalize_rows(rows: list) -> list[dict]:
    """يضمن أن كل صف يحتوي name و value، ويرتّب تنازلياً."""
    out = []
    for r in rows:
        name  = _clean_name(r.get("name"))
        value = r.get("value", 0)
        if isinstance(value, float):
            value = round(value, 2)
        out.append({"name": name, "value": value})

    # ترتيب صارم تنازلي بالقيمة
    out.sort(key=lambda x: x["value"] if isinstance(x["value"], (int, float)) else 0,
             reverse=True)
    return out[:_TOP_LIMIT]


# ══════════════════════════════════════════
# تنسيق القيمة
# ══════════════════════════════════════════

def _fmt_value(value) -> str:
    if isinstance(value, (int, float)):
        return f"{value:,.0f}"
    return str(value)


# ══════════════════════════════════════════
# البناء الرئيسي
# ══════════════════════════════════════════

def build_top(title: str, rows: list, note: str = "") -> str:
    """
    يبني رسالة توب بتنسيق ثابت ومحاذاة يسارية.

    الشكل:
        🔥 Top Active Users
        ─────────────────
        1) 🥇  48825  |  Name
        2) 🥈  33744  |  Name
        3) 🥉  32023  |  Name
        4)       712  |  Name
        ...
    """
    if not rows:
        return "❌ لا توجد بيانات."

    try:
        rows = _normalize_rows(rows)
    except Exception:
        pass

    if not rows:
        return "❌ لا توجد بيانات."

    # ── حساب أقصى عرض للقيمة لمحاذاة الأعمدة ──
    formatted_values = [_fmt_value(r["value"]) for r in rows]
    max_val_len      = max(len(v) for v in formatted_values)

    lines = []

    # ── رأس الرسالة ──
    lines.append(f"{LTR_MARK}🏆 {title}")
    lines.append("━━━━━━━━━━━━━━━")
    if note:
        lines.append(f"{LTR_MARK}💡 {note}")
        lines.append(f"{LTR_MARK}")

    # ── صفوف التوب ──
    for i, (row, val_str) in enumerate(zip(rows, formatted_values), 1):
        medal      = MEDALS[i - 1] if i <= 3 else "  "
        rank_label = f"{i})"
        # محاذاة القيمة يميناً داخل عمود ثابت العرض
        padded_val = val_str.rjust(max_val_len)
        name       = row["name"]

        # LTR_MARK يمنع انعكاس الترتيب عند وجود أسماء عربية
        lines.append(
            f"{LTR_MARK}{rank_label:<3} {medal}  {padded_val}  |  {name}"
        )

    lines.append("━━━━━━━━━━━━━━━")

    return "\n".join(lines)
