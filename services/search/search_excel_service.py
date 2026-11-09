"""ساخت فایل اکسل از نتایج جستجو.

این سرویس بین صفحه‌ی جستجو (`/search/api/export`) و دستیار هوشمند
(`/assistant/export/search`) مشترک است تا دو پیاده‌سازی از هم جدا نشوند.
"""

import io
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

DEFAULT_SHEET_TITLE = "نتایج جستجو"

HEADERS = [
    "کد DFC",
    "موضوع",
    "وضعیت",
    "پیمانکار",
    "پروژه",
    "تاریخ نامه",
    "شماره اتوماسیون",
    "شماره نامه پیمانکار",
    "شماره قرارداد",
    "دپارتمان",
    "ناحیه",
    "گروه مدرک",
    "زیرگروه",
    "مهلت پاسخ",
    "وضعیت پاسخ",
    "تاریخ دریافت",
    "تاریخ ارسال نهایی",
]

# (کلید در رکورد، کلید جایگزین)
FIELD_MAP = [
    ("code_dfc", None),
    ("subject", None),
    ("status_title", None),
    ("contractor_name", "contractor"),
    ("project_title", "project_name"),
    ("date_letter_jalali", "date_letter"),
    ("automation_number", None),
    ("contractor_letter_number", None),
    ("contract_number", None),
    ("department_title", None),
    ("area_title", None),
    ("group_title", None),
    ("subgroup_title", None),
    ("deadline_jalali", "deadline"),
    ("doc_response_status", None),
    ("date_received_jalali", "date_received"),
    ("final_send_date_jalali", "final_send_date"),
]


def _cell_value(record, key, fallback):
    value = record.get(key)
    if not value and fallback:
        value = record.get(fallback)
    return value or ""


def build_workbook(records, sheet_title=DEFAULT_SHEET_TITLE, extra_columns=None):
    """ساخت Workbook از رکوردهای جستجو.

    Args:
        records: لیست دیکشنری رکوردهای search_documents
        sheet_title: نام شیت
        extra_columns: لیست اختیاری (عنوان، تابع استخراج) برای ستون‌های اضافی
    """
    headers = list(HEADERS)
    if extra_columns:
        headers.extend(title for title, _getter in extra_columns)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_title
    sheet.sheet_view.rightToLeft = True
    sheet.append(headers)

    header_font = Font(bold=True, color="FFFFFF", size=11, name="Tahoma")
    header_fill = PatternFill("solid", fgColor="1B698B")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for cell in sheet[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align

    sheet.row_dimensions[1].height = 28

    body_font = Font(size=10, name="Tahoma")
    body_align = Alignment(horizontal="right", vertical="center", wrap_text=False)

    for record in records:
        row = [_cell_value(record, key, fallback) for key, fallback in FIELD_MAP]
        if extra_columns:
            row.extend(getter(record) for _title, getter in extra_columns)
        sheet.append(row)

    for row in sheet.iter_rows(min_row=2, max_row=sheet.max_row):
        for cell in row:
            cell.font = body_font
            cell.alignment = body_align

    for index, column_cells in enumerate(sheet.columns, start=1):
        longest = 10
        for cell in column_cells:
            if cell.value:
                longest = max(longest, len(str(cell.value)))
        sheet.column_dimensions[get_column_letter(index)].width = min(longest + 4, 45)

    return workbook


def build_search_excel(records, sheet_title=DEFAULT_SHEET_TITLE):
    """برگرداندن فایل اکسل به‌صورت جریان بایت (برای send_file)."""
    workbook = build_workbook(records, sheet_title=sheet_title)
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


def build_filename(prefix="search_results"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.xlsx"


__all__ = [
    "HEADERS",
    "build_workbook",
    "build_search_excel",
    "build_filename",
]
