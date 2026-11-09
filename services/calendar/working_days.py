"""محاسبهٔ روزهای کاری با احتساب تعطیلات رسمی و آخر هفته.

قواعد:

* تاریخ‌ها در دیتابیس میلادی و به شکل ``YYYY/MM/DD`` هستند.
* تعطیلات هفتگی از ``Config.WEEKEND_DAYS`` می‌آید (ISO: دوشنبه=۱ … یکشنبه=۷).
  پیش‌فرض فقط جمعه؛ اگر سازمان پنجشنبه تعطیل است با
  ``SSPE_WEEKEND_DAYS=4,5`` قابل تغییر است.
* تعطیلات رسمی از جدول ``calendar_holidays`` خوانده و ۶۰ ثانیه کش می‌شود.
* مهلت = «شروع + N روز کاری»؛ روز شروع به‌عنوان روز صفر در نظر گرفته می‌شود.
"""

import time
from datetime import date, datetime, timedelta

import jdatetime

from config import Config
from database.repositories import holidays as holidays_repo
from helpers.date_helper import DateHelper

#: مدت اعتبار کش تعطیلات (ثانیه)
CACHE_TTL = 60

#: حداکثر گشت برای جلوگیری از حلقهٔ بی‌پایان در صورت پیکربندی غلط
_MAX_SCAN_DAYS = 3650

_cache = {"expires": 0.0, "dates": frozenset()}


# ============================================================
# ★ تعطیلات
# ============================================================
def _weekend_days():
    return {int(day) for day in Config.WEEKEND_DAYS}


def load_holidays():
    """مجموعهٔ تاریخ‌های تعطیل فعال (میلادی YYYY/MM/DD) با کش کوتاه."""
    now = time.monotonic()
    if now < _cache["expires"]:
        return _cache["dates"]

    dates = set()
    try:
        dates = holidays_repo.all_active_dates()
    except Exception:
        # جدول ممکن است هنوز ساخته نشده باشد؛ تقویم نباید برنامه را بشکند
        dates = set()

    _cache["dates"] = frozenset(dates)
    _cache["expires"] = now + CACHE_TTL
    return _cache["dates"]


def invalidate_cache():
    """بعد از افزودن/حذف تعطیلات صدا زده می‌شود."""
    _cache["expires"] = 0


# ============================================================
# ★ تبدیل تاریخ
# ============================================================
def parse_date(value):
    """تبدیل ورودی (شمسی یا میلادی) به ``date`` میلادی؛ None اگر نامعتبر بود."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    normalized = DateHelper.convert_to_gregorian(value)
    if not normalized:
        return None

    try:
        return datetime.strptime(str(normalized).strip(), "%Y/%m/%d").date()
    except (ValueError, TypeError):
        return None


def format_gregorian(value):
    """خروجی استاندارد دیتابیس: YYYY/MM/DD میلادی."""
    parsed = parse_date(value)
    return parsed.strftime("%Y/%m/%d") if parsed else None


def format_jalali(value):
    """نمایش شمسی با ارقام فارسی برای قالب‌ها."""
    parsed = parse_date(value)
    return DateHelper.format_jalali(parsed.strftime("%Y/%m/%d")) if parsed else ""


# ============================================================
# ★ روز کاری
# ============================================================
def is_weekend(value):
    parsed = parse_date(value)
    return bool(parsed) and parsed.isoweekday() in _weekend_days()


def is_holiday(value):
    parsed = parse_date(value)
    return bool(parsed) and parsed.strftime("%Y/%m/%d") in load_holidays()


def is_working_day(value):
    parsed = parse_date(value)
    if not parsed:
        return False
    if parsed.isoweekday() in _weekend_days():
        return False
    return parsed.strftime("%Y/%m/%d") not in load_holidays()


def next_working_day(value):
    """اولین روز کاری از تاریخ داده‌شده (شامل خودش)."""
    parsed = parse_date(value)
    if not parsed:
        return None

    for _ in range(_MAX_SCAN_DAYS):
        if is_working_day(parsed):
            return parsed
        parsed += timedelta(days=1)
    return None


# ============================================================
# ★ جمع و تفریق روز کاری
# ============================================================
def add_working_days(start, days):
    """``start`` + ``days`` روز کاری؛ اگر days صفر/منفی باشد خود start برمی‌گردد."""
    parsed = parse_date(start)
    if parsed is None:
        return None

    try:
        remaining = int(days or 0)
    except (TypeError, ValueError):
        remaining = 0

    if remaining <= 0:
        return parsed

    current = parsed
    for _ in range(_MAX_SCAN_DAYS):
        current += timedelta(days=1)
        if is_working_day(current):
            remaining -= 1
            if remaining == 0:
                return current
    return None


def count_working_days(start, end):
    """تعداد روز کاری در بازهٔ ``(start, end]`` — مثبت برای end > start."""
    start_date = parse_date(start)
    end_date = parse_date(end)
    if start_date is None or end_date is None:
        return 0
    if end_date == start_date:
        return 0

    if end_date < start_date:
        return -count_working_days(end_date, start_date)

    return sum(
        1
        for offset in range(1, (end_date - start_date).days + 1)
        if is_working_day(start_date + timedelta(days=offset))
    )


def working_days_left(due, today=None):
    """روزهای کاری باقی‌مانده تا مهلت؛ منفی یعنی گذشته از مهلت."""
    reference = parse_date(today) or date.today()
    return count_working_days(reference, due)


# ============================================================
# ★ ساخت «ماه کاری» برای نمایش تقویم
# ============================================================
def month_status(jalali_year, jalali_month):
    """وضعیت روزهای یک ماه شمسی: working / weekend / holiday."""
    try:
        first = jdatetime.date(jalali_year, jalali_month, 1)
    except ValueError:
        return []

    if jalali_month == 12:
        next_first = jdatetime.date(jalali_year + 1, 1, 1)
    else:
        next_first = jdatetime.date(jalali_year, jalali_month + 1, 1)

    start_gregorian = first.togregorian()
    end_gregorian = next_first.togregorian()

    days = []
    current = start_gregorian
    while current < end_gregorian:
        gregorian_text = current.strftime("%Y/%m/%d")
        jalali_date = jdatetime.date.fromgregorian(date=current)

        # ★ تعطیلی ثبت‌شده بر وضعیت آخر هفته اولویت دارد تا کاربر بازخورد ببیند
        if gregorian_text in load_holidays():
            state = "holiday"
        elif current.isoweekday() in _weekend_days():
            state = "weekend"
        else:
            state = "working"

        days.append(
            {
                "jalali": jalali_date.strftime("%Y/%m/%d"),
                "day": jalali_date.day,
                "gregorian": gregorian_text,
                "state": state,
            }
        )
        current += timedelta(days=1)

    return days
