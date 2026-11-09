"""تست‌های صفحهٔ اسناد — رندر، صفحه‌بندی، فیلتر سال و آمار SQL."""

import pytest

from helpers.date_helper import DateHelper


# ============================================================
# ★ تبدیل سال — رگرسیون باگ میلادی/شمسی
# ============================================================
@pytest.mark.parametrize(
    "value,expected",
    [
        ("2026/04/25", 1405),
        ("2025/12/01", 1404),
        ("1405/01/01", 1405),
        ("1404/10/11", 1404),
    ],
)
def test_get_jalali_year_handles_both_calendars(value, expected):
    assert DateHelper.get_jalali_year(value) == expected


@pytest.mark.parametrize("value", ["", None, "0", "؟", "بدون تاریخ", "2026/13/45"])
def test_get_jalali_year_returns_none_for_invalid(value):
    assert DateHelper.get_jalali_year(value) is None


# ============================================================
# ★ سرویس صفحه‌بندی
# ============================================================
def _admin_client(client):
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "admin"
        session["role"] = "admin"
        session["full_name"] = "Admin"
    return client


def test_get_page_limits_rows_and_reports_totals(app_instance):
    from services.documents.document_service import DocumentService

    with app_instance.app_context():
        data = DocumentService.get_page("all", page=1, per_page=24)

    assert data["page"] == 1
    assert data["per_page"] == 24
    assert len(data["records"]) == 24
    assert data["total"] >= len(data["records"])
    assert data["pages"] == max(1, (data["total"] + 23) // 24)


def test_get_page_clamps_out_of_range_page(app_instance):
    from services.documents.document_service import DocumentService

    with app_instance.app_context():
        first = DocumentService.get_page("all", page=1)
        too_far = DocumentService.get_page("all", page=10 ** 6)

    assert too_far["page"] == first["pages"]
    assert too_far["records"]


def test_page_two_differs_from_page_one(app_instance):
    from services.documents.document_service import DocumentService

    with app_instance.app_context():
        page_one = DocumentService.get_page("all", page=1)
        page_two = DocumentService.get_page("all", page=2)

    assert page_one["records"][0]["id"] != page_two["records"][0]["id"]


def test_year_totals_add_up(app_instance):
    from services.documents.document_service import DocumentService

    with app_instance.app_context():
        years = DocumentService.get_available_years()
        total_all = DocumentService.get_page("all")["total"]
        per_year = sum(DocumentService.get_page(year)["total"] for year in years)

    assert total_all == per_year


def test_statistics_match_page_total(app_instance):
    from services.documents.document_service import DocumentService

    with app_instance.app_context():
        for year in ["all"] + DocumentService.get_available_years():
            data = DocumentService.get_page(year)
            stats = DocumentService.get_statistics(year)

            assert stats["total"] == data["total"]
            assert sum(item["count"] for item in stats["statuses"]) == data["total"]
            assert sum(item["count"] for item in stats["departments"]) == data["total"]
            assert sum(item["count"] for item in stats["areas"]) == data["total"]


# ============================================================
# ★ مسیر HTTP
# ============================================================
def test_documents_page_renders_cards(client):
    _admin_client(client)
    response = client.get("/documents/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "مدیریت اسناد" in html
    assert html.count('class="document-card"') == 24
    assert "documents-pagination" in html
    assert "مشاهده سند" in html


def test_documents_page_second_page(client):
    _admin_client(client)
    first = client.get("/documents/").get_data(as_text=True)
    second = client.get("/documents/?page=2").get_data(as_text=True)

    assert "page-btn active" in second
    assert first != second


def test_documents_page_year_filter(client):
    _admin_client(client)
    response = client.get("/documents/?year=1404")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "در سال ۱۴۰۴" in html


def test_documents_page_invalid_year_falls_back_to_all(client):
    _admin_client(client)
    response = client.get("/documents/?year=9999")

    assert response.status_code == 200
    assert "مدیریت اسناد" in response.get_data(as_text=True)


def test_documents_page_requires_admin_role(client):
    with client.session_transaction() as session:
        session["user_id"] = 5
        session["username"] = "expert"
        session["role"] = "expert"

    response = client.get("/documents/", follow_redirects=False)
    assert response.status_code == 403
