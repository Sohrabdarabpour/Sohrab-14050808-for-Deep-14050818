from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import jdatetime


# ════════════════════════════════════════════════════════════════
# ★ منطقه زمانی ایران — ثابت مرکزی
# ════════════════════════════════════════════════════════════════
TEHRAN_TZ = ZoneInfo("Asia/Tehran")


def now_tehran() -> datetime:
    """زمان فعلی ایران به صورت naive (بدون tzinfo) برای ذخیره در DB"""
    return datetime.now(TEHRAN_TZ).replace(tzinfo=None, microsecond=0)


def now_tehran_str() -> str:
    """زمان فعلی ایران به صورت رشته برای DB"""
    return now_tehran().strftime("%Y-%m-%d %H:%M:%S")


class DateHelper:
    """
    Helper تاریخ/زمان — با پشتیبانی کامل از منطقه زمانی ایران
    
    ★ نکته مهم: تمام ورودی‌های datetime از دیتابیس باید به وقت ایران (naive) باشند
    """

    # ════════════════════════════════════════════════════════════
    # ★ کمکی‌های عمومی — ارقام
    # ════════════════════════════════════════════════════════════
    @staticmethod
    def normalize_digits(value):
        if value is None:
            return ""
        value = str(value)
        persian_digits = "۰۱۲۳۴۵۶۷۸۹"
        arabic_digits  = "٠١٢٣٤٥٦٧٨٩"
        english_digits = "0123456789"
        for index, digit in enumerate(english_digits):
            value = value.replace(persian_digits[index], digit)
            value = value.replace(arabic_digits[index], digit)
        return value

    @staticmethod
    def to_persian_digits(value):
        english_digits = "0123456789"
        persian_digits = "۰۱۲۳۴۵۶۷۸۹"
        value = str(value)
        return value.translate(
            str.maketrans(english_digits, persian_digits)
        )

    # ════════════════════════════════════════════════════════════
    # ★ Excel serial → Gregorian
    # ════════════════════════════════════════════════════════════
    @staticmethod
    def convert_excel_serial_to_gregorian(value):
        try:
            serial = float(value)
        except (ValueError, TypeError):
            return None
        if serial < 1 or serial > 100000:
            return None
        try:
            excel_base = date(1899, 12, 30)
            converted_date = excel_base + timedelta(days=serial)
            return converted_date.strftime("%Y/%m/%d")
        except (ValueError, OverflowError):
            return None

    # ════════════════════════════════════════════════════════════
    # ★ تبدیل به میلادی
    # ════════════════════════════════════════════════════════════
    @staticmethod
    def convert_to_gregorian(value):
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value.strftime("%Y/%m/%d")
        if isinstance(value, date):
            return value.strftime("%Y/%m/%d")

        value = DateHelper.normalize_digits(value).strip()
        if value == "":
            return None
        value = value.replace("-", "/")

        try:
            numeric_value = float(value)
            if numeric_value.is_integer():
                excel_date = DateHelper.convert_excel_serial_to_gregorian(
                    int(numeric_value)
                )
                if excel_date:
                    return excel_date
        except (ValueError, TypeError):
            pass

        try:
            parts = value.split("/")
            if len(parts) != 3:
                return value
            year  = int(parts[0])
            month = int(parts[1])
            day   = int(parts[2].split(" ")[0])

            if year >= 1700:
                gregorian_date = date(year, month, day)
                return gregorian_date.strftime("%Y/%m/%d")

            gregorian_date = jdatetime.date(year, month, day).togregorian()
            return gregorian_date.strftime("%Y/%m/%d")
        except (ValueError, TypeError):
            return value

    # ════════════════════════════════════════════════════════════
    # ★ format_jalali — فقط تاریخ
    # ════════════════════════════════════════════════════════════
    @staticmethod
    def format_jalali(value):
        if value is None or value == "":
            return ""

        if isinstance(value, datetime):
            # ★ اگر aware بود، به تهران تبدیل کن و naive کن
            if value.tzinfo is not None:
                value = value.astimezone(TEHRAN_TZ).replace(tzinfo=None)
            jalali_date = jdatetime.datetime.fromgregorian(datetime=value)
            result = jalali_date.strftime("%Y/%m/%d")
            return DateHelper.to_persian_digits(result)

        if isinstance(value, date):
            jalali_date = jdatetime.date.fromgregorian(date=value)
            result = jalali_date.strftime("%Y/%m/%d")
            return DateHelper.to_persian_digits(result)

        value = DateHelper.normalize_digits(value).strip()
        if value == "":
            return ""
        value = value.replace("-", "/")

        try:
            numeric_value = float(value)
            if numeric_value.is_integer():
                excel_date = DateHelper.convert_excel_serial_to_gregorian(
                    int(numeric_value)
                )
                if excel_date:
                    value = excel_date
        except (ValueError, TypeError):
            pass

        try:
            parts = value.split("/")
            if len(parts) != 3:
                return value

            year  = int(parts[0])
            month = int(parts[1])
            day   = int(parts[2].split(" ")[0])

            if year < 1700:
                result = f"{year:04d}/{month:02d}/{day:02d}"
                return DateHelper.to_persian_digits(result)

            gregorian_date = date(year, month, day)
            jalali_date = jdatetime.date.fromgregorian(date=gregorian_date)
            result = jalali_date.strftime("%Y/%m/%d")
            return DateHelper.to_persian_digits(result)
        except (ValueError, TypeError):
            return value

    # ════════════════════════════════════════════════════════════
    # ★ format_jalali_datetime — ★★★ نسخه اصلاح‌شده با timezone ★★★
    # ════════════════════════════════════════════════════════════
    @staticmethod
    def format_jalali_datetime(value, show_time=True):
        """
        تاریخ جلالی + ساعت (اختیاری)
        
        ★★★ نکات مهم ★★★
        - اگر value یک datetime aware (با tzinfo) باشد → به تهران تبدیل می‌شود
        - اگر value یک datetime naive باشد → فرض می‌شود به وقت ایران است
        - اگر رشته باشد، تلاش می‌کنیم parse کنیم
        """
        if value is None or value == "":
            return ""

        # ─── اگر رشته است، parse کن ───
        if isinstance(value, str):
            value = DateHelper.normalize_digits(value).strip()
            if value == "":
                return ""

            # ★ تلاش برای parse با فرمت‌های مختلف
            parsed = None
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y/%m/%d %H:%M",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
            ):
                try:
                    parsed = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue

            # اگر parse نشد، مقدار اصلی را برگردان
            if parsed is None:
                try:
                    parsed = datetime.fromisoformat(value)
                except ValueError:
                    return value

            value = parsed

        # ─── اگر datetime است ───
        if isinstance(value, datetime):
            # ★ اگر aware بود، به تهران تبدیل کن
            if value.tzinfo is not None:
                value = value.astimezone(TEHRAN_TZ).replace(tzinfo=None)

            jalali_dt = jdatetime.datetime.fromgregorian(datetime=value)

            if show_time:
                result = jalali_dt.strftime("%Y/%m/%d - %H:%M")
            else:
                result = jalali_dt.strftime("%Y/%m/%d")

            return DateHelper.to_persian_digits(result)

        # ─── اگر date است ───
        if isinstance(value, date):
            jalali_d = jdatetime.date.fromgregorian(date=value)
            return DateHelper.to_persian_digits(jalali_d.strftime("%Y/%m/%d"))

        return str(value)

    # ════════════════════════════════════════════════════════════
    # ★ get_jalali_year
    # ════════════════════════════════════════════════════════════
    @staticmethod
    def get_jalali_year(value):
        if value is None or value == "":
            return None

        if isinstance(value, datetime):
            if value.tzinfo is not None:
                value = value.astimezone(TEHRAN_TZ).replace(tzinfo=None)
            return jdatetime.datetime.fromgregorian(datetime=value).year

        if isinstance(value, date):
            return jdatetime.date.fromgregorian(date=value).year

        normalized_value = DateHelper.normalize_digits(value).strip()
        if normalized_value == "":
            return None

        excel_date = DateHelper.convert_excel_serial_to_gregorian(
            normalized_value
        )
        if excel_date:
            value = excel_date
        else:
            value = normalized_value

        value = value.replace("-", "/")

        try:
            parts = value.split("/")
            if len(parts) != 3:
                return None

            year  = int(parts[0])
            month = int(parts[1])
            day   = int(parts[2].split(" ")[0])

            if year < 1700:
                # ورودی از قبل شمسی است
                return year

            # ورودی میلادی است (مثل 2026/04/25) → سال شمسی
            return jdatetime.date.fromgregorian(date=date(year, month, day)).year
        except (ValueError, TypeError):
            return None

    # ════════════════════════════════════════════════════════════
    # ★ parse_jalali_date
    # ════════════════════════════════════════════════════════════
    @staticmethod
    def parse_jalali_date(value):
        """«۱۴۰۵/۰۱/۰۱» یا «1405-01-01» → jdatetime.date؛ None اگر نامعتبر بود."""
        if value is None or value == "":
            return None

        text = DateHelper.normalize_digits(str(value)).strip().replace("-", "/")
        parts = text.split("/")
        if len(parts) != 3:
            return None

        try:
            year, month, day = (int(part) for part in parts)
            return jdatetime.date(year, month, day)
        except (ValueError, TypeError):
            return None

    # ════════════════════════════════════════════════════════════
    # ★ get_gregorian_range_from_jalali_year
    # ════════════════════════════════════════════════════════════
    @staticmethod
    def get_gregorian_range_from_jalali_year(year):
        if year is None or year == "" or year == "all":
            return None

        year = DateHelper.normalize_digits(year)

        try:
            year = int(year)
        except (ValueError, TypeError):
            return None

        start_gregorian = jdatetime.date(year, 1, 1).togregorian()
        end_gregorian   = jdatetime.date(year + 1, 1, 1).togregorian()

        return (
            start_gregorian.strftime("%Y/%m/%d"),
            end_gregorian.strftime("%Y/%m/%d"),
        )

    # ════════════════════════════════════════════════════════════
    # ★ get_jalali_month
    # ════════════════════════════════════════════════════════════
    @staticmethod
    def get_jalali_month(value):
        """
        ★ استخراج ماه شمسی از هر فرمت (میلادی، شمسی، Excel serial)
        خروجی: عدد 1 تا 12 یا None
        """
        if value is None or value == "":
            return None

        if isinstance(value, datetime):
            if value.tzinfo is not None:
                value = value.astimezone(TEHRAN_TZ).replace(tzinfo=None)
            return jdatetime.datetime.fromgregorian(datetime=value).month

        if isinstance(value, date):
            return jdatetime.date.fromgregorian(date=value).month

        normalized = DateHelper.normalize_digits(value).strip()
        if normalized == "":
            return None

        excel_date = DateHelper.convert_excel_serial_to_gregorian(normalized)
        if excel_date:
            value = excel_date
        else:
            value = normalized

        value = value.replace("-", "/")

        try:
            parts = value.split("/")
            if len(parts) != 3:
                return None

            year  = int(parts[0])
            month = int(parts[1])
            day   = int(parts[2].split(" ")[0])

            if year < 1700:
                return month

            return jdatetime.date(year, month, day).month
        except (ValueError, TypeError):
            return None

    # ════════════════════════════════════════════════════════════
    # ★ کمکی‌های جدید — برای سرویس‌ها
    # ════════════════════════════════════════════════════════════
    @staticmethod
    def parse_db_datetime(value):
        """
        ★ پارس امن زمان از دیتابیس
        
        ورودی: رشته مثل "2026-10-11 11:37:00" یا datetime یا None
        خروجی: datetime naive به وقت ایران یا None
        """
        if value is None or value == "":
            return None

        if isinstance(value, datetime):
            # اگر aware بود، به تهران تبدیل کن
            if value.tzinfo is not None:
                return value.astimezone(TEHRAN_TZ).replace(tzinfo=None)
            return value

        if isinstance(value, date):
            return datetime(value.year, value.month, value.day)

        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None

            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y/%m/%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y/%m/%d %H:%M",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%d",
                "%Y/%m/%d",
            ):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue

            try:
                parsed = datetime.fromisoformat(value)
                if parsed.tzinfo is not None:
                    parsed = parsed.astimezone(TEHRAN_TZ).replace(tzinfo=None)
                return parsed
            except ValueError:
                return None

        return None

    @staticmethod
    def format_db_datetime(dt_value) -> str:
        """
        ★ تبدیل datetime به رشته برای ذخیره در DB (به وقت ایران)
        """
        if not dt_value:
            return now_tehran_str()

        if isinstance(dt_value, datetime):
            if dt_value.tzinfo is not None:
                dt_value = dt_value.astimezone(TEHRAN_TZ).replace(tzinfo=None)
            return dt_value.strftime("%Y-%m-%d %H:%M:%S")

        if isinstance(dt_value, str):
            parsed = DateHelper.parse_db_datetime(dt_value)
            if parsed:
                return parsed.strftime("%Y-%m-%d %H:%M:%S")
            return dt_value

        return now_tehran_str()