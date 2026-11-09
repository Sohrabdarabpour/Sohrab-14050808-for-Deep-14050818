"""
سرویس Import/Export اکسل پروژه‌ها
"""
import os
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from database.init_db import (
    get_all_projects,
    get_project,
    get_project_by_code,
    create_project,
    update_project,
    get_all_contractors,
    get_all_contract_types,
    get_all_areas,
)


# ================================================================
# ★ ستون‌های اکسل
# ================================================================
EXCEL_COLUMNS = [
    # ============ شناسه ============
    ("id",                          "شناسه (ID)",              10),

    # ============ اطلاعات اصلی ============
    ("name",                        "نام پروژه",               30),
    ("code",                        "کد پروژه",                15),
    ("project_number",              "شماره پروژه",             15),
    ("description",                 "توضیحات",                 30),

    # ============ ارتباطات ============
    ("contractor_name",             "پیمانکار",                25),
    ("contract_type_title",         "نوع قرارداد",             20),
    ("area_title",                  "ناحیه",                   15),

    # ============ قرارداد ریالی ============
    ("contract_number",             "شماره قرارداد ریالی",     20),
    ("contract_amount",             "مبلغ ریالی",              20),

    # ============ قرارداد ارزی ============
    ("contract_number_foreign",     "شماره قرارداد ارزی",      20),
    ("contract_amount_foreign",     "مبلغ ارزی",               18),
    ("currency",                    "واحد پول",                10),

    # ============ تاریخ‌های قرارداد ============
    ("contract_start_date",         "شروع قرارداد",            15),
    ("contract_end_date",           "پایان قرارداد",           15),

    # ============ زمان‌بندی ============
    ("start_date",                  "شروع پروژه",              15),
    ("planned_end_date",            "پایان برنامه‌ای",          15),
    ("actual_end_date",             "پایان واقعی",             15),
    ("duration_days",               "مدت (روز)",               12),

    # ============ وضعیت ============
    ("status",                      "وضعیت",                   15),
    ("priority",                    "اولویت",                  12),

    # ============ پیشرفت‌ها ============
    ("progress_percent",            "پیشرفت کلی (٪)",          15),
    ("physical_progress",           "پیشرفت فیزیکی (٪)",       15),
    ("time_progress",               "پیشرفت برنامه‌ای (٪)",     15),
    ("financial_progress_rial",     "پیشرفت مالی ریالی (٪)",   18),
    ("financial_progress_foreign",  "پیشرفت مالی ارزی (٪)",    18),

    # ============ مالی ============
    ("budget",                      "بودجه (ریال)",            20),

    # ============ مکان ============
    ("province",                    "استان",                   15),
    ("city",                        "شهر",                     15),
    ("location",                    "موقعیت / آدرس",           25),

    # ============ متادیتا ============
    ("is_active",                   "وضعیت فعال",              12),
    ("notes",                       "یادداشت",                 30),
]

FIELD_NAMES = [col[0] for col in EXCEL_COLUMNS]
HEADER_NAMES = [col[1] for col in EXCEL_COLUMNS]
COLUMN_WIDTHS = [col[2] for col in EXCEL_COLUMNS]


# ================================================================
# مقادیر ثابت
# ================================================================
STATUS_LABELS = {
    "active":    "فعال",
    "completed": "تکمیل شده",
    "paused":    "متوقف شده",
    "cancelled": "لغو شده",
    "pending":   "در انتظار شروع",
}

STATUS_LABELS_REVERSE = {v: k for k, v in STATUS_LABELS.items()}
STATUS_LABELS_REVERSE.update({
    "فعال":       "active",
    "تکمیل":      "completed",
    "تکمیل شده":  "completed",
    "متوقف":      "paused",
    "متوقف شده":  "paused",
    "لغو":        "cancelled",
    "لغو شده":    "cancelled",
    "در انتظار":  "pending",
    "در انتظار شروع": "pending",
})

PRIORITY_LABELS = {
    "low":      "کم",
    "medium":   "متوسط",
    "high":     "بالا",
    "critical": "بحرانی",
}

PRIORITY_LABELS_REVERSE = {v: k for k, v in PRIORITY_LABELS.items()}
PRIORITY_LABELS_REVERSE.update({
    "کم":     "low",
    "متوسط":  "medium",
    "بالا":   "high",
    "بحرانی": "critical",
})


