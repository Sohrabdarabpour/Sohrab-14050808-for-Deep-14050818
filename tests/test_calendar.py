"""تست‌های تقویم کاری، تعطیلات و مهلت پاسخ."""

import sqlite3
import time
from datetime import date

import pytest

from services.calendar import working_days


# ============================================================
# ★ ابزار تست: خالی‌کردن کش تعطیلات
# ============================================================
@pytest.fixture
def clean_calendar():
    """تعطیلات را موقتاً خالی می‌کند تا ریاضی روز کاری مستقل از seed باشد."""
    saved_dates = working_days._cache["dates"]
    saved_expires = working_days._cache["expires"]

    working_days._cache["dates"] = frozenset()
    working_days._cache["expires"] = time.monotonic() + 3600
    try:
        yield
    finally:
        working_days._cache["dates"] = saved_dates
        working_days._cache["expires"] = saved_expires


# ============================================================
# ★ ریاضی روز کاری
# ============================================================
def test_thursday_and_friday_are_weekend(clean_calendar):
    """در این سازمان پنجشنبه و جمعه تعطیل هفتگی هستند."""
    from config import Config

    assert set(Config.WEEKEND_DAYS) == {4, 5}

    assert working_days.is_weekend("2026/03/19") is True    # پنجشنبه
    assert working_days.is_weekend("2026/03/20") is True    # جمعه
    assert working_days.is_working_day("2026/03/19") is False
    assert working_days.is_working_day("2026/03/18") is True   # چهارشنبه


def test_add_working_days_skips_weekend(clean_calendar):
    # چهارشنبه + ۱ روز کاری = شنبه (پنجشنبه و جمعه رد می‌شوند)
    assert working_days.format_gregorian(
        working_days.add_working_days("2026/03/18", 1)
    ) == "2026/03/21"


def test_add_working_days_skips_holiday(clean_calendar):
    working_days._cache["dates"] = frozenset({"2026/03/21"})  # شنبه تعطیل

    assert working_days.format_gregorian(
        working_days.add_working_days("2026/03/19", 1)
    ) == "2026/03/22"


def test_count_working_days(clean_calendar):
    # پنجشنبه تا یکشنبه: شنبه و یکشنبه = ۲ روز کاری
    assert working_days.count_working_days("2026/03/19", "2026/03/22") == 2
    assert working_days.count_working_days("2026/03/22", "2026/03/19") == -2


def test_working_days_left(clean_calendar):
    assert working_days.working_days_left("2026/03/22", today="2026/03/19") == 2
    assert working_days.working_days_left("2026/03/19", today="2026/03/22") == -2


def test_next_working_day(clean_calendar):
    assert working_days.format_gregorian(
        working_days.next_working_day("2026/03/20")
    ) == "2026/03/21"


def test_invalid_and_zero_days(clean_calendar):
    assert working_days.add_working_days("2026/03/19", 0) == date(2026, 3, 19)
    assert working_days.add_working_days("نامعتبر", 3) is None
    assert working_days.parse_date("") is None


def test_month_status_shape(clean_calendar):
    days = working_days.month_status(1405, 1)

    assert len(days) == 31, "فروردین ۳۱ روز است"
    assert {day["state"] for day in days} <= {"working", "weekend", "holiday"}
    assert all(day["gregorian"].count("/") == 2 for day in days)


def test_month_status_uses_jalali_day_numbers(clean_calendar):
    """شمارهٔ روز باید شمسی باشد، نه میلادی."""
    days = working_days.month_status(1405, 1)

    assert days[0]["jalali"] == "1405/01/01"
    assert days[0]["gregorian"] == "2026/03/21"
    assert days[0]["day"] == 1
    assert days[-1]["day"] == 31


def test_month_status_marks_thursday_weekend(clean_calendar):
    days = working_days.month_status(1405, 1)
    weekends = [day for day in days if day["state"] == "weekend"]

    assert len(weekends) >= 4, "پنجشنبه‌های ماه باید آخر هفته باشند"


