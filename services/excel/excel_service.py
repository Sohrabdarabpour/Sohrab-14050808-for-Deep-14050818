import io
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from config import Config
from helpers.date_helper import DateHelper
from database.connection import get_connection
from database.documents import add_documents_bulk


class ExcelService:
    BATCH_SIZE = 1000

    # ============================================================
    # ★ فیلدهای قابل Import/Export
    # ============================================================
    DOCUMENT_FIELDS = {
        # ---------- شناسه سند ----------
        "id",

        # ---------- اطلاعات اصلی ----------
        "code_dfc",
        "date_letter",
        "automation_number",
        "contractor_letter_number",
        "subject",
        "contract_number",
        "project_name",
        "contractor",
        "area",
        "date_received",
        "date_referral",
        "expert_name",
        "unit",
        "document_group",
        "sub_group",
        "deadline",
        "request_complete_docs",
        "complete_docs_by_contractor",
        "doc_response_status",
        "response_announce_date",
        "final_letter_number",
        "final_delay",
        "colleague",
        "Responsible_Party",

        # ---------- شناسه‌های ارجاعی ----------
        "user_id",
        "status_id",
        "area_id",
        "department_id",
        "group_id",
        "subgroup_id",
        "contractor_id",     # ★ جدید
        "project_id",        # ★ جدید
    }

    # ============================================================
    # ★ ستون‌های فایل قالب
    # ============================================================
    TEMPLATE_COLUMNS = [
        # ---------- شناسه‌ها ----------
        ("id", "شناسه سند"),
        
        # ---------- اطلاعات اصلی ----------
        ("code_dfc", "کد DFC"),
        ("date_letter", "تاریخ نامه"),
        ("automation_number", "شماره اتوماسیون"),
        ("contractor_letter_number", "شماره نامه پیمانکار"),
        ("subject", "موضوع"),
        ("contract_number", "شماره قرارداد"),
        ("project_name", "نام پروژه"),
        ("contractor", "پیمانکار"),
        ("area", "ناحیه / منطقه"),
        ("date_received", "تاریخ دریافت"),
        ("date_referral", "تاریخ ارجاع"),
        ("expert_name", "نام کارشناس"),
        ("unit", "واحد"),
        ("document_group", "گروه سند"),
        ("sub_group", "زیرگروه"),
        ("deadline", "مهلت پاسخ"),
        ("request_complete_docs", "درخواست تکمیل مدارک"),
        ("complete_docs_by_contractor", "تکمیل مدارک توسط پیمانکار"),
        ("doc_response_status", "وضعیت پاسخ مدرک"),
        ("response_announce_date", "تاریخ اعلام پاسخ"),
        ("final_send_date", "تاریخ ارسال نهایی"),
        ("final_letter_number", "شماره نامه نهایی"),
        ("final_delay", "تاخیر نهایی"),
        ("colleague", "همکار"),
        ("Responsible_Party", "طرف مسئول"),

        # ---------- شناسه‌های ارجاعی ----------
        ("user_id", "شناسه کاربر"),
        ("status_id", "شناسه وضعیت"),
        ("area_id", "شناسه ناحیه"),
        ("department_id", "شناسه دپارتمان"),
        ("group_id", "شناسه گروه"),
        ("subgroup_id", "شناسه زیرگروه"),
        ("contractor_id", "شناسه پیمانکار"),
        ("project_id", "شناسه پروژه"),
    ]

    TEMPLATE_ROWS = 100

    # ============================================================
    # ★ عرض ستون‌های فایل قالب
    # ============================================================
    TEMPLATE_WIDTHS = {
        # ============================================================
        # ★ شناسه سند (اول فایل)
        # ============================================================
        1: 12,    # شناسه سند

        # ============================================================
        # اطلاعات اصلی
        # ============================================================
        2: 18,    # کد DFC
        3: 16,    # تاریخ نامه
        4: 20,    # شماره اتوماسیون
        5: 20,    # شماره نامه پیمانکار
        6: 35,    # موضوع
        7: 20,    # شماره قرارداد
        8: 28,    # نام پروژه
        9: 25,    # پیمانکار
        10: 18,   # ناحیه
        11: 16,   # تاریخ دریافت
        12: 16,   # تاریخ ارجاع
        13: 22,   # نام کارشناس
        14: 15,   # واحد
        15: 20,   # گروه سند
        16: 22,   # زیرگروه
        17: 20,   # مهلت پاسخ
        18: 16,   # درخواست تکمیل مدارک
        19: 24,   # تکمیل مدارک توسط پیمانکار
        20: 28,   # وضعیت پاسخ مدرک
        21: 24,   # تاریخ اعلام پاسخ
        22: 22,   # ★ جدید: تاریخ ارسال نهایی
        23: 20,   # شماره نامه نهایی
        24: 20,   # تاخیر نهایی
        25: 16,   # همکار
        26: 20,   # طرف مسئول

        # ============================================================
        # شناسه‌های ارجاعی
        # ============================================================
        27: 22,   # شناسه کاربر
        28: 15,   # شناسه وضعیت
        29: 15,   # شناسه ناحیه
        30: 18,   # شناسه دپارتمان
        31: 15,   # شناسه گروه
        32: 15,   # شناسه زیرگروه

        # ============================================================
        # ★ شناسه‌های پیمانکار و پروژه (آخر فایل)
        # ============================================================
        33: 18,   # شناسه پیمانکار
        34: 15,   # شناسه پروژه
    }
    
    # ============================================================
    # خواندن فایل
    # ============================================================
    @staticmethod
    def read_file(file_path):
        return pd.read_excel(file_path)

    # ============================================================
    # تبدیل نام ستون‌ها (فارسی → انگلیسی)
    # ============================================================
    @staticmethod
    def rename_columns(dataframe):
        mapping = {}
        for column in dataframe.columns:
            column_name = str(column).strip()
            mapping[column] = Config.EXCEL_COLUMN_MAPPING.get(
                column_name,
                column_name
            )
        return dataframe.rename(columns=mapping)

    # ============================================================
    # تمیزکاری مقادیر
    # ============================================================
    @staticmethod
    def clean_value(value):
        if pd.isna(value):
            return None
        if isinstance(value, str):
            value = value.strip()
            return value if value else None
        return value

    @staticmethod
    def clean_integer(value):
        value = ExcelService.clean_value(value)
        if value is None:
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    # ============================================================
    # ★ آماده‌سازی یک ردیف
    # ============================================================
    @staticmethod
    def prepare_row(row):
        data = {}
        for field, value in row.items():
            if field not in ExcelService.DOCUMENT_FIELDS:
                continue
            value = ExcelService.clean_value(value)

            # ---------- شناسه‌ها (Integer) ----------
            if field in {
                "user_id",
                "status_id",
                "area_id",
                "department_id",
                "group_id",
                "subgroup_id",
                "contractor_id",     # ★ جدید
                "project_id",        # ★ جدید
            }:
                value = ExcelService.clean_integer(value)

            # ---------- تاریخ‌ها ----------
            if field in Config.DATE_FIELDS and value is not None:
                value = DateHelper.convert_to_gregorian(value)

            data[field] = value

        # ★ حذف id (auto-increment — همیشه توسط SQLite تولید می‌شه)
        data.pop("id", None)

        return data

    @staticmethod
    def prepare_batch(dataframe):
        documents = []
        for _, row in dataframe.iterrows():
            data = ExcelService.prepare_row(row)
            if any(value is not None for value in data.values()):
                documents.append(data)
        return documents

    # ============================================================
    # تعداد اسناد
    # ============================================================
    @staticmethod
    def get_document_count():
        connection = get_connection()
        try:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM documents"
            ).fetchone()
            return row["total"]
        finally:
            connection.close()

    # ============================================================
    # ★ اعتبارسنجی شناسه‌های ارجاعی
    # ============================================================
    @staticmethod
    def validate_reference_ids(documents):
        user_ids = {
            d["user_id"] for d in documents
            if d.get("user_id") is not None
        }
        status_ids = {
            d["status_id"] for d in documents
            if d.get("status_id") is not None
        }
        area_ids = {
            d["area_id"] for d in documents
            if d.get("area_id") is not None
        }
        department_ids = {
            d["department_id"] for d in documents
            if d.get("department_id") is not None
        }
        group_ids = {
            d["group_id"] for d in documents
            if d.get("group_id") is not None
        }
        subgroup_ids = {
            d["subgroup_id"] for d in documents
            if d.get("subgroup_id") is not None
        }
        # ★ جدید
        contractor_ids = {
            d["contractor_id"] for d in documents
            if d.get("contractor_id") is not None
        }
        project_ids = {
            d["project_id"] for d in documents
            if d.get("project_id") is not None
        }

        connection = get_connection()
        try:
            valid_user_ids = {
                r["id"] for r in connection.execute(
                    "SELECT id FROM users"
                ).fetchall()
            }
            valid_status_ids = {
                r["id"] for r in connection.execute(
                    "SELECT id FROM document_statuses"
                ).fetchall()
            }
            valid_area_ids = {
                r["id"] for r in connection.execute(
                    "SELECT id FROM areas"
                ).fetchall()
            }
            valid_department_ids = {
                r["id"] for r in connection.execute(
                    "SELECT id FROM departments"
                ).fetchall()
            }
            valid_group_ids = {
                r["id"] for r in connection.execute(
                    "SELECT id FROM document_groups"
                ).fetchall()
            }
            valid_subgroup_ids = {
                r["id"] for r in connection.execute(
                    "SELECT id FROM document_subgroups"
                ).fetchall()
            }
            # ★ جدید
            valid_contractor_ids = {
                r["id"] for r in connection.execute(
                    "SELECT id FROM contractors"
                ).fetchall()
            }
            valid_project_ids = {
                r["id"] for r in connection.execute(
                    "SELECT id FROM projects"
                ).fetchall()
            }
        finally:
            connection.close()

        return {
            "user_ids": user_ids - valid_user_ids,
            "status_ids": status_ids - valid_status_ids,
            "area_ids": area_ids - valid_area_ids,
            "department_ids": department_ids - valid_department_ids,
            "group_ids": group_ids - valid_group_ids,
            "subgroup_ids": subgroup_ids - valid_subgroup_ids,
            # ★ جدید
            "contractor_ids": contractor_ids - valid_contractor_ids,
            "project_ids": project_ids - valid_project_ids,
        }

    # ============================================================
    # ★ ورود فایل
    # ============================================================
    @staticmethod
    def import_file(file_path, mode="append"):
        if mode not in ("append", "replace"):
            return {
                "success": False,
                "mode": mode,
                "total": 0,
                "success_count": 0,
                "error_count": 0,
                "error_rows": [],
                "message": "حالت ورود اطلاعات نامعتبر است"
            }

        try:
            dataframe = ExcelService.read_file(file_path)
        except Exception as error:
            return {
                "success": False,
                "mode": mode,
                "total": 0,
                "success_count": 0,
                "error_count": 0,
                "error_rows": [],
                "message": f"خطا در خواندن فایل Excel: {error}"
            }

        dataframe = ExcelService.rename_columns(dataframe)
        total = len(dataframe)

        documents = []
        skipped_rows = []
        for index, row in dataframe.iterrows():
            data = ExcelService.prepare_row(row)
            if any(value is not None for value in data.values()):
                documents.append(data)
            else:
                skipped_rows.append(index + 2)

        if not documents:
            return {
                "success": False,
                "mode": mode,
                "total": total,
                "success_count": 0,
                "error_count": 0,
                "error_rows": skipped_rows,
                "message": "فایل Excel فاقد اطلاعات قابل ورود است"
            }

        # ---------- ★ اعتبارسنجی شناسه‌ها ----------
        invalid_ids = ExcelService.validate_reference_ids(documents)
        if any(invalid_ids.values()):
            messages = []
            if invalid_ids["user_ids"]:
                messages.append(
                    f"شناسه کاربر نامعتبر: {sorted(invalid_ids['user_ids'])}"
                )
            if invalid_ids["status_ids"]:
                messages.append(
                    f"شناسه وضعیت نامعتبر: {sorted(invalid_ids['status_ids'])}"
                )
            if invalid_ids["area_ids"]:
                messages.append(
                    f"شناسه ناحیه نامعتبر: {sorted(invalid_ids['area_ids'])}"
                )
            if invalid_ids["department_ids"]:
                messages.append(
                    f"شناسه دپارتمان نامعتبر: "
                    f"{sorted(invalid_ids['department_ids'])}"
                )
            if invalid_ids["group_ids"]:
                messages.append(
                    f"شناسه گروه نامعتبر: {sorted(invalid_ids['group_ids'])}"
                )
            if invalid_ids["subgroup_ids"]:
                messages.append(
                    f"شناسه زیرگروه نامعتبر: "
                    f"{sorted(invalid_ids['subgroup_ids'])}"
                )
            # ★ جدید
            if invalid_ids["contractor_ids"]:
                messages.append(
                    f"شناسه پیمانکار نامعتبر: "
                    f"{sorted(invalid_ids['contractor_ids'])}"
                )
            if invalid_ids["project_ids"]:
                messages.append(
                    f"شناسه پروژه نامعتبر: "
                    f"{sorted(invalid_ids['project_ids'])}"
                )

            return {
                "success": False,
                "mode": mode,
                "total": total,
                "success_count": 0,
                "error_count": len(documents),
                "error_rows": [],
                "message": "؛ ".join(messages)
            }

        if mode == "append":
            return ExcelService._import_append(
                documents, total, skipped_rows
            )

        return ExcelService._import_replace(
            documents, total, skipped_rows
        )

    # ============================================================
    # ★ Append
    # ============================================================
    @staticmethod
    def _import_append(documents, total, skipped_rows):
        success_count = 0
        error_count = 0
        error_rows = list(skipped_rows)
        document_index = 0

        for start in range(0, len(documents), ExcelService.BATCH_SIZE):
            batch = documents[start:start + ExcelService.BATCH_SIZE]
            inserted = add_documents_bulk(batch)
            success_count += inserted
            if inserted < len(batch):
                failed = len(batch) - inserted
                error_count += failed
                for offset in range(failed):
                    error_rows.append(document_index + offset + 2)
            document_index += len(batch)

        error_count += len(skipped_rows)

        return {
            "success": error_count == 0,
            "mode": "append",
            "total": total,
            "success_count": success_count,
            "error_count": error_count,
            "error_rows": error_rows,
            "message": (
                "اطلاعات با موفقیت به داده‌های موجود اضافه شد"
                if error_count == 0
                else "ورود اطلاعات انجام شد اما بعضی ردیف‌ها دارای خطا بودند"
            )
        }

    # ============================================================
    # ★ Replace
    # ============================================================
    @staticmethod
    def _import_replace(documents, total, skipped_rows):
        connection = get_connection()
        success_count = 0
        error_count = 0
        error_rows = list(skipped_rows)

        try:
            connection.execute("BEGIN")
            connection.execute("DELETE FROM documents")

            for start in range(0, len(documents), ExcelService.BATCH_SIZE):
                batch = documents[start:start + ExcelService.BATCH_SIZE]
                fields = list(batch[0].keys())
                columns = ", ".join(fields)
                placeholders = ", ".join(["?"] * len(fields))
                values = [
                    [document.get(field) for field in fields]
                    for document in batch
                ]
                cursor = connection.executemany(
                    f"INSERT INTO documents ({columns}) "
                    f"VALUES ({placeholders})",
                    values
                )
                inserted = cursor.rowcount
                if inserted < 0:
                    inserted = len(batch)
                success_count += inserted

            error_count += len(skipped_rows)
            connection.commit()

            return {
                "success": error_count == 0,
                "mode": "replace",
                "total": total,
                "success_count": success_count,
                "error_count": error_count,
                "error_rows": error_rows,
                "message": (
                    "اطلاعات قبلی حذف و اطلاعات فایل با موفقیت جایگزین شد"
                    if error_count == 0
                    else "جایگزینی انجام شد اما بعضی ردیف‌ها خطا داشتند"
                )
            }

        except Exception as error:
            connection.rollback()
            return {
                "success": False,
                "mode": "replace",
                "total": total,
                "success_count": 0,
                "error_count": total,
                "error_rows": error_rows,
                "message": (
                    "جایگزینی اطلاعات انجام نشد و "
                    f"اطلاعات قبلی حفظ شد: {error}"
                )
            }
        finally:
            connection.close()

    # ============================================================
    # ★ ایجاد فایل قالب
    # ============================================================
    @staticmethod
    def _create_workbook():
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "اسناد"

        header_fill = PatternFill(
            fill_type="solid",
            fgColor="3D8499"
        )
        header_font = Font(
            name="Segoe UI", size=8, bold=True, color="FFFFFF"
        )
        body_font = Font(
            name="Segoe UI", size=8, bold=False, color="000000"
        )
        header_alignment = Alignment(
            horizontal="center",
            vertical="center",
            readingOrder=2,
            wrap_text=True
        )
        body_alignment = Alignment(
            horizontal="right",
            vertical="center",
            readingOrder=2,
            wrap_text=True
        )
        thin_border = Border(
            left=Side(style="thin", color="D9E2E5"),
            right=Side(style="thin", color="D9E2E5"),
            top=Side(style="thin", color="D9E2E5"),
            bottom=Side(style="thin", color="D9E2E5")
        )

        total_columns = len(ExcelService.TEMPLATE_COLUMNS)

        for column_index, (_, persian_name) in enumerate(
            ExcelService.TEMPLATE_COLUMNS, start=1
        ):
            cell = worksheet.cell(
                row=1,
                column=column_index,
                value=persian_name
            )
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border

        for row in worksheet.iter_rows(
            min_row=2,
            max_row=ExcelService.TEMPLATE_ROWS + 1,
            min_col=1,
            max_col=total_columns
        ):
            for cell in row:
                cell.font = body_font
                cell.alignment = body_alignment
                cell.border = thin_border

        worksheet.row_dimensions[1].height = 32
        for row_index in range(2, ExcelService.TEMPLATE_ROWS + 2):
            worksheet.row_dimensions[row_index].height = 22

        for column_index, width in ExcelService.TEMPLATE_WIDTHS.items():
            worksheet.column_dimensions[
                get_column_letter(column_index)
            ].width = width

        last_column = get_column_letter(total_columns)
        last_row = ExcelService.TEMPLATE_ROWS + 1

        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = f"A1:{last_column}{last_row}"
        worksheet.sheet_view.rightToLeft = True
        worksheet.sheet_properties.pageSetUpPr.fitToPage = True
        worksheet.page_setup.orientation = "landscape"
        worksheet.page_setup.fitToWidth = 1
        worksheet.page_setup.fitToHeight = 0
        worksheet.print_title_rows = "1:1"

        return workbook

    @staticmethod
    def export_template():
        workbook = ExcelService._create_workbook()
        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)
        return output

    @staticmethod
    def create_template():
        return ExcelService.export_template()


        # ============================================================
    # ★ Export داده‌های موجود
    # ============================================================
    @staticmethod
    def export_data(output_path=None, filters=None):
        """
        خروجی اکسل از داده‌های موجود

        Args:
            output_path (str): مسیر ذخیره (اختیاری)
            filters (dict): فیلترهای دلخواه

        Returns:
            str: مسیر فایل ذخیره‌شده
        """
        import os
        from datetime import datetime

        # ---- مسیر پیش‌فرض ----
        if output_path is None:
            base_dir = os.path.join(
                Config.UPLOAD_FOLDER, "excel_exports"
            )
            os.makedirs(base_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(
                base_dir, f"documents_export_{timestamp}.xlsx"
            )

        # ---- دریافت داده‌ها ----
        documents = ExcelService._get_documents_for_export(
            filters or {}
        )

        # ---- ساخت workbook ----
        workbook = ExcelService._create_workbook()

        # ---- حذف سطرهای خالی قالب ----
        worksheet = workbook.active
        # حذف سطرهای ۲ تا ۱۰۱ (قالب خالی)
        for row_idx in range(
            ExcelService.TEMPLATE_ROWS + 1, 1, -1
        ):
            worksheet.delete_rows(row_idx)

        # ---- نوشتن هدر (از قبل هست، دوباره نمی‌خواد) ----

        # ---- استایل داده‌ها ----
        body_font = Font(
            name="Segoe UI", size=8, bold=False, color="000000"
        )
        body_alignment = Alignment(
            horizontal="right",
            vertical="center",
            readingOrder=2,
            wrap_text=True
        )
        thin_border = Border(
            left=Side(style="thin", color="D9E2E5"),
            right=Side(style="thin", color="D9E2E5"),
            top=Side(style="thin", color="D9E2E5"),
            bottom=Side(style="thin", color="D9E2E5")
        )

        # ---- نوشتن داده‌ها ----
        for row_idx, doc in enumerate(documents, start=2):
            for col_idx, (field, _) in enumerate(
                ExcelService.TEMPLATE_COLUMNS, start=1
            ):
                value = doc.get(field, "")

                # ---- تبدیل‌های خاص ----
                if value is None:
                    value = ""

                # تاریخ شمسی (اگه تاریخ میلادی ذخیره شده)
                # if field in Config.DATE_FIELDS and value:
                #     try:
                #         value = DateHelper.format_jalali(value)
                #     except Exception:
                #         pass

                cell = worksheet.cell(
                    row=row_idx, column=col_idx, value=value
                )
                cell.font = body_font
                cell.alignment = body_alignment
                cell.border = thin_border

        # ---- تنظیم ارتفاع سطرها ----
        for row_idx in range(2, len(documents) + 2):
            worksheet.row_dimensions[row_idx].height = 22

        # ---- به‌روزرسانی auto_filter ----
        last_column = get_column_letter(
            len(ExcelService.TEMPLATE_COLUMNS)
        )
        last_row = max(len(documents) + 1, 1)
        worksheet.auto_filter.ref = f"A1:{last_column}{last_row}"

        # ---- ذخیره ----
        workbook.save(output_path)
        return output_path

    # ============================================================
    # ★ دریافت اسناد برای Export
    # ============================================================
    @staticmethod
    def _get_documents_for_export(filters):
        """
        دریافت اسناد از دیتابیس با فیلتر

        Args:
            filters (dict): {
                "year": int | "all",
                "status_id": int,
                "area_id": int,
                "user_id": int,
                "contractor_id": int,
                "project_id": int,
                "only_active": bool,
            }

        Returns:
            list[dict]
        """
        connection = get_connection()
        try:
            sql = "SELECT * FROM documents WHERE 1=1"
            params = []

            year = filters.get("year")
            if year and year != "all":
                # فیلتر بر اساس سال (تاریخ دریافت)
                sql += " AND date_received LIKE ?"
                params.append(f"{year}%")

            status_id = filters.get("status_id")
            if status_id:
                sql += " AND status_id = ?"
                params.append(status_id)

            area_id = filters.get("area_id")
            if area_id:
                sql += " AND area_id = ?"
                params.append(area_id)

            department_id = filters.get("department_id")
            if department_id:
                sql += " AND department_id = ?"
                params.append(department_id)

            user_id = filters.get("user_id")
            if user_id:
                sql += " AND user_id = ?"
                params.append(user_id)

            contractor_id = filters.get("contractor_id")
            if contractor_id:
                sql += " AND contractor_id = ?"
                params.append(contractor_id)

            project_id = filters.get("project_id")
            if project_id:
                sql += " AND project_id = ?"
                params.append(project_id)

            # اگه خواستی فقط اسناد فعال:
            # (اگه ستون is_active توی documents داشتی)

            sql += " ORDER BY id DESC"
            rows = connection.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            connection.close()