# ================================================================
# ★ Export به اکسل
# ================================================================
def export_projects_to_excel(
    output_path=None,
    only_active=False,
    contractor_id=None,
    contract_type_id=None,
    area_id=None,
    status=None,
):
    """
    خروجی اکسل از پروژه‌ها

    Args:
        output_path (str): مسیر ذخیره فایل
        فقط فیلترهای دلخواه

    Returns:
        str: مسیر فایل ذخیره‌شده
    """
    if output_path is None:
        base_dir = os.path.join(
            "static", "uploads", "projects"
        )
        os.makedirs(base_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(
            base_dir, f"projects_export_{timestamp}.xlsx"
        )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "پروژه‌ها"
    ws.sheet_view.rightToLeft = True

    # ---- استایل هدر ----
    header_font = Font(
        name="Vazirmatn", size=11, bold=True, color="FFFFFF"
    )
    header_fill = PatternFill(
        start_color="1B698B", end_color="167A5C", fill_type="solid"
    )
    header_align = Alignment(
        horizontal="center", vertical="center", wrap_text=True
    )
    thin = Side(border_style="thin", color="D0D7DE")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # ---- نوشتن هدر ----
    for col_idx, header in enumerate(HEADER_NAMES, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = border

    # ---- عرض ستون‌ها ----
    for col_idx, width in enumerate(COLUMN_WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width
    ws.row_dimensions[1].height = 32

    # ---- داده‌ها ----
    from database.init_db import get_all_projects
    projects = get_all_projects(
        only_active=only_active,
        contractor_id=contractor_id,
        contract_type_id=contract_type_id,
        area_id=area_id,
        status=status,
    )

    data_font = Font(name="Vazirmatn", size=10)
    data_align = Alignment(
        horizontal="center", vertical="center", wrap_text=False
    )

    for row_idx, project in enumerate(projects, start=2):
        for col_idx, field in enumerate(FIELD_NAMES, start=1):
            value = project.get(field, "")

            # ---- تبدیل‌های خاص ----
            if value is None:
                value = ""

            if field == "status":
                value = STATUS_LABELS.get(value, value)
            elif field == "priority":
                value = PRIORITY_LABELS.get(value, value)
            elif field == "is_active":
                value = "فعال" if value else "غیرفعال"

            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.font = data_font
            cell.alignment = data_align
            cell.border = border

    wb.save(output_path)
    return output_path


# ================================================================
# ★ Import از اکسل
# ================================================================
def import_projects_from_excel(file_path, update_existing=False):
    """
    Import پروژه‌ها از فایل اکسل

    Args:
        file_path (str): مسیر فایل
        update_existing (bool): به‌روزرسانی رکوردهای موجود

    Returns:
        dict: نتیجه Import
    """
    result = {
        "success": False,
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
    }

    if not os.path.exists(file_path):
        result["errors"].append("فایل اکسل یافت نشد")
        return result

    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
    except Exception as e:
        result["errors"].append(f"خطا در باز کردن فایل: {e}")
        return result

    ws = wb.active

    # ---- خواندن هدر ----
    header_row = [cell.value for cell in ws[1]]
    header_map = {}
    for idx, header in enumerate(header_row):
        if header is None:
            continue
        header = str(header).strip()
        if header in HEADER_NAMES:
            field = FIELD_NAMES[HEADER_NAMES.index(header)]
            header_map[field] = idx

    # ---- چک ستون اجباری ----
    if "name" not in header_map:
        result["errors"].append("ستون «نام پروژه» در فایل یافت نشد")
        return result

    # ---- Preload for FK mapping ----
    contractors = {c["name"]: c["id"] for c in get_all_contractors()}
    contract_types = {t["title"]: t["id"] for t in get_all_contract_types()}
    areas = {a["title"]: a["id"] for a in get_all_areas()}

    # ---- پردازش ردیف‌ها ----
    for row_idx, row in enumerate(
        ws.iter_rows(min_row=2, values_only=True), start=2
    ):
        if not row or all(cell is None for cell in row):
            continue

        data = {}
        for field, col_idx in header_map.items():
            if col_idx < len(row):
                data[field] = row[col_idx]

        # ---- اعتبارسنجی نام ----
        name = data.get("name")
        if isinstance(name, str):
            name = name.strip()
        if not name:
            result["skipped"] += 1
            continue

        # ---- نگاشت FK ----
        contractor_name = data.get("contractor_name")
        if contractor_name:
            contractor_name = str(contractor_name).strip()
            data["contractor_id"] = contractors.get(contractor_name)
        data.pop("contractor_name", None)

        ct_title = data.get("contract_type_title")
        if ct_title:
            ct_title = str(ct_title).strip()
            data["contract_type_id"] = contract_types.get(ct_title)
        data.pop("contract_type_title", None)

        area_title = data.get("area_title")
        if area_title:
            area_title = str(area_title).strip()
            data["area_id"] = areas.get(area_title)
        data.pop("area_title", None)

        # ---- تبدیل status ----
        status_val = data.get("status")
        if status_val:
            status_val = str(status_val).strip()
            data["status"] = STATUS_LABELS_REVERSE.get(
                status_val, "active"
            )

        # ---- تبدیل priority ----
        priority_val = data.get("priority")
        if priority_val:
            priority_val = str(priority_val).strip()
            data["priority"] = PRIORITY_LABELS_REVERSE.get(
                priority_val, "medium"
            )

        # ---- تبدیل is_active ----
        is_active_val = data.get("is_active")
        if isinstance(is_active_val, str):
            is_active = 1 if is_active_val.strip() in (
                "فعال", "1", "true", "True", "yes"
            ) else 0
        elif is_active_val in (0, 1, True, False):
            is_active = int(is_active_val)
        else:
            is_active = 1
        data["is_active"] = is_active

        # ---- ★ حذف id (auto-increment) ----
        data.pop("id", None)

        # ---- تمیزکاری ----
        clean_data = {}
        for field, value in data.items():
            if isinstance(value, str):
                value = value.strip()
                clean_data[field] = value if value else None
            else:
                clean_data[field] = value
        clean_data["name"] = name

        # ---- currency پیش‌فرض ----
        if not clean_data.get("currency"):
            clean_data["currency"] = "USD"

        # ---- چک تکراری ----
        code = clean_data.get("code")
        existing = None
        if code:
            existing = get_project_by_code(code)

        if existing:
            if update_existing:
                ok = update_project(existing["id"], **clean_data)
                if ok:
                    result["updated"] += 1
                else:
                    result["errors"].append(
                        f"ردیف {row_idx}: خطا در به‌روزرسانی"
                    )
            else:
                result["skipped"] += 1
            continue

        # ---- ایجاد جدید ----
        new_id = create_project(**clean_data)
        if new_id:
            result["inserted"] += 1
        else:
            result["errors"].append(
                f"ردیف {row_idx}: خطا در ایجاد پروژه «{name}»"
            )

    result["success"] = True
    return result


# ================================================================
# ★ فایل قالب (Template)
# ================================================================
def generate_import_template(output_path=None):
    """
    ساخت فایل اکسل نمونه برای Import

    Returns:
        str: مسیر فایل ذخیره‌شده
    """
    if output_path is None:
        base_dir = os.path.join(
            "static", "uploads", "projects"
        )
        os.makedirs(base_dir, exist_ok=True)
        output_path = os.path.join(
            base_dir, "projects_template.xlsx"
        )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "قالب پروژه‌ها"
    ws.sheet_view.rightToLeft = True

    header_font = Font(
        name="Vazirmatn", size=11, bold=True, color="FFFFFF"
    )
    header_fill = PatternFill(
        start_color="1B698B", end_color="167A5C", fill_type="solid"
    )
    header_align = Alignment(
        horizontal="center", vertical="center", wrap_text=True
    )

    for col_idx, header in enumerate(HEADER_NAMES, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align

    for col_idx, width in enumerate(COLUMN_WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width
    ws.row_dimensions[1].height = 32

    # ---- نمونه (با id خالی در ابتدا) ----
    sample = [
        "",                      # ★ id (خالی — خودکار ساخته می‌شه)
        "پروژه سد کرخه",        # name
        "PRJ-001",               # code
        "1403/125",              # project_number
        "پروژه نمونه",           # description
        "شرکت عمرانی پارس",      # contractor_name
        "EPC (طراحی + تأمین + اجرا)",  # contract_type_title
        "",                      # area_title
        "1403/125",              # contract_number
        50000000000,             # contract_amount
        "F-2024/001",            # contract_number_foreign
        1000000,                 # contract_amount_foreign
        "USD",                   # currency
        "1403/01/01",            # contract_start_date
        "1405/01/01",            # contract_end_date
        "1403/01/15",            # start_date
        "1405/01/15",            # planned_end_date
        "",                      # actual_end_date
        730,                     # duration_days
        "فعال",                  # status
        "بالا",                  # priority
        25,                      # progress_percent
        20,                      # physical_progress
        30,                      # time_progress
        15,                      # financial_progress_rial
        10,                      # financial_progress_foreign
        60000000000,             # budget
        "خوزستان",               # province
        "اندیمشک",               # city
        "سد کرخه",               # location
        "فعال",                  # is_active
        "توضیحات نمونه",         # notes
    ]

    for col_idx, value in enumerate(sample, start=1):
        ws.cell(row=2, column=col_idx, value=value)

    wb.save(output_path)
    return output_path


# ================================================================
# ★ دیتای نمونه (اختیاری)
# ================================================================
def create_sample_projects():
    """ایجاد چند پروژه نمونه برای تست"""
    projects = [
        {
            "name": "پروژه سد کرخه",
            "code": "PRJ-001",
            "project_number": "1403/125",
            "contract_number": "1403/125",
            "contract_amount": 50000000000,
            "status": "active",
            "priority": "high",
            "progress_percent": 25,
            "physical_progress": 20,
            "time_progress": 30,
            "financial_progress_rial": 15,
            "is_active": 1,
        },
        {
            "name": "پروژه جاده قم-تهران",
            "code": "PRJ-002",
            "contract_number": "1403/201",
            "contract_amount": 80000000000,
            "status": "active",
            "priority": "critical",
            "progress_percent": 45,
            "physical_progress": 50,
            "time_progress": 40,
            "financial_progress_rial": 35,
            "is_active": 1,
        },
    ]

    inserted = 0
    for p in projects:
        if p.get("code"):
            existing = get_project_by_code(p["code"])
            if existing:
                continue
        new_id = create_project(**p)
        if new_id:
            inserted += 1

    if inserted:
        print(f"✅ {inserted} پروژه نمونه ایجاد شد")