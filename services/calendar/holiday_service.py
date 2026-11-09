"""مدیریت تعطیلات تقویم — منطق کسب‌وکار روی لایهٔ repository."""

from database.repositories import holidays as holidays_repo
from helpers.date_helper import DateHelper

from . import working_days

ALLOWED_KINDS = ("official", "company", "other")

KIND_LABELS = {
    "official": "تعطیل رسمی",
    "company": "تعطیل سازمانی",
    "other": "سایر",
}


def parse_jalali(value):
    """«۱۴۰۵/۰۱/۰۱» → jdatetime.date؛ None اگر نامعتبر بود."""
    return DateHelper.parse_jalali_date(value)


def list_years():
    return holidays_repo.list_years()


def list_for_year(year):
    return holidays_repo.list_for_year(year)


def get(holiday_id):
    return holidays_repo.get(holiday_id)


def create(jalali_date, title, kind="official", user_id=None):
    """افزودن تعطیلی؛ خروجی: (موفقیت، پیام خطا)."""
    jdate = parse_jalali(jalali_date)
    if jdate is None:
        return False, "تاریخ شمسی نامعتبر است (نمونه: ۱۴۰۵/۰۱/۰۱)."

    title = (title or "").strip()
    if not title:
        return False, "عنوان تعطیلی الزامی است."

    if kind not in ALLOWED_KINDS:
        kind = "official"

    status = holidays_repo.create(
        holiday_date=jdate.togregorian().strftime("%Y/%m/%d"),
        jalali_date=jdate.strftime("%Y/%m/%d"),
        jalali_year=jdate.year,
        title=title,
        kind=kind,
        created_by=user_id,
    )

    if status == "duplicate":
        return False, "این تاریخ قبلاً به‌عنوان تعطیلی ثبت شده است."
    if status != "created":
        return False, "ثبت تعطیلی انجام نشد؛ دوباره تلاش کنید."

    working_days.invalidate_cache()
    return True, ""


def delete(holiday_id):
    deleted = holidays_repo.delete(holiday_id)
    if deleted:
        working_days.invalidate_cache()
    return deleted


def toggle(jalali_date, user_id=None, reason=None):
    """کلیک روی روز تقویم: تعطیل ↔ غیرتعطیل.

    خروجی: (موفقیت، پیام، وضعیت جدید) که وضعیت جدید ``on``/``off`` است.
    """
    jdate = parse_jalali(jalali_date)
    if jdate is None:
        return False, "تاریخ شمسی نامعتبر است.", None

    gregorian = jdate.togregorian().strftime("%Y/%m/%d")
    existing = holidays_repo.get_by_date(gregorian)

    if existing:
        if not holidays_repo.delete(existing["id"]):
            return False, "حذف تعطیلی انجام نشد؛ دوباره تلاش کنید.", None
        working_days.invalidate_cache()
        return True, "این روز از تعطیلات خارج شد.", "off"

    reason = (reason or "").strip()
    if not reason:
        return False, "علت تعطیلی را وارد کنید.", None
    if len(reason) > 500:
        return False, "علت تعطیلی نباید بیشتر از ۵۰۰ نویسه باشد.", None

    status = holidays_repo.create(
        holiday_date=gregorian,
        jalali_date=jdate.strftime("%Y/%m/%d"),
        jalali_year=jdate.year,
        title="تعطیل دستی",
        kind="company",
        created_by=user_id,
        reason=reason,
    )

    if status != "created":
        return False, "تغییر وضعیت انجام نشد؛ دوباره تلاش کنید.", None

    working_days.invalidate_cache()
    return True, "این روز تعطیل شد.", "on"


def create_many(items):
    """درج گروهی (برای seed): items = [(jalali_date, title, kind), …]."""
    created = 0
    for jalali_date, title, kind in items:
        ok, _ = create(jalali_date, title, kind)
        if ok:
            created += 1
    return created
