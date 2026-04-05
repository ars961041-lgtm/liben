# database/utils/tops_builder.py

import random
from utils.helpers import get_lines

# -----------------------------
# 🏆 إيموجيات المراتب الأولى
# -----------------------------
MEDALS = ["🥇", "🥈", "🥉"]


# -----------------------------
# 🧠 تجهيز الصفوف بشكل آمن
# -----------------------------
def _normalize_rows(rows):
    """
    يضمن أن كل صف يحتوي name و value
    """
    normalized = []

    for r in rows:
        name = str(r.get("name", "Unknown"))
        value = r.get("value", 0)

        # تحويل القيم لأرقام أو نص
        if isinstance(value, float):
            value = round(value, 2)

        normalized.append({
            "name": name,
            "value": value
        })

    return normalized


# -----------------------------
# ✨ تصميم 1: بسيط
# -----------------------------
def design_simple(title, rows, note=""):
    text = f"🏆 {title}\n\n"

    if note:
        text += f"💡 {note}\n\n"

    for i, r in enumerate(rows, 1):
        medal = MEDALS[i - 1] if i <= 3 else "•"
        text += f"{medal} {r['name']} | {r['value']}\n"

    return text


# -----------------------------
# ✨ تصميم 2: مرتب
# -----------------------------
def design_ranked(title, rows, note=""):
    text = f"📊 {title}\n\n"

    if note:
        text += f"💡 {note}\n\n"

    for i, r in enumerate(rows, 1):
        text += f"{i}) {r['name']} → {r['value']}\n"

    return text


# -----------------------------
# ✨ تصميم 3: تفصيلي
# -----------------------------
def design_card(title, rows, note=""):
    text = f"🌟 {title}\n\n"

    if note:
        text += f"💡 {note}\n\n"

    for i, r in enumerate(rows, 1):
        medal = MEDALS[i - 1] if i <= 3 else f"{i}."
        text += f"{medal} {r['name']}\n"
        text += f"   📊 القيمة: {r['value']}\n\n"

    return text


# -----------------------------
# ✨ تصميم 4: فاخر
# -----------------------------
def design_fancy(title, rows, note=""):
    text = f"👑 ═══ {title} ═══ 👑\n\n"

    if note:
        text += f"💡 {note}\n\n"

    for i, r in enumerate(rows, 1):
        medal = MEDALS[i - 1] if i <= 3 else "🔹"
        text += f"{medal} {r['name']}  ➤  {r['value']}\n"

    text += "\n════════════════"
    return text


# -----------------------------
# ✨ تصميم 5: احترافي
# -----------------------------
def design_pro(title, rows, note=""):
    text = f"🏆 {title}\n"
    text += f"{get_lines()}\n\n"

    if note:
        text += f"💡 {note}\n\n"

    for i, r in enumerate(rows, 1):
        medal = MEDALS[i - 1] if i <= 3 else f"{i}"
        text += f"{medal} ⟫ {r['name']}\n"
        text += f"   ↳ 📊 {r['value']}\n\n"

    text += f"{get_lines()}"
    return text


# -----------------------------
# 🎲 قائمة التصاميم
# -----------------------------
DESIGNS = [
    design_simple,
    design_ranked,
    design_card,
    design_fancy,
    design_pro
]


# -----------------------------
# 🧠 الدالة الأساسية
# -----------------------------
def build_top(title, rows, note=""):
    """
    إنشاء رسالة التوب
    """

    if not rows:
        return "❌ لا توجد بيانات."

    try:
        rows = _normalize_rows(rows)
        design = random.choice(DESIGNS)
        return design(title, rows, note)

    except Exception as e:
        # fallback إذا حصل خطأ في أحد التصاميم
        text = f"🏆 {title}\n\n"
        for i, r in enumerate(rows, 1):
            text += f"{i}. {r.get('name','Unknown')} | {r.get('value',0)}\n"

        return text