"""
نظام الاستبدال الذكي — بدون regex، حدود كلمات بالمسافات
"""


def replace_word(text: str, old: str, new: str, count: int = 0) -> tuple[str, int]:
    """
    يستبدل الكلمة القديمة بالجديدة مع احترام حدود الكلمات.

    الخوارزمية:
    1. نضيف مسافة في البداية والنهاية (padding)
    2. نبحث عن " old " (مع مسافتين)
    3. نستبدل بـ " new "
    4. نزيل الـ padding

    يرجع (النص_الجديد, عدد_الاستبدالات_الفعلية)
    """
    if not old or not text:
        return text, 0

    target      = " " + old + " "
    replacement = " " + new + " "
    padded      = " " + text + " "

    replaced_count = 0

    if count <= 0:
        # استبدال كل التكرارات
        result = padded
        while target in result:
            result = result.replace(target, replacement, 1)
            replaced_count += 1
    else:
        # استبدال أول N تكرارات فقط
        result = padded
        for _ in range(count):
            if target not in result:
                break
            result = result.replace(target, replacement, 1)
            replaced_count += 1

    # إزالة الـ padding
    result = result[1:-1]
    return result, replaced_count


def parse_replace_command(text: str) -> tuple[str, str, int] | None:
    """
    تحليل أمر التعديل

    الصيغ المدعومة:

    تعديل كلمة كلمة
    تعديل كلمة كلمة 2

    تعديل |جملة| |جملة|
    تعديل |جملة| |جملة| 2
    """

    text = text.strip()

    if not text.startswith("تعديل"):
        return None

    body = text[5:].strip()

    # ───── صيغة |النص| ─────
    if "|" in body:
        parts = body.split("|")

        # الشكل المتوقع:
        # ['', old, ' ', new, ' 2']
        if len(parts) < 4:
            return None

        old = parts[1].strip()
        new = parts[3].strip()

        after = parts[4].strip() if len(parts) >= 5 else ""

        count = 0
        if after:
            try:
                count = int(after)
            except ValueError:
                return None

        return old, new, count

    # ───── الصيغة القديمة (كلمات) ─────
    parts = body.split()

    if len(parts) < 2:
        return None

    old = parts[0]
    new = parts[1]

    count = 0

    if len(parts) >= 3:
        try:
            count = int(parts[2])
        except ValueError:
            return None

    return old, new, count