"""تست‌های پاک‌سازی HTML خروجی دستیار (ضد XSS)."""

from services.ai.sanitizer import sanitize_html


# ============================================================
# ★ حذف محتوای خطرناک
# ============================================================
def test_script_tag_and_content_are_removed():
    cleaned = sanitize_html("<p>سلام</p><script>alert('x')</script><p>پایان</p>")

    assert "script" not in cleaned.lower()
    assert "alert" not in cleaned
    assert "سلام" in cleaned and "پایان" in cleaned


def test_img_with_event_handler_is_removed():
    cleaned = sanitize_html('<img src=x onerror="alert(1)">متن سالم')

    assert "img" not in cleaned.lower()
    assert "onerror" not in cleaned.lower()
    assert "متن سالم" in cleaned


def test_iframe_and_svg_are_removed():
    cleaned = sanitize_html('<iframe src="https://evil"></iframe><svg onload="x()"></svg>ok')

    assert "iframe" not in cleaned.lower()
    assert "svg" not in cleaned.lower()
    assert cleaned.endswith("ok")


def test_javascript_href_is_stripped_but_text_kept():
    cleaned = sanitize_html('<a href="javascript:alert(1)">کلیک</a>')

    assert "javascript" not in cleaned.lower()
    assert "کلیک" in cleaned
    assert "<a>" in cleaned or "<a " in cleaned


def test_data_url_in_href_is_rejected():
    cleaned = sanitize_html('<a href="data:text/html;base64,PHNjcmlwdD4=">x</a>')

    assert "data:" not in cleaned


# ============================================================
# ★ حفظ تگ‌های مجاز
# ============================================================
def test_allowed_markup_is_preserved():
    source = (
        '<i class="fa-solid fa-check" style="color:#10b981"></i> '
        "<strong>۷۰۴۵</strong> سند"
    )
    cleaned = sanitize_html(source)

    assert '<i class="fa-solid fa-check" style="color:#10b981">' in cleaned
    assert "<strong>۷۰۴۵</strong>" in cleaned


def test_link_with_https_is_preserved():
    cleaned = sanitize_html('<a href="https://example.com/doc">سند</a>')

    assert 'href="https://example.com/doc"' in cleaned
    assert "سند" in cleaned


def test_style_with_url_is_dropped():
    cleaned = sanitize_html('<i style="background:url(javascript:alert(1))">x</i>')

    assert "style=" not in cleaned
    assert "javascript" not in cleaned


def test_text_is_escaped():
    cleaned = sanitize_html("۵ < ۶ و ۷ > ۶")

    assert "&lt;" in cleaned and "&gt;" in cleaned
    assert "<" not in cleaned.replace("&lt;", "")


def test_unclosed_tags_are_closed():
    cleaned = sanitize_html("<strong>متن باز")

    assert cleaned.count("<strong>") == cleaned.count("</strong>")


def test_empty_and_none_input():
    assert sanitize_html("") == ""
    assert sanitize_html(None) == ""


# ============================================================
# ★ یکپارچگی با مسیر LLM
# ============================================================
def test_llm_answer_is_sanitized(monkeypatch):
    from services.ai.assistant_service import AssistantService
    from services.ai.llm_service import LLMService

    def fake_ask(**kwargs):
        return {
            "success": True,
            "answer": '<img src=x onerror="alert(1)"><strong>۷۰۴۵</strong> سند تکمیل شده',
            "tools_used": [],
            "iterations": 1,
        }

    monkeypatch.setattr(LLMService, "ask", staticmethod(fake_ask))

    result = AssistantService._ask_llm("چند سند تکمیل شده؟", user_id=1, is_admin=False)

    assert result is not None
    assert "onerror" not in result["answer"]
    assert "<strong>۷۰۴۵</strong>" in result["answer"]
