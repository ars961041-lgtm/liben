"""
محرك التحليل — منطق بحت، لا تفاعل مع البوت.

الوسوم المدعومة:
  #b#  #i#  #u#  #s#  #sp#  #c#  #pre#  #q#  #e#
  #a# URL | TEXT
  #m# USER_ID
  #c# lang ... #c#   → <pre><code class="language-lang">...</code></pre>

المحلل يعمل بمرور واحد (single-pass) مع مكدس للوسوم المفتوحة.
"""
import re
import html
from typing import NamedTuple

from .format_constants import SIMPLE_TAGS, RAW_CONTENT_TAGS, MAX_INPUT_LENGTH


# ══════════════════════════════════════════
# نتيجة التحليل
# ══════════════════════════════════════════

class ParseResult(NamedTuple):
    html:     str          # النص المُحوَّل
    warnings: list[str]    # تحذيرات (وسوم مُصلَحة، إلخ)
    ok:       bool         # True إذا لم تكن هناك أخطاء


# ══════════════════════════════════════════
# التعبير النمطي لاكتشاف الوسوم
# ══════════════════════════════════════════

# يطابق: #tag#  أو  #tag# rest_of_line  (للوسوم الخاصة مثل #a# و #m#)
_TAG_RE = re.compile(
    r"#([a-z]+)#"          # وسم بسيط
    r"(?:[ \t]+(.+?))?$",  # محتوى اختياري في نفس السطر (للروابط والإشارات)
    re.MULTILINE,
)

# ══════════════════════════════════════════
# الدالة الرئيسية
# ══════════════════════════════════════════

def parse(text: str) -> ParseResult:
    """
    يحوّل النص المُعلَّم بوسوم مخصصة إلى HTML صالح لـ Telegram.
    """
    warnings: list[str] = []

    # ── التحقق من الطول ──
    if not text or not text.strip():
        return ParseResult("", [], True)

    if len(text) > MAX_INPUT_LENGTH:
        text = text[:MAX_INPUT_LENGTH]
        warnings.append(f"⚠️ النص طويل جداً — تم اقتصاصه إلى {MAX_INPUT_LENGTH} حرف.")

    result = _Parser(text, warnings).run()
    return ParseResult(result, warnings, True)


# ══════════════════════════════════════════
# المحلل الداخلي
# ══════════════════════════════════════════

