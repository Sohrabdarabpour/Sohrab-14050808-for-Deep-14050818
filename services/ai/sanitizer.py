"""پاک‌سازی HTML خروجی مدل زبانی (ضد XSS).

پاسخ دستیار به‌صورت HTML در صفحه تزریق می‌شود (``innerHTML``) چون handlerها
از آیکون و رنگ استفاده می‌کنند. خروجی مدل اما قابل اعتماد نیست: یک سند با
موضوع مخرب می‌تواند از طریق prompt injection مدل را وادار کند تگ اجرایی
تولید کند. این ماژول با یک allowlist ساده (بدون وابستگی اضافه) فقط تگ‌ها و
صفاتِ بی‌خطر را نگه می‌دارد.
"""

from html import escape
from html.parser import HTMLParser

#: تگ‌هایی که handlerها و قالب دستیار استفاده می‌کنند
ALLOWED_TAGS = {
    "a", "b", "br", "code", "div", "em", "hr", "i", "li", "ol", "p",
    "small", "span", "strong", "u", "ul", "table", "thead", "tbody",
    "tr", "th", "td",
}

#: تگ‌هایی که کل محتوایشان باید دور ریخته شود
DROPPED_CONTENT_TAGS = {
    "script", "style", "iframe", "object", "embed", "svg", "math",
    "template", "form", "input", "button", "link", "meta", "base",
}

ALLOWED_ATTRS = {
    "class", "style", "href", "title", "target", "rel", "colspan",
    "rowspan", "dir", "lang", "data-doc-id", "data-status", "data-id",
}

VOID_TAGS = {"br", "hr"}

ALLOWED_HREF_PREFIXES = ("http://", "https://", "mailto:", "tel:", "#", "/", "./", "../")

#: الگوهای خطرناک در مقدار style (اجرای کد یا بارگذاری منبع خارجی)
DANGEROUS_STYLE_MARKERS = (
    "url(", "expression", "javascript:", "@import", "behavior",
    "-moz-binding", "\\", "&#",
)

MAX_INPUT_LENGTH = 20_000


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._open_tags = []
        self._drop_depth = 0

    # ------------------------------------------------------------
    # تگ‌های باز
    # ------------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()

        if tag in DROPPED_CONTENT_TAGS:
            self._drop_depth += 1
            return
        if self._drop_depth or tag not in ALLOWED_TAGS:
            return

        rendered = self._render_tag(tag, attrs)

        if tag in VOID_TAGS:
            self.parts.append(rendered)
            return

        self.parts.append(rendered)
        self._open_tags.append(tag)

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if tag in DROPPED_CONTENT_TAGS or self._drop_depth:
            return
        if tag in ALLOWED_TAGS:
            self.parts.append(self._render_tag(tag, attrs, self_closing=True))

    # ------------------------------------------------------------
    # تگ‌های بسته
    # ------------------------------------------------------------
    def handle_endtag(self, tag):
        tag = tag.lower()

        if tag in DROPPED_CONTENT_TAGS:
            if self._drop_depth:
                self._drop_depth -= 1
            return
        if self._drop_depth or tag not in self._open_tags:
            return

        while self._open_tags:
            open_tag = self._open_tags.pop()
            self.parts.append(f"</{open_tag}>")
            if open_tag == tag:
                break

    # ------------------------------------------------------------
    # متن و entityها
    # ------------------------------------------------------------
    def handle_data(self, data):
        if not self._drop_depth:
            self.parts.append(escape(data, quote=False))

    def handle_entityref(self, name):
        if not self._drop_depth:
            self.parts.append(f"&amp;{escape(name)};")

    def handle_charref(self, name):
        if not self._drop_depth:
            self.parts.append(f"&amp;#{escape(name)};")

    # ------------------------------------------------------------
    # ساخت تگ امن
    # ------------------------------------------------------------
    def _render_tag(self, tag, attrs, self_closing=False):
        safe_attrs = []

        for name, value in attrs:
            name = name.lower()
            if name not in ALLOWED_ATTRS or value is None:
                continue

            cleaned = self._clean_attr(name, value)
            if cleaned is None:
                continue

            safe_attrs.append(f'{name}="{escape(cleaned, quote=True)}"')

        if tag == "a" and any(attr.startswith('target="_blank"') for attr in safe_attrs):
            if not any(attr.startswith("rel=") for attr in safe_attrs):
                safe_attrs.append('rel="noopener noreferrer"')

        suffix = " /" if self_closing else ""
        attrs_sql = (" " + " ".join(safe_attrs)) if safe_attrs else ""
        return f"<{tag}{attrs_sql}{suffix}>"

    @staticmethod
    def _clean_attr(name, value):
        value = str(value).strip()

        if name == "style":
            lowered = value.lower()
            if any(marker in lowered for marker in DANGEROUS_STYLE_MARKERS):
                return None
            return value

        if name == "href":
            lowered = value.lower()
            if lowered.startswith(("javascript:", "data:", "vbscript:")):
                return None
            if not lowered.startswith(ALLOWED_HREF_PREFIXES):
                return None
            return value

        return value


def sanitize_html(html_text):
    """پاک‌سازی HTML با allowlist؛ در خطا، متن به‌صورت escape برگردانده می‌شود."""
    if not html_text:
        return ""

    text = str(html_text)[:MAX_INPUT_LENGTH]

    try:
        parser = _Sanitizer()
        parser.feed(text)
        parser.close()

        # بستن تگ‌هایی که باز مانده‌اند تا ساختار DOM به‌هم نریزد
        while parser._open_tags:
            parser.parts.append(f"</{parser._open_tags.pop()}>")

        return "".join(parser.parts)
    except Exception:
        return escape(text, quote=False)
