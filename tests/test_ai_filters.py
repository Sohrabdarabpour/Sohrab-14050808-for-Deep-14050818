"""تست‌های جستجوی پیشرفته‌ی دستیار و خروجی اکسل."""

import io
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.ai.llm_config import LLMConfig  # noqa: E402
from services.ai.search_filter_builder import SearchFilterBuilder  # noqa: E402

EXCEL_MIMETYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture(autouse=True)
def offline_llm():
    original = LLMConfig.ENABLED
    LLMConfig.ENABLED = False
    yield
    LLMConfig.ENABLED = original


# ============================================================
# استخراج فیلتر از متن
# ============================================================
def test_extracts_status():
    filters, labels = SearchFilterBuilder("اسناد تکمیل شده").build()
    assert filters["status_code"] == "completed"
    assert any("وضعیت" in label for label in labels)


def test_extracts_contractor_by_name():
    filters, _labels = SearchFilterBuilder("اسناد پیمانکار آبسان پالایش").build()
    assert filters.get("contractor_id") == 2


def test_extracts_area_by_name():
    filters, _labels = SearchFilterBuilder("اسناد ناحیه سیالات").build()
    assert filters.get("area_id")


def test_extracts_relative_date_range():
    filters, labels = SearchFilterBuilder("اسناد ماه گذشته").build()
    assert filters.get("date_from")
    assert filters.get("date_to")
    assert filters["date_from"] <= filters["date_to"]
    assert any("بازه" in label for label in labels)


def test_extracts_explicit_jalali_dates():
    filters, _labels = SearchFilterBuilder("اسناد از 1405/01/01 تا 1405/03/31").build()
    # جلالی به میلادی تبدیل می‌شود
    assert filters["date_from"].startswith("2026")
    assert filters["date_to"].startswith("2026")


def test_free_text_goes_to_query():
    filters, _labels = SearchFilterBuilder("اسناد درباره تأخیر مدارک").build()
    assert filters.get("query")
    # NLU حروف عربی را نرمال می‌کند: «تأخیر» → «تاخیر»
    assert "تاخیر" in filters["query"]


def test_empty_question_yields_no_filters():
    filters, labels = SearchFilterBuilder("").build()
    assert filters == {}
    assert labels == []


# ============================================================
# intentها
# ============================================================
@pytest.mark.parametrize(
    "question,expected",
    [
        ("اسناد پیمانکار MMTE با وضعیت تکمیل", "filtered_search"),
        ("اسناد ناحیه سیالات از ماه گذشته", "filtered_search"),
        ("خروجی اکسل اسناد پیمانکار MMTE", "filtered_export"),
        ("دانلود اکسل اسناد ناحیه برق", "filtered_export"),
    ],
)
def test_detect_filter_intents(app_instance, question, expected):
    from services.ai import IntentRegistry
    from services.ai.nlu import NLU

    intent, _entities, _confidence = IntentRegistry.detect(
        NLU.clean(question), is_admin=True
    )
    assert intent == expected, f"«{question}» → {intent} (انتظار: {expected})"


def test_plain_count_intent_not_hijacked():
    """«چند سند تکمیل شده» نباید به جستجوی پیشرفته برود."""
    from services.ai import IntentRegistry
    from services.ai.nlu import NLU

    intent, _entities, _confidence = IntentRegistry.detect(
        NLU.clean("چند سند تکمیل شده؟"), is_admin=True
    )
    assert intent == "count_completed"


def test_filtered_search_answer_contains_link(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = "admin"

    response = client.post(
        "/assistant/ask",
        json={"question": "اسناد پیمانکار MMTE با وضعیت تکمیل"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["meta"]["intent"] == "filtered_search"
    assert "/assistant/export/search" in payload["answer"]


# ============================================================
# خروجی اکسل
# ============================================================
def test_export_endpoint_returns_xlsx(client):
    import openpyxl

    with client.session_transaction() as sess:
        sess["user_id"] = 1

    response = client.get("/assistant/export/search?contractor=1&status=completed")

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith(EXCEL_MIMETYPE)

    workbook = openpyxl.load_workbook(io.BytesIO(response.data))
    sheet = workbook.active

    assert sheet.max_column == 17
    assert sheet.max_row > 1
    assert sheet.cell(row=1, column=1).value == "کد DFC"
    assert sheet.sheet_view.rightToLeft is True


def test_export_requires_login(client):
    response = client.get("/assistant/export/search?contractor=1")
    assert response.status_code == 302


def test_export_without_results_returns_404(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1

    response = client.get("/assistant/export/search?contractor=1&status=deleted&q=zzzzz")

    assert response.status_code == 404
    assert response.get_json()["error"] == "no_results"


def test_llm_tools_include_search_and_export():
    from services.ai.llm_tools import LLMTools

    names = {tool["function"]["name"] for tool in LLMTools.get_tools_schema(True)}
    assert "search_documents_advanced" in names
    assert "export_search_excel" in names
    assert "list_projects" in names


def test_llm_tool_search_advanced_returns_results():
    from services.ai.llm_tools import LLMTools

    result = LLMTools.execute(
        "search_documents_advanced",
        {"contractor_name": "MMTE", "limit": 3},
        user_id=1,
        is_admin=True,
    )
    assert result["total"] > 0
    assert len(result["documents"]) <= 3


def test_llm_tool_export_returns_url():
    from services.ai.llm_tools import LLMTools

    result = LLMTools.execute(
        "export_search_excel",
        {"contractor_name": "MMTE"},
        user_id=1,
        is_admin=True,
    )
    assert result["download_url"].startswith("/assistant/export/search")
    assert result["total"] > 0
