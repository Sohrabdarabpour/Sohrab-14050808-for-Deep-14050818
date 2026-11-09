"""تعطیلات ثابت تقویم (بر اساس تاریخ شمسی).

تعطیلات قمری (عید فطر، محرم، …) هر سال جابه‌جا می‌شوند و باید از صفحهٔ
تقویم یا فایل ورودی توسط مدیر ثبت شوند؛ اینجا فقط تعطیلات ثابت شمسی
seed می‌شوند.

این لایه فقط با repository و helper کار می‌کند (بدون وابستگی به services).
"""

from database.repositories import holidays as holidays_repo
from helpers.date_helper import DateHelper

#: (ماه/روز شمسی، عنوان)
FIXED_HOLIDAYS = [
    ("01/01", "عید نوروز"),
    ("01/02", "عید نوروز"),
    ("01/03", "عید نوروز"),
    ("01/04", "عید نوروز"),
    ("01/12", "روز جمهوری اسلامی"),
    ("01/13", "روز طبیعت"),
    ("03/14", "رحلت حضرت امام خمینی"),
    ("03/15", "قیام ۱۵ خرداد"),
    ("11/22", "پیروزی انقلاب اسلامی"),
    ("12/29", "ملی شدن صنعت نفت"),
]

#: سال‌هایی که از پیش پر می‌شوند
SEED_YEARS = (1404, 1405, 1406)


def create_fixed_holidays():
    """درج تعطیلات ثابت فقط برای سال‌هایی که هنوز هیچ تعطیلی‌ای ندارند.

    اگر برای یک سال حتی یک رکورد وجود داشته باشد، آن سال دست‌نخورده می‌ماند تا
    حذف/تغییر دستی مدیر در ری‌استارت بعدی برنگردد.
    """
    seeded_years = set(holidays_repo.list_years())
    created = 0

    for year in SEED_YEARS:
        if year in seeded_years:
            continue

        for month_day, title in FIXED_HOLIDAYS:
            jdate = DateHelper.parse_jalali_date(f"{year}/{month_day}")
            if jdate is None:
                continue

            status = holidays_repo.create(
                holiday_date=jdate.togregorian().strftime("%Y/%m/%d"),
                jalali_date=jdate.strftime("%Y/%m/%d"),
                jalali_year=jdate.year,
                title=title,
                kind="official",
            )
            if status == "created":
                created += 1

    return created


def run():
    created = create_fixed_holidays()
    if created:
        print(f"✅ {created} تعطیلات ثابت تقویم ایجاد شد")