class _Parser:
    """
    محلل بمرور واحد مع مكدس للوسوم المفتوحة.
    يعالج السطر تلو الآخر ثم يدمج النتيجة.
    """

    def __init__(self, text: str, warnings: list[str]):
        self.text     = text
        self.warnings = warnings
        self.stack: list[str] = []   # مكدس الوسوم المفتوحة
        self.out: list[str]   = []   # أجزاء الإخراج

    # ── نقطة الدخول ──
    def run(self) -> str:
        lines = self.text.split("\n")
        processed = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # ── كشف بداية كود بلوك: #c# lang أو #pre# ──
            block_match = re.match(r"^#(c|pre)#(?:[ \t]+(\w+))?[ \t]*$", line)
            if block_match:
                tag  = block_match.group(1)
                lang = block_match.group(2) if tag == "c" else None
                # جمع المحتوى حتى وسم الإغلاق
                content_lines = []
                i += 1
                while i < len(lines):
                    if lines[i].strip() == f"#{tag}#":
                        i += 1
                        break
                    content_lines.append(lines[i])
                    i += 1
                else:
                    self.warnings.append(f"⚠️ وسم #{tag}# لم يُغلق — تم الإغلاق تلقائياً.")
                raw = "\n".join(content_lines)
                escaped = html.escape(raw)
                if lang:
                    processed.append(
                        f'<pre><code class="language-{html.escape(lang)}">'
                        f'{escaped}</code></pre>'
                    )
                elif tag == "c":
                    processed.append(f"<code>{escaped}</code>")
                else:
                    processed.append(f"<pre>{escaped}</pre>")
                continue

            # ── سطر عادي ──
            processed.append(self._process_line(line))
            i += 1

        # ── إغلاق الوسوم المفتوحة ──
        if self.stack:
            self.warnings.append(
                f"⚠️ وسوم لم تُغلق: {', '.join('#'+t+'#' for t in self.stack)} — تم الإغلاق تلقائياً."
            )
            while self.stack:
                tag = self.stack.pop()
                _, close, _ = SIMPLE_TAGS[tag]
                processed.append(close)

        return "\n".join(processed)

    # ── معالجة سطر واحد ──
    def _process_line(self, line: str) -> str:
        """
        يعالج سطراً واحداً: يبحث عن الوسوم ويحوّلها.
        """
        out   = []
        pos   = 0
        stack = self.stack   # مشترك مع كامل المحلل

        # نمط الوسوم في السطر
        for m in re.finditer(r"#([a-z]+)#(?:[ \t]+(.+))?", line):
            tag_key = m.group(1)
            inline  = (m.group(2) or "").strip()

            # ── نص قبل الوسم ──
            before = line[pos:m.start()]
            if before:
                out.append(html.escape(before))
            pos = m.end()

            # ── وسم رابط ──
            if tag_key == "a":
                out.append(self._parse_link(inline))
                continue

            # ── وسم إشارة مستخدم ──
            if tag_key == "m":
                out.append(self._parse_mention(inline))
                continue

            # ── وسم بسيط ──
            if tag_key not in SIMPLE_TAGS:
                # وسم غير معروف — أبقِه كنص
                out.append(html.escape(m.group(0)))
                continue

            open_html, close_html, _ = SIMPLE_TAGS[tag_key]

            if tag_key not in stack:
                # فتح الوسم
                stack.append(tag_key)
                out.append(open_html)
            else:
                # إغلاق الوسم — مع تصحيح الترتيب إذا لزم
                if stack[-1] == tag_key:
                    stack.pop()
                    out.append(close_html)
                else:
                    # ترتيب خاطئ — أغلق كل شيء حتى هذا الوسم
                    self.warnings.append(
                        f"⚠️ ترتيب وسوم خاطئ عند #{tag_key}# — تم التصحيح تلقائياً."
                    )
                    # أغلق الوسوم الأحدث أولاً
                    while stack and stack[-1] != tag_key:
                        inner = stack.pop()
                        _, inner_close, _ = SIMPLE_TAGS[inner]
                        out.append(inner_close)
                    if stack and stack[-1] == tag_key:
                        stack.pop()
                        out.append(close_html)

        # ── ما تبقى من السطر ──
        tail = line[pos:]
        if tail:
            out.append(html.escape(tail))

        return "".join(out)

    # ── تحليل الرابط ──
    def _parse_link(self, inline: str) -> str:
        """
        #a# URL | TEXT  →  <a href="URL">TEXT</a>
        """
        if "|" in inline:
            url, _, text = inline.partition("|")
            url  = url.strip()
            text = text.strip() or url
        else:
            url  = inline.strip()
            text = url

        if not url:
            return html.escape(f"#a# {inline}")

        # تحقق بسيط من الرابط
        if not (url.startswith("http://") or url.startswith("https://")
                or url.startswith("tg://")):
            self.warnings.append(f"⚠️ رابط غير صالح: {url[:50]}")
            return html.escape(text)

        return f'<a href="{html.escape(url)}">{html.escape(text)}</a>'

    # ── تحليل الإشارة ──
    def _parse_mention(self, inline: str) -> str:
        """
        #m# USER_ID  →  <a href="tg://user?id=USER_ID">@mention</a>
        """
        uid = inline.strip()
        if not uid.lstrip("-").isdigit():
            self.warnings.append(f"⚠️ معرف مستخدم غير صالح: {uid[:20]}")
            return html.escape(f"#m# {inline}")
        return f'<a href="tg://user?id={uid}">@{uid}</a>'
