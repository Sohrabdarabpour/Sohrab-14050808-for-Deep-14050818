import io
import pandas as pd
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from database.connection import get_connection


class DocumentSubgroupExcelService:
    """سرویس خروجی و ورودی اکسل زیرگروه‌های سند (ساختار M:N — بدون primary)"""

    # ============================================================
    # ★ ستون‌های خروجی
    # ============================================================
    EXPORT_COLUMNS = [
        ("id", "شناسه"),
        ("title", "عنوان زیرگروه"),
        ("code", "کد زیرگروه"),
        ("groups_titles", "گروه‌های مرتبط"),          # ★ M:N
        ("departments_titles", "دپارتمان‌های متولی"),  # ★ M:N
        ("days_review", "بازه بررسی (روز)"),
        ("documents_count", "تعداد اسناد"),
        ("sort_order", "ترتیب نمایش"),
        ("is_active_label", "وضعیت"),
        ("created_at", "تاریخ ایجاد"),
    ]

    # ============================================================
    # ★ عرض ستون‌های خروجی
    # ============================================================
    EXPORT_WIDTHS = {
        1: 10,   # شناسه
        2: 35,   # عنوان زیرگروه
        3: 12,   # کد زیرگروه
        4: 45,   # گروه‌های مرتبط
        5: 45,   # دپارتمان‌های متولی
        6: 15,   # بازه بررسی
        7: 15,   # تعداد اسناد
        8: 15,   # ترتیب نمایش
        9: 12,   # وضعیت
        10: 22,  # تاریخ ایجاد
    }

    # ============================================================
    # ★ نگاشت ستون‌های ایمپورت
    # ============================================================
    IMPORT_COLUMN_MAPPING = {
        "عنوان زیرگروه": "title",
        "زیرگروه": "title",
        "نام زیرگروه": "title",
        "کد زیرگروه": "code",
        "کد": "code",
        "بازه بررسی": "days_review",
        "بازه بررسی (روز)": "days_review",
        "بازه": "days_review",
        "روز": "days_review",
        "رنگ": "color",
        "توضیحات": "description",
        "ترتیب نمایش": "sort_order",
        "ترتیب": "sort_order",
        "وضعیت": "is_active",
        "فعال": "is_active",
        # ★ گروه‌ها (M:N) — با کاما جدا میشن
        "گروه‌های مرتبط": "groups",
        "گروه‌ها": "groups",
        "گروه سند": "groups",
        "گروه": "groups",
        # ★ دپارتمان‌ها (M:N) — با کاما جدا میشن
        "دپارتمان‌های متولی": "departments",
        "دپارتمان‌ها": "departments",
        "دپارتمان": "departments",
        "واحد متولی": "departments",
    }

    # ============================================================
    # ★ دریافت داده‌ها برای خروجی
    # ============================================================
    @staticmethod
    def get_data(group_id=None, department_id=None):
        """
        دریافت لیست زیرگروه‌ها با اطلاعات M:N

        پارامترها:
            group_id      : فیلتر بر اساس گروه
            department_id : فیلتر بر اساس دپارتمان
        """
        connection = get_connection()
        try:
            query = """
                SELECT
                    sg.id,
                    sg.title,
                    sg.code,
                    sg.color,
                    sg.days_review,
                    sg.description,
                    sg.sort_order,
                    sg.is_active,
                    sg.created_at,
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

            result = []
            for row in rows:
                item = dict(row)

                # ★ گروه‌های مرتبط (M:N)
                groups = connection.execute("""
                    SELECT g.title
                    FROM document_groups g
                    INNER JOIN group_subgroups gs
                        ON gs.group_id = g.id
                    WHERE gs.subgroup_id = ?
                    ORDER BY gs.sort_order ASC, g.title ASC
                """, (item["id"],)).fetchall()

                item["groups_titles"] = "، ".join(
                    [g["title"] for g in groups]
                ) if groups else "—"

                # ★ دپارتمان‌های متولی (M:N) — بدون is_primary
                departments = connection.execute("""
                    SELECT d.title
                    FROM departments d
                    INNER JOIN subgroup_departments sd
                        ON sd.department_id = d.id
                    WHERE sd.subgroup_id = ?
                    ORDER BY d.title ASC
                """, (item["id"],)).fetchall()

                item["departments_titles"] = "، ".join(
                    [d["title"] for d in departments]
                ) if departments else "—"

                item["is_active_label"] = (
                    "فعال" if item["is_active"] else "غیرفعال"
                )

                result.append(item)

            return result
        finally:
            connection.close()

    # ============================================================
    # ★ ساخت فایل اکسل خروجی
    # ============================================================
    @staticmethod
    def _create_workbook(data):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "زیرگروه‌های سند"

        header_fill = PatternFill(fill_type="solid", fgColor="167A5C")
        header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
        body_font = Font(name="Segoe UI", size=9, bold=False, color="000000")
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

        total_columns = len(
            DocumentSubgroupExcelService.EXPORT_COLUMNS
        )

        # هدر
        for column_index, (_, persian_name) in enumerate(
            DocumentSubgroupExcelService.EXPORT_COLUMNS, start=1
        ):
            cell = worksheet.cell(
                row=1, column=column_index, value=persian_name
            )
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border

        # بدنه
        for row_index, item in enumerate(data, start=2):
            for column_index, (field, _) in enumerate(
                DocumentSubgroupExcelService.EXPORT_COLUMNS, start=1
            ):
                value = item.get(field)
                cell = worksheet.cell(
                    row=row_index, column=column_index, value=value
                )
                cell.font = body_font
                cell.border = thin_border

                if field in {
                    "id", "code", "days_review",
                    "documents_count", "sort_order",
                    "is_active_label", "created_at"
                }:
                    cell.alignment = center_alignment
                else:
                    cell.alignment = body_alignment

                if field == "is_active_label" and value == "غیرفعال":
                    cell.fill = inactive_fill
                    cell.font = Font(
                        name="Segoe UI", size=9,
                        bold=True, color="C53030"
                    )
                elif field == "is_active_label" and value == "فعال":
                    cell.font = Font(
                        name="Segoe UI", size=9,
                        bold=True, color="276749"
                    )

                if field == "days_review":
                    cell.font = Font(
                        name="Segoe UI", size=10,
                        bold=True, color="167A5C"
                    )

        # تنظیمات
        worksheet.row_dimensions[1].height = 34
        for row_index in range(2, len(data) + 2):
            worksheet.row_dimensions[row_index].height = 24

        for column_index, width in (
            DocumentSubgroupExcelService.EXPORT_WIDTHS.items()
        ):
            worksheet.column_dimensions[
                get_column_letter(column_index)
            ].width = width

        last_column = get_column_letter(total_columns)
        last_row = len(data) + 1

        worksheet.freeze_panes = "A2"
        if last_row > 1:
            worksheet.auto_filter.ref = f"A1:{last_column}{last_row}"
        worksheet.sheet_view.rightToLeft = True
        worksheet.sheet_properties.pageSetUpPr.fitToPage = True
        worksheet.page_setup.orientation = "landscape"
        worksheet.page_setup.fitToWidth = 1
        worksheet.page_setup.fitToHeight = 0
        worksheet.print_title_rows = "1:1"

        return workbook

    # ============================================================
    # ★ خروجی نهایی
    # ============================================================
    @staticmethod
    def export_subgroups(group_id=None, department_id=None):
        """خروجی اکسل زیرگروه‌ها"""
        data = DocumentSubgroupExcelService.get_data(
            group_id=group_id,
            department_id=department_id,
        )
        workbook = DocumentSubgroupExcelService._create_workbook(data)
        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)
        return output

    @staticmethod
    def build_export_filename(group_id=None, department_id=None):
        """ساخت نام فایل خروجی با تاریخ شمسی"""
        try:
            import jdatetime
            date_str = jdatetime.date.today().strftime("%Y%m%d")
        except Exception:
            date_str = datetime.now().strftime("%Y%m%d")

        parts = ["document_subgroups"]
        if group_id:
            parts.append(f"group_{group_id}")
        if department_id:
            parts.append(f"dept_{department_id}")
        parts.append(date_str)

        return "_".join(parts) + ".xlsx"

    # ============================================================
    # ★★★ بخش ایمپورت ★★★
    # ============================================================
    @staticmethod
    def read_import_file(file_path):
        """خواندن فایل اکسل برای ایمپورت"""
        try:
            dataframe = pd.read_excel(file_path)
        except Exception as error:
            return None, f"خطا در خواندن فایل: {error}"

        mapping = {}
        for column in dataframe.columns:
            column_name = str(column).strip()
            mapped = DocumentSubgroupExcelService.IMPORT_COLUMN_MAPPING.get(
                column_name
            )
            if mapped:
                mapping[column] = mapped

        dataframe = dataframe.rename(columns=mapping)

        if "title" not in dataframe.columns:
            return None, "ستون «عنوان زیرگروه» در فایل پیدا نشد."

        # ★ چک: حداقل یکی از گروه‌ها یا دپارتمان‌ها
        has_relation = (
            "groups" in dataframe.columns
            or "departments" in dataframe.columns
        )
        if not has_relation:
            return None, (
                "ستون «گروه‌های مرتبط» یا «دپارتمان‌های متولی» "
                "در فایل پیدا نشد."
            )

        return dataframe, None

    @staticmethod
    def _split_multi_value(raw):
        """
        تبدیل رشته با کاما به لیست
        پشتیبانی از «،» فارسی و «,» انگلیسی و «;»
        """
        if pd.isna(raw) or not str(raw).strip():
            return []
        text = str(raw).strip()
        for sep in ["؛", ";", "،"]:
            text = text.replace(sep, ",")
        return [s.strip() for s in text.split(",") if s.strip()]

    @staticmethod
    def _build_group_maps(connection):
        """ساخت نقشه کد/عنوان گروه → شناسه"""
        rows = connection.execute("""
            SELECT id, code, title
            FROM document_groups
        """).fetchall()

        by_code = {}
        by_title = {}
        for row in rows:
            if row["code"]:
                by_code[row["code"].strip().lower()] = row["id"]
            if row["title"]:
                by_title[row["title"].strip()] = row["id"]

        return by_code, by_title

    @staticmethod
    def _build_department_maps(connection):
        """ساخت نقشه نام/کد دپارتمان → شناسه"""
        rows = connection.execute("""
            SELECT id, title, code
            FROM departments
        """).fetchall()

        by_title = {}
        by_code = {}
        for row in rows:
            if row["title"]:
                by_title[row["title"].strip()] = row["id"]
            if row["code"]:
                by_code[row["code"].strip().lower()] = row["id"]

        return by_title, by_code

    @staticmethod
    def _resolve_group_ids(
        raw_groups, group_by_code, group_by_title
    ):
        """
        تبدیل لیست عنوان/کد گروه به لیست شناسه
        پشتیبانی از شناسه عددی مستقیم
        """
        group_ids = []
        for item in raw_groups:
            item_str = str(item).strip()
            if not item_str:
                continue

            # ★ اگه عدد بود، مستقیم به عنوان id
            try:
                gid = int(float(item_str))
                group_ids.append(gid)
                continue
            except (ValueError, TypeError):
                pass

            # ★ جستجو در code و title
            gid = (
                group_by_code.get(item_str.lower())
                or group_by_title.get(item_str)
            )
            if gid:
                group_ids.append(gid)

        return group_ids

    @staticmethod
    def _resolve_department_ids(
        raw_departments, dept_by_title, dept_by_code
    ):
        """تبدیل لیست عنوان/کد دپارتمان به لیست شناسه"""
        dept_ids = []
        for item in raw_departments:
            item_str = str(item).strip()
            if not item_str:
                continue

            try:
                did = int(float(item_str))
                dept_ids.append(did)
                continue
            except (ValueError, TypeError):
                pass

            did = (
                dept_by_title.get(item_str)
                or dept_by_code.get(item_str.lower())
            )
            if did:
                dept_ids.append(did)

        return dept_ids

    @staticmethod
    def _prepare_import_row(
        row, group_by_code, group_by_title,
        dept_by_title, dept_by_code
    ):
        """پردازش یک ردیف برای ایمپورت"""
        data = {}

        # عنوان (الزامی)
        title = row.get("title")
        if pd.isna(title) or not str(title).strip():
            return None
        data["title"] = str(title).strip()

        # کد زیرگروه
        code = row.get("code")
        if not pd.isna(code) and str(code).strip():
            data["code"] = str(code).strip()
        else:
            data["code"] = None

        # بازه بررسی
        days = row.get("days_review")
        if not pd.isna(days):
            try:
                data["days_review"] = int(float(days))
            except (ValueError, TypeError):
                data["days_review"] = 0
        else:
            data["days_review"] = 0

        # رنگ
        color = row.get("color")
        if not pd.isna(color) and str(color).strip():
            color_str = str(color).strip()
            if not color_str.startswith("#"):
                color_str = f"#{color_str}"
            data["color"] = color_str
        else:
            data["color"] = "#3D8499"

        # توضیحات
        description = row.get("description")
        if not pd.isna(description) and str(description).strip():
            data["description"] = str(description).strip()
        else:
            data["description"] = None

        # ترتیب
        sort_order = row.get("sort_order")
        if not pd.isna(sort_order):
            try:
                data["sort_order"] = int(float(sort_order))
            except (ValueError, TypeError):
                data["sort_order"] = 0
        else:
            data["sort_order"] = 0

        # وضعیت
        is_active = row.get("is_active")
        if pd.isna(is_active):
            data["is_active"] = 1
        else:
            if isinstance(is_active, (int, float)):
                data["is_active"] = 1 if int(is_active) == 1 else 0
            else:
                active_str = str(is_active).strip().lower()
                if active_str in (
                    "فعال", "بله", "yes", "true", "1", "active"
                ):
                    data["is_active"] = 1
                elif active_str in (
                    "غیرفعال", "خیر", "no", "false", "0", "inactive"
                ):
                    data["is_active"] = 0
                else:
                    data["is_active"] = 1

        # ★ گروه‌ها (M:N)
        raw_groups = DocumentSubgroupExcelService._split_multi_value(
            row.get("groups")
        )
        data["group_ids"] = DocumentSubgroupExcelService._resolve_group_ids(
            raw_groups, group_by_code, group_by_title
        )

        # ★ دپارتمان‌ها (M:N) — بدون primary
        raw_depts = DocumentSubgroupExcelService._split_multi_value(
            row.get("departments")
        )
        data["department_ids"] = (
            DocumentSubgroupExcelService._resolve_department_ids(
                raw_depts, dept_by_title, dept_by_code
            )
        )

        return data

    @staticmethod
    def import_subgroups(file_path, mode="append"):
        """ایمپورت زیرگروه‌ها از فایل اکسل"""
        if mode not in ("append", "replace"):
            return {
                "success": False, "mode": mode, "total": 0,
                "success_count": 0, "error_count": 0,
                "error_rows": [], "message": "حالت ایمپورت نامعتبر است"
            }

        dataframe, error = DocumentSubgroupExcelService.read_import_file(
            file_path
        )
        if error:
            return {
                "success": False, "mode": mode, "total": 0,
                "success_count": 0, "error_count": 0,
                "error_rows": [], "message": error
            }

        total = len(dataframe)

        connection = get_connection()
        try:
            group_by_code, group_by_title = (
                DocumentSubgroupExcelService._build_group_maps(connection)
            )
            dept_by_title, dept_by_code = (
                DocumentSubgroupExcelService._build_department_maps(
                    connection
                )
            )
        finally:
            connection.close()

        subgroups = []
        skipped_rows = []

        for index, row in dataframe.iterrows():
            data = DocumentSubgroupExcelService._prepare_import_row(
                row, group_by_code, group_by_title,
                dept_by_title, dept_by_code
            )
            if data:
                subgroups.append(data)
            else:
                skipped_rows.append(index + 2)

        if not subgroups:
            return {
                "success": False, "mode": mode, "total": total,
                "success_count": 0, "error_count": 0,
                "error_rows": skipped_rows,
                "message": "هیچ زیرگروه معتبری در فایل پیدا نشد."
            }

        if mode == "append":
            return DocumentSubgroupExcelService._import_append(
                subgroups, total, skipped_rows
            )
        return DocumentSubgroupExcelService._import_replace(
            subgroups, total, skipped_rows
        )

    @staticmethod
    def _insert_relations(connection, subgroup_id, sg):
        """
        درج ارتباطات M:N یک زیرگروه
        ★ بدون is_primary
        """
        # ★ گروه‌ها
        for gid in sg.get("group_ids", []):
            connection.execute("""
                INSERT OR IGNORE INTO group_subgroups
                (group_id, subgroup_id, sort_order, is_active)
                VALUES (?, ?, 0, 1)
            """, (gid, subgroup_id))

        # ★ دپارتمان‌ها (بدون primary)
        for did in sg.get("department_ids", []):
            connection.execute("""
                INSERT OR IGNORE INTO subgroup_departments
                (subgroup_id, department_id)
                VALUES (?, ?)
            """, (subgroup_id, did))

    @staticmethod
    def _import_append(subgroups, total, skipped_rows):
        """افزودن زیرگروه‌ها به داده‌های موجود"""
        connection = get_connection()
        success_count = 0
        skipped_duplicates = 0
        error_rows = list(skipped_rows)

        try:
            for idx, sg in enumerate(subgroups):
                row_number = idx + 2

                # ★ چک تکراری بودن title (در کل سیستم)
                existing = connection.execute("""
                    SELECT id FROM document_subgroups WHERE title = ?
                """, (sg["title"],)).fetchone()

                if existing:
                    skipped_duplicates += 1
                    continue

                # ★ چک تکراری بودن code
                if sg["code"]:
                    existing_code = connection.execute("""
                        SELECT id FROM document_subgroups WHERE code = ?
                    """, (sg["code"],)).fetchone()
                    if existing_code:
                        sg["code"] = None

                try:
                    cursor = connection.execute("""
                        INSERT INTO document_subgroups
                        (title, code, color, days_review,
                         description, sort_order, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        sg["title"],
                        sg["code"],
                        sg["color"],
                        sg["days_review"],
                        sg["description"],
                        sg["sort_order"],
                        sg["is_active"],
                    ))
                    subgroup_id = cursor.lastrowid

                    # ★ درج ارتباطات M:N
                    DocumentSubgroupExcelService._insert_relations(
                        connection, subgroup_id, sg
                    )

                    success_count += 1
                except Exception:
                    error_rows.append(row_number)

            connection.commit()

            message_parts = [f"{success_count} زیرگروه اضافه شد"]
            if skipped_duplicates:
                message_parts.append(
                    f"{skipped_duplicates} تکراری نادیده گرفته شد"
                )
            if error_rows:
                message_parts.append(f"{len(error_rows)} ردیف خطا داشت")

            return {
                "success": len(error_rows) == 0,
                "mode": "append",
                "total": total,
                "success_count": success_count,
                "error_count": len(error_rows),
                "error_rows": error_rows,
                "message": "، ".join(message_parts)
            }

        except Exception as error:
            connection.rollback()
            return {
                "success": False, "mode": "append",
                "total": total, "success_count": 0,
                "error_count": total, "error_rows": error_rows,
                "message": f"خطا در ایمپورت: {error}"
            }
        finally:
            connection.close()

    @staticmethod
    def _import_replace(subgroups, total, skipped_rows):
        """حذف کامل و جایگزینی زیرگروه‌ها"""
        connection = get_connection()
        success_count = 0
        error_rows = list(skipped_rows)

        try:
            # ★ چک وابستگی اسناد
            docs_count = connection.execute("""
                SELECT COUNT(*) AS cnt FROM documents
                WHERE subgroup_id IS NOT NULL
            """).fetchone()["cnt"]

            if docs_count > 0:
                return {
                    "success": False, "mode": "replace",
                    "total": total, "success_count": 0,
                    "error_count": 0, "error_rows": [],
                    "message": (
                        f"امکان جایگزینی کامل وجود ندارد. "
                        f"{docs_count} سند به زیرگروه‌های موجود وابسته است."
                    )
                }

            connection.execute("BEGIN")

            # ★ حذف ارتباطات و زیرگروه‌ها
            connection.execute("DELETE FROM subgroup_departments")
            connection.execute("DELETE FROM group_subgroups")
            connection.execute("DELETE FROM document_subgroups")

            for idx, sg in enumerate(subgroups):
                try:
                    cursor = connection.execute("""
                        INSERT INTO document_subgroups
                        (title, code, color, days_review,
                         description, sort_order, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        sg["title"],
                        sg["code"],
                        sg["color"],
                        sg["days_review"],
                        sg["description"],
                        sg["sort_order"],
                        sg["is_active"],
                    ))
                    subgroup_id = cursor.lastrowid

                    DocumentSubgroupExcelService._insert_relations(
                        connection, subgroup_id, sg
                    )

                    success_count += 1
                except Exception:
                    error_rows.append(idx + 2)

            connection.commit()

            return {
                "success": len(error_rows) == 0,
                "mode": "replace",
                "total": total,
                "success_count": success_count,
                "error_count": len(error_rows),
                "error_rows": error_rows,
                "message": (
                    f"داده‌های قبلی حذف و "
                    f"{success_count} زیرگروه جدید ایجاد شد"
                )
            }

        except Exception as error:
            connection.rollback()
            return {
                "success": False, "mode": "replace",
                "total": total, "success_count": 0,
                "error_count": total, "error_rows": error_rows,
                "message": f"خطا در جایگزینی: {error}"
            }
        finally:
            connection.close()