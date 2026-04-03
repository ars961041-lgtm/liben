"""
ثوابت نظام التنسيق الذكي
"""

# ── خريطة الوسوم البسيطة (نفس الوسم يفتح ويغلق) ──
# tag_key → (html_open, html_close, is_block)
SIMPLE_TAGS: dict[str, tuple[str, str, bool]] = {
    "b":   ("<b>",              "</b>",              False),
    "i":   ("<i>",              "</i>",              False),
    "u":   ("<u>",              "</u>",              False),
    "s":   ("<s>",              "</s>",              False),
    "sp":  ("<tg-spoiler>",     "</tg-spoiler>",     False),
    "c":   ("<code>",           "</code>",           False),
    "pre": ("<pre>",            "</pre>",            True),
    "q":   ("<blockquote>",     "</blockquote>",     True),
    "e":   ('<blockquote expandable="1">', "</blockquote>", True),
}

# ── الوسوم التي لا تُحلَّل داخلها وسوم أخرى ──
RAW_CONTENT_TAGS = {"c", "pre"}

# ── الحد الأقصى لطول النص المدخل ──
MAX_INPUT_LENGTH = 4000

# ── دليل التنسيق — كل قسم ──
FORMAT_GUIDE: dict[str, dict] = {
    "bold": {
        "label":   "굵게Bold — عريض",
        "emoji":   "𝐁",
        "title":   "✏️ النص العريض",
        "desc":    "يجعل النص <b>عريضاً</b>.",
        "usage":   "#b#نص عريض#b#",
        "example": "<b>نص عريض</b>",
    },
    "italic": {
        "label":   "Italic — مائل",
        "emoji":   "𝐼",
        "title":   "✏️ النص المائل",
        "desc":    "يجعل النص <i>مائلاً</i>.",
        "usage":   "#i#نص مائل#i#",
        "example": "<i>نص مائل</i>",
    },
    "underline": {
        "label":   "Underline — تحته خط",
        "emoji":   "U̲",
        "title":   "✏️ تحته خط",
        "desc":    "يضع خطاً تحت النص.",
        "usage":   "#u#نص#u#",
        "example": "<u>نص</u>",
    },
    "strike": {
        "label":   "Strike — يتوسطه خط",
        "emoji":   "S̶",
        "title":   "✏️ يتوسطه خط",
        "desc":    "يضع خطاً في وسط النص.",
        "usage":   "#s#نص#s#",
        "example": "<s>نص</s>",
    },
    "code": {
        "label":   "Code — كود",
        "emoji":   "</>",
        "title":   "✏️ الكود",
        "desc":    (
            "كود مضمّن: <code>#c#نص#c#</code>\n"
            "كود بلوك بلغة: <code>#c# python\nكود\n#c#</code>"
        ),
        "usage":   "#c#print('hello')#c#",
        "example": "<code>print('hello')</code>",
    },
    "spoiler": {
        "label":   "Spoiler — مخفي",
        "emoji":   "👁",
        "title":   "✏️ النص المخفي",
        "desc":    "يخفي النص حتى يضغط عليه المستخدم.",
        "usage":   "#sp#نص مخفي#sp#",
        "example": "<tg-spoiler>نص مخفي</tg-spoiler>",
    },
    "quote": {
        "label":   "Quote — اقتباس",
        "emoji":   "❝",
        "title":   "✏️ الاقتباس",
        "desc":    (
            "اقتباس عادي: <code>#q#نص#q#</code>\n"
            "اقتباس قابل للتوسيع: <code>#e#نص#e#</code>"
        ),
        "usage":   "#q#هذا اقتباس#q#",
        "example": "<blockquote>هذا اقتباس</blockquote>",
    },
    "link": {
        "label":   "Link — رابط",
        "emoji":   "🔗",
        "title":   "✏️ الروابط والإشارات",
        "desc":    (
            "رابط: <code>#a# https://example.com | اضغط هنا</code>\n"
            "إشارة مستخدم: <code>#m# 123456789</code>"
        ),
        "usage":   "#a# https://t.me | تيليغرام",
        "example": '<a href="https://t.me">تيليغرام</a>',
    },
    "advanced": {
        "label":   "Advanced — متقدم",
        "emoji":   "⚡",
        "title":   "✏️ التنسيق المتقدم",
        "desc":    (
            "دمج الوسوم:\n"
            "<code>#b##i#نص عريض ومائل#i##b#</code>\n\n"
            "كود بلوك:\n"
            "<code>#pre#\nكود هنا\n#pre#</code>\n\n"
            "الوسوم غير المغلقة تُغلق تلقائياً."
        ),
        "usage":   "#b##i#متقدم#i##b#",
        "example": "<b><i>متقدم</i></b>",
    },
}
