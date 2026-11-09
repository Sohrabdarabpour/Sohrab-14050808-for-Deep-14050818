"""تقویم کاری: تعطیلات و نمایش ماه شمسی."""

from datetime import datetime

import jdatetime
from flask import (
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from config import Config
from forms.calendar import HolidayForm
from helpers.date_helper import now_tehran
from security.decorators import role_required
from services.calendar import holiday_service, working_days

from . import calendar_bp

PERSIAN_MONTHS = [
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
]

WEEKDAY_LABELS = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]

#: نام فارسی روزهای هفته بر اساس ISO (دوشنبه=۱ … یکشنبه=۷)
ISO_WEEKDAY_LABELS = {
    1: "دوشنبه",
    2: "سه‌شنبه",
    3: "چهارشنبه",
    4: "پنجشنبه",
    5: "جمعه",
    6: "شنبه",
    7: "یکشنبه",
}


def _current_jalali():
    return jdatetime.date.fromgregorian(date=now_tehran().date())


def _saturday_offset(gregorian_date):
    """جای روز در هفتهٔ ایرانی (شنبه=۰ … جمعه=۶)."""
    return (datetime.strptime(gregorian_date, "%Y/%m/%d").isoweekday() + 1) % 7


def _weekend_indexes():
    """ایندکس ستون‌های آخر هفته در جدول شمسی (شنبه=۰)."""
    return [(_iso + 1) % 7 for _iso in Config.WEEKEND_DAYS]


def _build_weeks(days):
    """تبدیل روزهای ماه به هفته‌های هفت‌ستونه با خانه‌های خالی."""
    if not days:
        return []

    cells = [None] * _saturday_offset(days[0]["gregorian"]) + days
    while len(cells) % 7:
        cells.append(None)

    return [cells[index:index + 7] for index in range(0, len(cells), 7)]


@calendar_bp.route("/", methods=["GET"])
@role_required("admin", "manager")
def index():
    """نمایش ماه شمسی و مدیریت تعطیلات."""
    today = _current_jalali()

    years = holiday_service.list_years()
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month
    month = min(max(month, 1), 12)

    if year not in years:
        years.append(year)
        years.sort(reverse=True)

    days = working_days.month_status(year, month)
    weeks = _build_weeks(days)

    holidays = holiday_service.list_for_year(year)
    holiday_titles = {item["holiday_date"]: item["title"] for item in holidays}
    holiday_reasons = {
        item["holiday_date"]: item["reason"] for item in holidays if item["reason"]
    }

    stats = {
        "working": sum(1 for day in days if day["state"] == "working"),
        "weekend": sum(1 for day in days if day["state"] == "weekend"),
        "holiday": sum(1 for day in days if day["state"] == "holiday"),
    }

    weekend_label = " و ".join(
        ISO_WEEKDAY_LABELS[day]
        for day in sorted(Config.WEEKEND_DAYS)
        if day in ISO_WEEKDAY_LABELS
    )

    return render_template(
        "calendar/index.html",
        form=HolidayForm(),
        weekend_label=weekend_label,
        weekend_indexes=_weekend_indexes(),
        years=years,
        year=year,
        month=month,
        month_name=PERSIAN_MONTHS[month - 1],
        month_names=PERSIAN_MONTHS,
        weekday_labels=WEEKDAY_LABELS,
        weeks=weeks,
        days=days,
        stats=stats,
        holidays=holidays,
        holiday_titles=holiday_titles,
        holiday_reasons=holiday_reasons,
        today=today.strftime("%Y/%m/%d"),
        today_year=today.year,
        today_month=today.month,
        kind_labels=holiday_service.KIND_LABELS,
    )


@calendar_bp.route("/add", methods=["POST"])
@role_required("admin", "manager")
def add_holiday():
    """افزودن تعطیلی جدید (اعتبارسنجی در فرم انجام می‌شود)."""
    form = HolidayForm()

    if not form.validate_on_submit():
        for messages in form.errors.values():
            for message in messages:
                flash(message, "danger")
        return redirect(url_for("calendar.index", year=_current_jalali().year))

    ok, error = holiday_service.create(
        jalali_date=form.holiday_date.data,
        title=form.title.data,
        kind=form.kind.data,
        user_id=session.get("user_id"),
    )

    if ok:
        flash("تعطیلی به تقویم اضافه شد.", "success")
    else:
        flash(error, "danger")

    parsed = holiday_service.parse_jalali(form.holiday_date.data)
    today = _current_jalali()
    return redirect(
        url_for(
            "calendar.index",
            year=parsed.year if parsed else today.year,
            month=parsed.month if parsed else today.month,
        )
    )


@calendar_bp.route("/toggle", methods=["POST"])
@role_required("admin", "manager")
def toggle_holiday():
    """کلیک روی روز تقویم: تعطیل یا غیرتعطیل کردن آن روز."""
    value = request.form.get("date")

    ok, message, _state = holiday_service.toggle(
        value,
        session.get("user_id"),
        request.form.get("reason"),
    )
    flash(message, "success" if ok else "danger")

    parsed = holiday_service.parse_jalali(value) or _current_jalali()
    return redirect(
        url_for("calendar.index", year=parsed.year, month=parsed.month)
    )


@calendar_bp.route("/<int:holiday_id>/delete", methods=["POST"])
@role_required("admin", "manager")
def delete_holiday(holiday_id):
    """حذف تعطیلی."""
    holiday = holiday_service.get(holiday_id)
    year = holiday["jalali_year"] if holiday else _current_jalali().year

    if holiday_service.delete(holiday_id):
        flash("تعطیلی حذف شد.", "success")
    else:
        flash("تعطیلی مورد نظر پیدا نشد.", "danger")

    month = None
    if holiday and holiday.get("jalali_date"):
        parts = str(holiday["jalali_date"]).split("/")
        if len(parts) == 3:
            try:
                month = int(parts[1])
            except (TypeError, ValueError):
                month = None

    return redirect(url_for("calendar.index", year=year, month=month))
