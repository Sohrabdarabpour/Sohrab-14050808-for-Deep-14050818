import os
from datetime import timedelta

# بارگذاری متغیرهای محیطی از فایل .env
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:  # pragma: no cover
    pass


def _env_bool(name, default=False):
    """خواندن متغیر محیطی بولی (1/true/yes/on)."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_iso_days(name, default):
    """روزهای تعطیل هفتگی به شکل ISO (دوشنبه=۱ … یکشنبه=۷)."""
    raw = os.environ.get(name, "")
    if not raw.strip():
        return default
    days = set()
    for part in raw.split(","):
        try:
            value = int(part.strip())
        except (TypeError, ValueError):
            continue
        if 1 <= value <= 7:
            days.add(value)
    return tuple(sorted(days)) if days else default


#: مقدار پیش‌فرض SECRET_KEY — فقط برای توسعه است
DEV_SECRET_KEY = "sspe-rev1-secret-key"


class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SECRET_KEY = os.environ.get("SECRET_KEY") or DEV_SECRET_KEY
    DATABASE_PATH = os.environ.get("SSPE_DATABASE_PATH") or os.path.join(
        BASE_DIR, "instance", "database.db"
    )
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

    # ★★★ حذف محدودیت Flask — ما خودمان استریمی بررسی می‌کنیم
    MAX_CONTENT_LENGTH = None

    # ★★★ جدید — تنظیمات آپلود پکیج سند
    DOCUMENT_UPLOAD_ROOT = os.path.join(BASE_DIR, "instance", "uploads")
    MAX_UPLOAD_SIZE_BYTES = None  # None = بدون محدودیت
    ALLOWED_UPLOAD_EXTENSIONS = {
        # اسناد اداری
        "pdf", "doc", "docx", "docm", "xls", "xlsx", "xlsm",
        "ppt", "pptx", "pptm", "txt", "csv", "rtf", "odt", "ods",
        # تصاویر
        "jpg", "jpeg", "jfif", "png", "gif", "bmp", "webp", "svg",
        "heic", "heif", "tiff", "tif",
        # ویدیو و صدا
        "mp4", "mov", "avi", "mkv", "webm", "mpg", "mpeg",
        "mp3", "wav", "ogg", "m4a", "aac",
        # آرشیو
        "zip", "rar", "7z", "tar", "gz",
        # CAD
        "dwg", "dxf", "step", "stp", "iges", "igs", "rvt", "ifc",
        # مدیریت پروژه
        "mpp", "vsd", "vsdx",
        # ایمیل
        "msg", "eml",
        # اسکن
        "djvu",
    }
    PREVIEWABLE_EXTENSIONS = {
        "pdf", "txt", "csv", "json", "xml",
        "jpg", "jpeg", "jfif", "png", "gif", "bmp", "webp", "svg",
        "tiff", "tif",
        "mp4", "webm", "mov", "m4a",
        "mp3", "wav", "ogg",
    }

    DATE_FORMAT = "%Y/%m/%d"

    # ============================================================
    # ★ امنیت نشست
    # ============================================================
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

    # ============================================================
    # ★ DEBUG
    # ============================================================
    DEBUG = _env_bool("FLASK_DEBUG", False)

    # ============================================================
    # ★ تقویم کاری و مهلت پاسخ
    # ============================================================
    WEEKEND_DAYS = _env_iso_days("SSPE_WEEKEND_DAYS", (4, 5))
    DEFAULT_SLA_DAYS = _env_int("SSPE_DEFAULT_SLA_DAYS", 7)

    # ============================================================
    # ★ CSRF
    # ============================================================
    WTF_CSRF_TIME_LIMIT = None
    WTF_CSRF_HEADERS = ["X-CSRFToken", "X-CSRF-Token"]

    @classmethod
    def is_default_secret(cls):
        return cls.SECRET_KEY == DEV_SECRET_KEY

    DATE_FIELDS = [
        "date_letter",
        "date_received",
        "date_referral",
        "deadline",
        "request_complete_docs",
        "complete_docs_by_contractor",
        "response_announce_date",
        "final_send_date",
    ]

    EXCEL_COLUMN_MAPPING = {
        # شناسه‌ها
        "شناسه سند": "id",
        "شناسه": "id",
        "ID": "id",
        "id": "id",
        "شناسه پیمانکار": "contractor_id",
        "شناسه پیمانکار ": "contractor_id",
        "شناسه پروژه": "project_id",
        "شناسه پروژه ": "project_id",

        # اطلاعات اصلی سند
        "کد DFC": "code_dfc",
        "تاریخ نامه": "date_letter",
        "تاریخ نامه پیمانکار": "date_letter",
        "شماره اتوماسیون": "automation_number",
        "شماره نامه اتوماسیون": "automation_number",
        "شماره نامه پیمانکار": "contractor_letter_number",
        "موضوع": "subject",
        "موضوع نامه": "subject",
        "شماره قرارداد": "contract_number",
        "شماره قرارداد ریالی": "contract_number",
        "نام پروژه": "project_name",
        "پیمانکار": "contractor",
        "ناحیه": "area",
        "ناحیه / منطقه": "area",
        "تاریخ دریافت": "date_received",
        "تاریخ ارجاع": "date_referral",
        "نام کارشناس": "expert_name",
        "نام کارشناس ": "expert_name",
        "شناسه کاربر": "user_id",
        "شناسه کارشناس": "user_id",
        "واحد": "unit",
        "گروه مدرک": "document_group",
        "گروه سند": "document_group",
        "زیرگروه": "sub_group",
        "زیر گروه": "sub_group",
        "زیر گروه ": "sub_group",
        "مهلت پاسخ": "deadline",
        "موعد تحویل": "deadline",
        "درخواست تکمیل مدارک": "request_complete_docs",
        "تاریخ درخواست تکمیل مدارک": "request_complete_docs",
        "تاریخ  درخواست تکمیل مدارک(کارشناس)": "request_complete_docs",
        "تکمیل مدارک توسط پیمانکار": "complete_docs_by_contractor",
        "تاریخ تکمیل مدارک": "complete_docs_by_contractor",
        "تاریخ تکمیل مدارک توسط پیمانکار": "complete_docs_by_contractor",
        "وضعیت پاسخ مدرک": "doc_response_status",
        "تاریخ اعلام پاسخ": "response_announce_date",
        "تاریخ ارسال نهایی": "final_send_date",
        "تاریخ ارسال نهایی ": "final_send_date",
        "تاریخ ارسال": "final_send_date",
        "شماره نامه نهایی": "final_letter_number",
        "شماره نامه نهایی ": "final_letter_number",
        "تاخیر نهایی": "final_delay",
        "تاخیر نهایی ": "final_delay",
        "همکار": "colleague",
        "همکار ": "colleague",
        "طرف مسئول": "Responsible_Party",
        "مسئول رسیدگی": "Responsible_Party",
        "مسئول رسیدگی ": "Responsible_Party",

        # شناسه‌های ارجاعی
        "شناسه وضعیت": "status_id",
        "شناسه ناحیه": "area_id",
        "شناسه دپارتمان": "department_id",
        "شناسه گروه": "group_id",
        "شناسه گروه سند": "group_id",
        "شناسه زیرگروه": "subgroup_id",
        "شناسه زیرگروه سند": "subgroup_id",

        # انگلیسی
        "Responsible_Party": "Responsible_Party",
        "responsible_party": "Responsible_Party",
        "Responsible party": "Responsible_Party",
    }