# ============================================================
# ★ تعطیلات در دیتابیس
# ============================================================
def test_seeded_fixed_holidays_exist(app_instance):
    from services.calendar import holiday_service

    with app_instance.app_context():
        holidays = holiday_service.list_for_year(1405)
        dates = {item["jalali_date"] for item in holidays}

    assert "1405/01/01" in dates
    assert "1405/01/13" in dates
    assert "1405/11/22" in dates


def test_seed_does_not_restore_deleted_holiday(app_instance):
    """حذف دستی تعطیلات نباید در ری‌استارت بعدی برگردد."""
    from database.seeds import holidays as seed_holidays
    from services.calendar import holiday_service

    with app_instance.app_context():
        target = next(
            item for item in holiday_service.list_for_year(1405)
            if item["jalali_date"] == "1405/01/12"
        )
        assert holiday_service.delete(target["id"]) is True

        seed_holidays.create_fixed_holidays()

        remaining = holiday_service.list_for_year(1405)
        assert all(item["jalali_date"] != "1405/01/12" for item in remaining)


def test_add_and_delete_holiday(app_instance):
    from services.calendar import holiday_service

    with app_instance.app_context():
        ok, error = holiday_service.create("1405/09/01", "تعطیل تست", "company")
        assert ok, error

        created = [
            item for item in holiday_service.list_for_year(1405)
            if item["jalali_date"] == "1405/09/01"
        ]
        assert len(created) == 1
        assert created[0]["kind"] == "company"

        assert holiday_service.delete(created[0]["id"]) is True
        remaining = [
            item for item in holiday_service.list_for_year(1405)
            if item["jalali_date"] == "1405/09/01"
        ]
        assert remaining == []


def test_duplicate_holiday_is_rejected(app_instance):
    from services.calendar import holiday_service

    with app_instance.app_context():
        ok, _ = holiday_service.create("1405/09/02", "تعطیل تکراری")
        assert ok

        duplicate, error = holiday_service.create("1405/09/02", "تکرار")
        assert duplicate is False
        assert "قبلاً" in error


def test_invalid_jalali_date_is_rejected(app_instance):
    from services.calendar import holiday_service

    with app_instance.app_context():
        ok, error = holiday_service.create("1405/13/40", "نامعتبر")
        assert ok is False

        ok, error = holiday_service.create("", "بدون تاریخ")
        assert ok is False


def test_persian_digits_are_accepted(app_instance):
    from services.calendar import holiday_service

    with app_instance.app_context():
        ok, error = holiday_service.create("۱۴۰۵/۱۰/۰۱", "تعطیل ارقام فارسی")
        assert ok, error
        holidays = holiday_service.list_for_year(1405)
        assert any(item["jalali_date"] == "1405/10/01" for item in holidays)


# ============================================================
# ★ مهلت پاسخ (SLA)
# ============================================================
def _create_group_and_subgroup(suffix, group_days, subgroup_days):
    from database.connection import get_connection

    connection = get_connection()
    try:
        group = connection.execute(
            """
            INSERT INTO document_groups (title, code, days_review, is_active)
            VALUES (?, ?, ?, 1)
            """,
            (f"گروه تست {suffix}", f"TG{suffix}", group_days),
        )
        group_id = group.lastrowid

        subgroup = connection.execute(
            """
            INSERT INTO document_subgroups (title, code, days_review, is_active)
            VALUES (?, ?, ?, 1)
            """,
            (f"زیرگروه تست {suffix}", f"TS{suffix}", subgroup_days),
        )
        subgroup_id = subgroup.lastrowid
        connection.commit()
    finally:
        connection.close()

    return group_id, subgroup_id


def test_sla_priority_subgroup_over_group(app_instance, clean_calendar):
    from services.documents import sla

    with app_instance.app_context():
        group_id, subgroup_id = _create_group_and_subgroup("a1", 5, 3)
        days, source = sla.resolve_days(group_id, subgroup_id)
        assert (days, source) == (3, "subgroup")


