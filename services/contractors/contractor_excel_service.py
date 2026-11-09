"""
سرویس Import/Export اکسل پیمانکاران
"""
import os
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from database.init_db import (
    get_all_contractors,
    get_contractor_by_code,
    create_contractor,
    update_contractor,
)


# ================================================================
# ★ ستون‌های اکسل (id به عنوان اولین ستون)
# ================================================================
EXCEL_COLUMNS = [
    ("id",                    "شناسه پیمانکار",     10),
    ("name",                  "نام پیمانکار",        30),
    ("code",                  "کد پیمانکار",         15),
    ("national_id",           "کد ملی / شناسه ملی",  20),
    ("economic_code",         "کد اقتصادی",          15),
    ("registration_number",   "شماره ثبت",           15),
    ("manager_name",          "نام مدیرعامل",        20),
    ("phone",                 "تلفن",                15),
    ("mobile",                "موبایل",              15),
    ("email",                 "ایمیل",               25),
    ("province",              "استان",               15),
    ("city",                  "شهر",                 15),
    ("postal_code",           "کد پستی",             15),
    ("address",               "آدرس",                40),
    ("grade",                 "رتبه / گرید",         15),
    ("is_active",             "وضعیت (1=فعال)",      15),
    ("description",           "توضیحات",             30),
]

FIELD_NAMES = [col[0] for col in EXCEL_COLUMNS]
HEADER_NAMES = [col[1] for col in EXCEL_COLUMNS]
COLUMN_WIDTHS = [col[2] for col in EXCEL_COLUMNS]


# ================================================================
# ★ Export به اکسل
# ================================================================
def export_contractors_to_excel(output_path=None):
    """خروجی اکسل از همه پیمانکاران"""
    if output_path is None:
        base_dir = os.path.join(
            "static", "uploads", "contractors"
        )
        os.makedirs(base_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(
            base_dir, f"contractors_export_{timestamp}.xlsx"
        )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "پیمانکاران"
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
    thin = Side(border_style="thin", color="D0D7DE")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col_idx, header in enumerate(HEADER_NAMES, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = border

    for col_idx, width in enumerate(COLUMN_WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width
    ws.row_dimensions[1].height = 32

    contractors = get_all_contractors(only_active=False)
    data_font = Font(name="Vazirmatn", size=10)
    data_align = Alignment(
        horizontal="center", vertical="center", wrap_text=False
    )

    for row_idx, contractor in enumerate(contractors, start=2):
        for col_idx, field in enumerate(FIELD_NAMES, start=1):
            value = contractor.get(field, "")
            if value is None:
                value = ""
            if field == "is_active":
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
def import_contractors_from_excel(file_path, update_existing=False):
    """Import پیمانکاران از فایل اکسل"""
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

    if "name" not in header_map:
        result["errors"].append(
            "ستون «نام پیمانکار» در فایل یافت نشد"
        )
        return result

    # ---- پردازش ردیف‌ها ----
    for row_idx, row in enumerate(
        ws.iter_rows(min_row=2, values_only=True), start=2
    ):
        if not row or all(cell is None for cell in row):
            continue

        data = {}
        for field, col_idx in header_map.items():
            if col_idx < len(row):
                value = row[col_idx]
                data[field] = value

        name = (data.get("name") or "").strip() \
            if isinstance(data.get("name"), str) \
            else data.get("name")

        if not name:
            result["skipped"] += 1
            continue

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

        # ---- تمیزکاری داده‌ها ----
        clean_data = {}
        for field, value in data.items():
            if isinstance(value, str):
                value = value.strip()
                clean_data[field] = value if value else None
            else:
                clean_data[field] = value
        clean_data["name"] = name

        # ---- حذف id از داده‌ها (auto-increment است) ----
        clean_data.pop("id", None)

        # ---- چک تکراری ----
        code = clean_data.get("code")
        existing = None
        if code:
            existing = get_contractor_by_code(code)

        if existing:
            if update_existing:
                ok = update_contractor(existing["id"], **clean_data)
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
        new_id = create_contractor(**clean_data)
        if new_id:
            result["inserted"] += 1
        else:
            result["errors"].append(
                f"ردیف {row_idx}: خطا در ایجاد پیمانکار «{name}»"
            )

    result["success"] = True
    return result


# ================================================================
# ★ فایل نمونه (Template)
# ================================================================
def generate_import_template(output_path=None):
    """ساخت فایل اکسل نمونه برای import"""
    if output_path is None:
        base_dir = os.path.join(
            "static", "uploads", "contractors"
        )
        os.makedirs(base_dir, exist_ok=True)
        output_path = os.path.join(
            base_dir, "contractors_template.xlsx"
        )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "قالب پیمانکاران"
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

    # ---- نمونه (id به عنوان اولین ستون) ----
    sample = [
        "",                        # id (خالی - auto increment)
        "شرکت عمرانی پارس",        # name
        "CON-001",                 # code
        "1234567890",              # national_id
        "411234567890",            # economic_code
        "12345",                   # registration_number
        "علی رضایی",               # manager_name
        "02188776655",             # phone
        "09121234567",             # mobile
        "info@pars.com",           # email
        "تهران",                   # province
        "تهران",                   # city
        "1234567890",              # postal_code
        "تهران، خیابان آزادی، پلاک ۱۰",  # address
        "1",                       # grade
        "1",                       # is_active
        "شرکت نمونه",              # description
    ]
    for col_idx, value in enumerate(sample, start=1):
        ws.cell(row=2, column=col_idx, value=value)

    wb.save(output_path)
    return output_path