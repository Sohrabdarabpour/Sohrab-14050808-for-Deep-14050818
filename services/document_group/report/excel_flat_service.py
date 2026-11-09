import io
import pandas as pd
from datetime import datetime
from itertools import product

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from database.connection import get_connection


class DocumentSubgroupExcelFlatService:
    """
    ★ نسخه Flat: به ازای هر ترکیب (گروه × دپارتمان) یک ردیف جدا
    
    مثال:
        زیرگروه «استخدام» با:
        - گروه‌ها: منابع انسانی (HR), روش اجرایی (PR)
        - دپارتمان‌ها: دفتر فنی (TECH), کنترل کیفی (QC)
        
        نتیجه: 4 ردیف (2 گروه × 2 دپارتمان)
    """

    # ============================================================
    # ★ ستون‌های خروجی
    # ============================================================
    EXPORT_COLUMNS = [
        # اطلاعات زیرگروه
        ("subgroup_id", "شناسه زیرگروه"),
        ("subgroup_title", "عنوان زیرگروه"),
        ("subgroup_code", "کد زیرگروه"),
        ("days_review", "بازه بررسی (روز)"),
        ("subgroup_sort_order", "ترتیب زیرگروه"),
        ("is_active_label", "وضعیت"),
        ("subgroup_created_at", "تاریخ ایجاد زیرگروه"),
        # اطلاعات گروه
        ("group_id", "شناسه گروه"),
        ("group_title", "عنوان گروه"),
        ("group_code", "کد گروه"),
        ("group_sort_order", "ترتیب گروه"),
        # اطلاعات دپارتمان
        ("department_id", "شناسه دپارتمان"),
        ("department_title", "عنوان دپارتمان"),
        ("department_code", "کد دپارتمان"),
        ("department_sort_order", "ترتیب دپارتمان"),
        # آمار
        ("documents_count", "تعداد اسناد"),
    ]

    # ============================================================
    # ★ عرض ستون‌ها
    # ============================================================
    EXPORT_WIDTHS = {
        1: 12,   # subgroup_id
        2: 30,   # subgroup_title
        3: 12,   # subgroup_code
        4: 14,   # days_review
        5: 12,   # subgroup_sort_order
        6: 10,   # is_active_label
        7: 20,   # subgroup_created_at
        8: 12,   # group_id
        9: 28,   # group_title
        10: 12,  # group_code
        11: 12,  # group_sort_order
        12: 14,  # department_id
        13: 28,  # department_title
        14: 14,  # department_code
        15: 15,  # department_sort_order
        16: 12,  # documents_count
    }

    # ============================================================
    # ★ ستون‌های گروه‌بندی شده (برای رنگ‌آمیزی سرستون‌ها)
    # ============================================================
    COLUMN_GROUPS = {
        "subgroup": {
            "title": "اطلاعات زیرگروه",
            "color": "167A5C",   # سبز
            "columns": [
                "subgroup_id", "subgroup_title", "subgroup_code",
                "days_review", "subgroup_sort_order",
                "is_active_label", "subgroup_created_at",
            ],
        },
        "group": {
            "title": "گروه مرتبط",
            "color": "1B698B",   # آبی
            "columns": [
                "group_id", "group_title", "group_code",
                "group_sort_order",
            ],
        },
        "department": {
            "title": "دپارتمان متولی",
            "color": "805AD5",   # بنفش
            "columns": [
                "department_id", "department_title",
                "department_code", "department_sort_order",
            ],
        },
        "stats": {
            "title": "آمار",
            "color": "D69E2E",   # طلایی
            "columns": ["documents_count"],
        },
    }

    # ============================================================
    # ★ دریافت داده‌های Flat
    # ============================================================
    @staticmethod
    def get_flat_data(group_id=None, department_id=None):
        """
        دریافت داده‌های زیرگروه‌ها به صورت Flat
        (هر ترکیب گروه × دپارتمان = یک ردیف)
        """
        connection = get_connection()
        try:
            # ==================================================
            # 1) زیرگروه‌های اصلی
            # ==================================================
            query = """
                SELECT
                    sg.id             AS subgroup_id,
                    sg.title          AS subgroup_title,
                    sg.code           AS subgroup_code,
                    sg.color          AS subgroup_color,
                    sg.days_review    AS days_review,
                    sg.description    AS subgroup_description,
                    sg.sort_order     AS subgroup_sort_order,
                    sg.is_active      AS is_active,
                    sg.created_at     AS subgroup_created_at,
                    (
                        SELECT COUNT(*)
                        FROM documents d
                        WHERE d.subgroup_id = sg.id
                    ) AS documents_count
                FROM document_subgroups sg
                WHERE 1=1
            """
            params = []

            if group_id:
                query += """
                    AND sg.id IN (
                        SELECT subgroup_id FROM group_subgroups
                        WHERE group_id = ?
                    )
                """
                params.append(group_id)

            if department_id:
                query += """
                    AND sg.id IN (
                        SELECT subgroup_id FROM subgroup_departments
                        WHERE department_id = ?
                    )
                """
                params.append(department_id)

            query += " ORDER BY sg.sort_order ASC, sg.id ASC"

            rows = connection.execute(query, params).fetchall()
            subgroups = [dict(r) for r in rows]

            # ==================================================
            # 2) برای هر زیرگروه → گروه‌ها و دپارتمان‌ها
            # ==================================================
            result = []

            for sg in subgroups:
                # ★ گروه‌های مرتبط
                groups = connection.execute("""
                    SELECT
                        g.id         AS group_id,
                        g.title      AS group_title,
                        g.code       AS group_code,
                        g.sort_order AS group_sort_order
                    FROM document_groups g
                    INNER JOIN group_subgroups gs
                        ON gs.group_id = g.id
                    WHERE gs.subgroup_id = ?
                    ORDER BY gs.sort_order ASC, g.title ASC
                """, (sg["subgroup_id"],)).fetchall()
                groups = [dict(g) for g in groups]

                # ★ دپارتمان‌های متولی
                departments = connection.execute("""
                    SELECT
                        d.id         AS department_id,
                        d.title      AS department_title,
                        d.code       AS department_code,
                        d.sort_order AS department_sort_order
                    FROM departments d
                    INNER JOIN subgroup_departments sd
                        ON sd.department_id = d.id
                    WHERE sd.subgroup_id = ?
                    ORDER BY d.title ASC
                """, (sg["subgroup_id"],)).fetchall()
                departments = [dict(d) for d in departments]

                # ★ اگه هیچ گروه و دپارتمانی نبود → یه ردیف خالی
                if not groups and not departments:
                    result.append(
                        DocumentSubgroupExcelFlatService._build_row(
                            sg, None, None
                        )
                    )
                    continue

                # ★ اگه فقط گروه بود
                if groups and not departments:
                    for g in groups:
                        result.append(
                            DocumentSubgroupExcelFlatService._build_row(
                                sg, g, None
                            )
                        )
                    continue

                # ★ اگه فقط دپارتمان بود
                if departments and not groups:
                    for d in departments:
                        result.append(
                            DocumentSubgroupExcelFlatService._build_row(
                                sg, None, d
                            )
                        )
                    continue

                # ★ ترکیب کارتزین (گروه × دپارتمان)
                for g, d in product(groups, departments):
                    result.append(
                        DocumentSubgroupExcelFlatService._build_row(
                            sg, g, d
                        )
                    )

            return result

        finally:
            connection.close()

    # ============================================================
    # ★ ساخت یک ردیف (Helper)
    # ============================================================
    @staticmethod
    def _build_row(sg, group, department):
        """ساخت یه ردیف از زیرگروه، گروه و دپارتمان"""
        return {
            # اطلاعات زیرگروه
            "subgroup_id":           sg["subgroup_id"],
            "subgroup_title":        sg["subgroup_title"],
            "subgroup_code":         sg["subgroup_code"],
            "days_review":           sg["days_review"],
            "subgroup_sort_order":   sg["subgroup_sort_order"],
            "is_active_label":       "فعال" if sg["is_active"] else "غیرفعال",
            "subgroup_created_at":   sg["subgroup_created_at"],
            # اطلاعات گروه (ممکنه None باشه)
            "group_id":              group["group_id"] if group else None,
            "group_title":           group["group_title"] if group else "—",
            "group_code":            group["group_code"] if group else "—",
            "group_sort_order":      group["group_sort_order"] if group else None,
            # اطلاعات دپارتمان (ممکنه None باشه)
            "department_id":         department["department_id"] if department else None,
            "department_title":      department["department_title"] if department else "—",
            "department_code":       department["department_code"] if department else "—",
            "department_sort_order": department["department_sort_order"] if department else None,
            # آمار
            "documents_count":       sg["documents_count"],
        }

    # ============================================================
    # ★ ساخت فایل اکسل
    # ============================================================
    @staticmethod
    def _create_workbook(data):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "زیرگروه‌ها (Flat)"

        # ------------------------------------------------
        # استایل‌ها
        # ------------------------------------------------
        body_font = Font(name="Segoe UI", size=9, bold=False, color="000000")
        body_font_bold = Font(name="Segoe UI", size=9, bold=True, color="000000")
        group_header_font = Font(
            name="Segoe UI", size=11, bold=True, color="FFFFFF"
        )
        header_font = Font(
            name="Segoe UI", size=9, bold=True, color="FFFFFF"
        )
        header_alignment = Alignment(
            horizontal="center", vertical="center",
            readingOrder=2, wrap_text=True
        )
        body_alignment = Alignment(
            horizontal="right", vertical="center",
            readingOrder=2, wrap_text=True
        )
        center_alignment = Alignment(
            horizontal="center", vertical="center",
            readingOrder=2, wrap_text=True
        )
        thin_border = Border(
            left=Side(style="thin", color="D9E2E5"),
            right=Side(style="thin", color="D9E2E5"),
            top=Side(style="thin", color="D9E2E5"),
            bottom=Side(style="thin", color="D9E2E5")
        )
        inactive_fill = PatternFill(fill_type="solid", fgColor="FDEAEA")
        group_alt_fill = PatternFill(fill_type="solid", fgColor="F8FAFC")

        total_columns = len(
            DocumentSubgroupExcelFlatService.EXPORT_COLUMNS
        )

        # ------------------------------------------------
        # ★ ردیف اول: گروه‌بندی ستون‌ها (عنوان بخش)
        # ------------------------------------------------
        col_index = 1
        for group_key, group_info in (
            DocumentSubgroupExcelFlatService.COLUMN_GROUPS.items()
        ):
            group_color = group_info["color"]
            group_cols = group_info["columns"]
            span = len(group_cols)

            cell = worksheet.cell(
                row=1, column=col_index,
                value=group_info["title"]
            )
            cell.font = group_header_font
            cell.fill = PatternFill(
                fill_type="solid", fgColor=group_color
            )
            cell.alignment = header_alignment
            cell.border = thin_border

            # ★ merge کردن سلول‌ها
            if span > 1:
                end_col = col_index + span - 1
                worksheet.merge_cells(
                    start_row=1, start_column=col_index,
                    end_row=1, end_column=end_col
                )
                # ★ اعمال border به همه سلول‌های merge شده
                for c in range(col_index, end_col + 1):
                    worksheet.cell(row=1, column=c).border = thin_border
                    worksheet.cell(row=1, column=c).fill = PatternFill(
                        fill_type="solid", fgColor=group_color
                    )

            col_index += span

        # ------------------------------------------------
        # ★ ردیف دوم: هدر ستون‌ها
        # ------------------------------------------------
        for column_index, (_, persian_name) in enumerate(
            DocumentSubgroupExcelFlatService.EXPORT_COLUMNS, start=1
        ):
            # ★ پیدا کردن رنگ گروه مربوطه
            field_name = DocumentSubgroupExcelFlatService.EXPORT_COLUMNS[
                column_index - 1
            ][0]

            group_color = "3D8499"  # پیش‌فرض
            for gk, ginfo in (
                DocumentSubgroupExcelFlatService.COLUMN_GROUPS.items()
            ):
                if field_name in ginfo["columns"]:
                    group_color = ginfo["color"]
                    break

            cell = worksheet.cell(
                row=2, column=column_index, value=persian_name
            )
            cell.font = header_font
            cell.fill = PatternFill(
                fill_type="solid", fgColor=group_color
            )
            cell.alignment = header_alignment
            cell.border = thin_border

        # ------------------------------------------------
        # ★ بدنه داده‌ها (شروع از ردیف 3)
        # ------------------------------------------------
        for row_index, item in enumerate(data, start=3):
            for column_index, (field, _) in enumerate(
                DocumentSubgroupExcelFlatService.EXPORT_COLUMNS, start=1
            ):
                value = item.get(field)

                # ★ None → خالی نشون داده بشه
                if value is None:
                    value = ""

                cell = worksheet.cell(
                    row=row_index, column=column_index, value=value
                )
                cell.font = body_font
                cell.border = thin_border

                # ★ ستون‌هایی که مرکزچین بشن
                if field in {
                    "subgroup_id", "subgroup_code", "days_review",
                    "subgroup_sort_order", "is_active_label",
                    "group_id", "group_code", "group_sort_order",
                    "department_id", "department_code",
                    "department_sort_order", "documents_count",
                }:
                    cell.alignment = center_alignment
                else:
                    cell.alignment = body_alignment

                # ★ رنگ ستون وضعیت
                if field == "is_active_label":
                    if value == "غیرفعال":
                        cell.fill = inactive_fill
                        cell.font = Font(
                            name="Segoe UI", size=9,
                            bold=True, color="C53030"
                        )
                    elif value == "فعال":
                        cell.font = Font(
                            name="Segoe UI", size=9,
                            bold=True, color="276749"
                        )

                # ★ روز بررسی برجسته
                if field == "days_review" and value != "":
                    cell.font = Font(
                        name="Segoe UI", size=10,
                        bold=True, color="167A5C"
                    )

                # ★ تعداد اسناد برجسته
                if field == "documents_count" and value != "":
                    cell.font = Font(
                        name="Segoe UI", size=10,
                        bold=True, color="1B698B"
                    )

                # ★ "—" برای گروه/دپارتمان خالی
                if value == "—":
                    cell.font = Font(
                        name="Segoe UI", size=9,
                        bold=False, italic=True, color="A0AEB8"
                    )

        # ------------------------------------------------
        # ★ تنظیمات نهایی
        # ------------------------------------------------
        worksheet.row_dimensions[1].height = 28  # ردیف گروه‌بندی
        worksheet.row_dimensions[2].height = 34  # ردیف هدر

        for row_index in range(3, len(data) + 3):
            worksheet.row_dimensions[row_index].height = 22

        # ★ عرض ستون‌ها
        for column_index, width in (
            DocumentSubgroupExcelFlatService.EXPORT_WIDTHS.items()
        ):
            worksheet.column_dimensions[
                get_column_letter(column_index)
            ].width = width

        last_column = get_column_letter(total_columns)
        last_row = len(data) + 2

        # ★ فریز کردن تا ردیف 2
        worksheet.freeze_panes = "A3"

        # ★ فیلتر روی ردیف هدر (ردیف 2)
        if last_row > 2:
            worksheet.auto_filter.ref = f"A2:{last_column}{last_row}"

        worksheet.sheet_view.rightToLeft = True
        worksheet.sheet_properties.pageSetUpPr.fitToPage = True
        worksheet.page_setup.orientation = "landscape"
        worksheet.page_setup.fitToWidth = 1
        worksheet.page_setup.fitToHeight = 0
        worksheet.print_title_rows = "1:2"

        return workbook

    # ============================================================
    # ★ خروجی نهایی
    # ============================================================
    @staticmethod
    def export_subgroups_flat(group_id=None, department_id=None):
        """خروجی اکسل Flat زیرگروه‌ها"""
        data = DocumentSubgroupExcelFlatService.get_flat_data(
            group_id=group_id,
            department_id=department_id,
        )
        workbook = DocumentSubgroupExcelFlatService._create_workbook(data)
        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)
        return output

    @staticmethod
    def build_flat_filename(group_id=None, department_id=None):
        """نام فایل خروجی Flat"""
        try:
            import jdatetime
            date_str = jdatetime.date.today().strftime("%Y%m%d")
        except Exception:
            date_str = datetime.now().strftime("%Y%m%d")

        parts = ["document_subgroups_flat"]
        if group_id:
            parts.append(f"group_{group_id}")
        if department_id:
            parts.append(f"dept_{department_id}")
        parts.append(date_str)

        return "_".join(parts) + ".xlsx"