def test_sla_falls_back_to_group(app_instance, clean_calendar):
    from services.documents import sla

    with app_instance.app_context():
        group_id, subgroup_id = _create_group_and_subgroup("a2", 5, 0)
        days, source = sla.resolve_days(group_id, subgroup_id)
        assert (days, source) == (5, "group")


def test_sla_falls_back_to_default(app_instance, clean_calendar):
    from config import Config
    from services.documents import sla

    with app_instance.app_context():
        days, source = sla.resolve_days(None, None)
        assert source == "default"
        assert days == Config.DEFAULT_SLA_DAYS


def test_preview_skips_holidays(app_instance, clean_calendar):
    from services.documents import sla

    working_days._cache["dates"] = frozenset({"2026/03/21"})

    with app_instance.app_context():
        group_id, subgroup_id = _create_group_and_subgroup("a3", 0, 1)
        result = sla.preview(group_id, subgroup_id, "2026/03/19")

    # پنجشنبه + ۱ روز کاری با احتساب تعطیلی شنبه = یکشنبه
    assert result["due"] == "2026/03/22"
    assert result["days"] == 1
    assert result["source"] == "subgroup"


def test_apply_to_document_persists_sla(app_instance, clean_calendar):
    from database.connection import get_connection
    from services.documents import sla

    with app_instance.app_context():
        group_id, subgroup_id = _create_group_and_subgroup("a4", 0, 2)

        connection = get_connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO documents (subject, date_received, group_id, subgroup_id)
                VALUES (?, ?, ?, ?)
                """,
                ("سند تست SLA", "2026/03/19", group_id, subgroup_id),
            )
            document_id = cursor.lastrowid
            connection.commit()
        finally:
            connection.close()

        result = sla.apply_to_document(document_id)
        assert result["days"] == 2

        connection = get_connection()
        try:
            row = connection.execute(
                "SELECT sla_days, sla_source, response_due_date FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
        finally:
            connection.close()

    assert row["sla_days"] == 2
    assert row["sla_source"] == "subgroup"
    assert row["response_due_date"] == "2026/03/22"   # شنبه و یکشنبه


# ============================================================
# ★ صفحهٔ تقویم
# ============================================================
def _admin(client):
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["username"] = "admin"
        session["role"] = "admin"
    return client


def test_calendar_page_renders(client):
    _admin(client)
    response = client.get("/calendar/?year=1405&month=1")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "تقویم کاری" in html
    assert "فروردین" in html
    assert "محاسبهٔ مهلت پاسخ" not in html
    assert "calendar-grid" in html
    assert '<option value="1" selected>' in html.replace("selected=\"selected\"", "selected")
    assert "اردیبهشت" in html
    assert "th-weekend" in html


def test_calendar_page_has_holiday_cells(client):
    _admin(client)
    html = client.get("/calendar/?year=1405&month=1").get_data(as_text=True)

    assert "day-holiday" in html
    assert "عید نوروز" in html


def test_calendar_add_holiday_via_http(client):
    _admin(client)
    response = client.post(
        "/calendar/add",
        data={"holiday_date": "1405/09/05", "title": "تعطیل HTTP", "kind": "company"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "month=9" in response.headers["Location"]
    html = client.get("/calendar/?year=1405&month=9").get_data(as_text=True)
    assert "تعطیل HTTP" in html


def test_calendar_requires_admin_role(client):
    with client.session_transaction() as session:
        session["user_id"] = 5
        session["username"] = "expert"
        session["role"] = "expert"

    assert client.get("/calendar/").status_code == 403


def test_calendar_no_longer_shows_deadline_calculator(client):
    _admin(client)
    html = client.get("/calendar/?month=1&year=1405").get_data(as_text=True)

    assert "محاسبهٔ مهلت پاسخ" not in html
    assert "calcGroup" not in html


def test_invalid_date_is_rejected_by_form(client):
    _admin(client)
    response = client.post(
        "/calendar/add",
        data={"holiday_date": "1405/13/40", "title": "تاریخ غلط", "kind": "official"},
        follow_redirects=True,
    )

    html = response.get_data(as_text=True)
    assert "نامعتبر" in html


def test_sidebar_has_calendar_link_for_admin(client):
    _admin(client)
    html = client.get("/search/").get_data(as_text=True)

    assert 'href="/calendar/"' in html
    assert "تقویم کاری" in html


def test_sidebar_hides_calendar_for_expert(client):
    with client.session_transaction() as session:
        session["user_id"] = 5
        session["username"] = "expert"
        session["role"] = "expert"

    html = client.get("/search/").get_data(as_text=True)
    assert 'href="/calendar/"' not in html


def test_calendar_days_are_clickable(client):
    _admin(client)
    html = client.get("/calendar/?year=1405&month=1").get_data(as_text=True)

    assert 'action="/calendar/toggle"' in html
    assert 'name="date" value="1405/01/01"' in html
    assert html.count("day-toggle-form") == 31
    assert 'id="holidayReasonDialog"' in html
    assert 'name="reason"' in html


def test_toggle_day_on_and_off(client):
    _admin(client)
    from database.repositories import holidays as holidays_repo
    from helpers.date_helper import DateHelper

    date = "1405/09/15"
    gregorian_date = DateHelper.convert_to_gregorian(date)

    reason = "تعمیرات اضطراری"
    response = client.post(
        "/calendar/toggle",
        data={"date": date, "reason": reason},
        follow_redirects=False,
    )
    assert response.status_code == 302

    holiday = holidays_repo.get_by_date(gregorian_date)
    assert holiday is not None
    assert holiday["title"] == "تعطیل دستی"
    assert holiday["reason"] == reason

    html = client.get("/calendar/?year=1405&month=9").get_data(as_text=True)
    assert reason in html

    client.post("/calendar/toggle", data={"date": date})

    assert holidays_repo.get_by_date(gregorian_date) is None


def test_toggle_requires_a_reason_when_adding_holiday(client):
    _admin(client)

    response = client.post(
        "/calendar/toggle",
        data={"date": "1405/09/15", "reason": "  "},
        follow_redirects=True,
    )

    assert "علت تعطیلی را وارد کنید" in response.get_data(as_text=True)


def test_month_navigation_does_not_keep_removed_calculator_parameters(client):
    _admin(client)
    html = client.get("/calendar/?year=1405&month=2").get_data(as_text=True)

    assert "year=1405&amp;month=1" in html
    assert "امروز" in html


def test_calendar_holiday_migration_adds_reason_column():
    from database.tables.calendar_holidays import migrate

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("CREATE TABLE calendar_holidays (id INTEGER PRIMARY KEY)")
        migrate(connection.cursor())
        columns = {
            column["name"]
            for column in connection.execute("PRAGMA table_info(calendar_holidays)")
        }
        assert "reason" in columns
    finally:
        connection.close()


def test_toggle_invalid_date_is_safe(client):
    _admin(client)
    response = client.post(
        "/calendar/toggle", data={"date": "نامعتبر"}, follow_redirects=True
    )

    assert response.status_code == 200
    assert "نامعتبر" in response.get_data(as_text=True)


def test_calendar_module_follows_project_structure(app_instance):
    """ماژول جدید باید همان الگوی routes/services/forms/database/templates را داشته باشد."""
    import os

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    expected = [
        "routes/calendar/__init__.py",
        "routes/calendar/calendar_routes.py",
        "services/calendar/__init__.py",
        "services/calendar/holiday_service.py",
        "services/calendar/working_days.py",
        "forms/calendar/__init__.py",
        "forms/calendar/forms.py",
        "database/tables/calendar_holidays.py",
        "database/repositories/holidays.py",
        "database/repositories/document_groups.py",
        "database/seeds/holidays.py",
        "templates/calendar/index.html",
        "static/css/pages/calendar.css",
        "static/js/pages/calendar/index.js",
        "tests/test_calendar.py",
    ]

    missing = [path for path in expected if not os.path.isfile(os.path.join(root, path))]
    assert not missing, f"فایل‌های الگوی ماژول پیدا نشد: {missing}"
