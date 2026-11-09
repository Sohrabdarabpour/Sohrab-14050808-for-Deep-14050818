import io
import pandas as pd
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from database.connection import get_connection


class DocumentGroupExcelService:
    """سرویس خروجی و ورودی اکسل گروه‌های سند (ساختار M:N)"""

    # ============================================================
    # ★ ستون‌های خروجی
    # ============================================================
    EXPORT_COLUMNS = [
        ("id", "شناسه"),
        ("title", "عنوان گروه"),
        ("code", "کد گروه"),
        ("color", "رنگ"),
        ("description", "توضیحات"),
        ("subgroups_titles", "زیرگروه‌ها"),          # ★ جدید (M:N)
        ("subgroups_count", "تعداد زیرگروه"),
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
        2: 35,   # عنوان گروه
        3: 15,   # کد گروه
        4: 15,   # رنگ
        5: 40,   # توضیحات
        6: 60,   # زیرگروه‌ها ← جدید
        7: 15,   # تعداد زیرگروه
        8: 15,   # تعداد اسناد
        9: 15,   # ترتیب نمایش
        10: 12,  # وضعیت
        11: 22,  # تاریخ ایجاد
    }

    # ============================================================
    # ★ نگاشت ستون‌های ایمپورت
    # ============================================================
    IMPORT_COLUMN_MAPPING = {
        "عنوان گروه": "title",
        "عنوان": "title",
        "نام گروه": "title",
        "کد گروه": "code",
        "کد": "code",
        "رنگ": "color",
        "توضیحات": "description",
        "توضیح": "description",
        "ترتیب نمایش": "sort_order",
        "ترتیب": "sort_order",
        "وضعیت": "is_active",
        "فعال": "is_active",
        # ★ زیرگروه‌ها (M:N) — با کاما جدا میشن
        "زیرگروه‌ها": "subgroups",
        "زیرگروه": "subgroups",
        "زیرگروه ها": "subgroups",
    }

    # ============================================================
    # ★ دریافت داده‌ها برای خروجی
    # ============================================================
    @staticmethod
    def get_data():
        """دریافت لیست گروه‌ها همراه با زیرگروه‌ها و تعداد اسناد"""
        connection = get_connection()
        try:
            rows = connection.execute("""
                SELECT
                    g.id,
                    g.title,
                    g.code,
                    g.color,
                    g.description,
                    g.sort_order,
                    g.is_active,
                    g.created_at,
                    (
                        SELECT COUNT(*)
                        FROM group_subgroups gs
                        WHERE gs.group_id = g.id
                    ) AS subgroups_count,
                    (
                        SELECT COUNT(*)
                        FROM documents d
                        WHERE d.group_id = g.id
                    ) AS documents_count
                FROM document_groups g
                ORDER BY g.sort_order ASC, g.id ASC
            """).fetchall()

            result = []
            for row in rows:
                item = dict(row)

                # ★ لیست زیرگروه‌های مرتبط
                subgroups = connection.execute("""
                    SELECT sg.title
                    FROM document_subgroups sg
                    INNER JOIN group_subgroups gs
                        ON gs.subgroup_id = sg.id
                    WHERE gs.group_id = ?
                    ORDER BY gs.sort_order ASC, sg.title ASC
                """, (item["id"],)).fetchall()

                item["subgroups_titles"] = "، ".join(
                    [s["title"] for s in subgroups]
                ) if subgroups else "—"

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
        worksheet.title = "گروه‌های سند"

        # استایل‌ها
        header_fill = PatternFill(fill_type="solid", fgColor="3D8499")
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

        total_columns = len(DocumentGroupExcelService.EXPORT_COLUMNS)

        # هدر
        for column_index, (_, persian_name) in enumerate(
            DocumentGroupExcelService.EXPORT_COLUMNS, start=1
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
                DocumentGroupExcelService.EXPORT_COLUMNS, start=1
            ):
                value = item.get(field)
                cell = worksheet.cell(
                    row=row_index, column=column_index, value=value
                )
                cell.font = body_font
                cell.border = thin_border

                if field in {
                    "id", "subgroups_count", "documents_count",
                    "sort_order", "is_active_label", "created_at"
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

        # تنظیمات
        worksheet.row_dimensions[1].height = 32
        for row_index in range(2, len(data) + 2):
            worksheet.row_dimensions[row_index].height = 22

        for column_index, width in (
            DocumentGroupExcelService.EXPORT_WIDTHS.items()
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
    def export_groups():
        """خروجی اکسل گروه‌ها"""
        data = DocumentGroupExcelService.get_data()
        workbook = DocumentGroupExcelService._create_workbook(data)
        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)
        return output

    @staticmethod
    def build_export_filename():
        """ساخت نام فایل خروجی با تاریخ شمسی"""
        try:
            import jdatetime
            date_str = jdatetime.date.today().strftime("%Y%m%d")
        except Exception:
            date_str = datetime.now().strftime("%Y%m%d")
        return f"document_groups_{date_str}.xlsx"

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
            mapped = DocumentGroupExcelService.IMPORT_COLUMN_MAPPING.get(
                column_name
            )
            if mapped:
                mapping[column] = mapped

        dataframe = dataframe.rename(columns=mapping)

        if "title" not in dataframe.columns:
            return None, (
                "ستون «عنوان گروه» در فایل پیدا نشد. "
                "لطفاً از قالب استاندارد استفاده کنید."
            )

        return dataframe, None

    @staticmethod
    def _prepare_import_row(row):
        """پردازش یک ردیف برای ایمپورت"""
        data = {}

        title = row.get("title")
        if pd.isna(title) or not str(title).strip():
            return None
        data["title"] = str(title).strip()

        code = row.get("code")
        if not pd.isna(code) and str(code).strip():
            data["code"] = str(code).strip()
        else:
            data["code"] = None

        color = row.get("color")
        if not pd.isna(color) and str(color).strip():
            color_str = str(color).strip()
            if not color_str.startswith("#"):
                color_str = f"#{color_str}"
            data["color"] = color_str
        else:
            data["color"] = "#3D8499"

        description = row.get("description")
        if not pd.isna(description) and str(description).strip():
            data["description"] = str(description).strip()
        else:
            data["description"] = None

        sort_order = row.get("sort_order")
        if not pd.isna(sort_order):
            try:
                data["sort_order"] = int(float(sort_order))
            except (ValueError, TypeError):
                data["sort_order"] = 0
        else:
            data["sort_order"] = 0

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

        # ★ زیرگروه‌ها (با کاما یا نقطه‌ویرگول جدا میشن)
        subgroups_raw = row.get("subgroups")
        if not pd.isna(subgroups_raw) and str(subgroups_raw).strip():
            # پشتیبانی از کاما فارسی «،» و انگلیسی «,» و «;»
            text = str(subgroups_raw).strip()
            for sep in ["؛", ";", "،"]:
                text = text.replace(sep, ",")
            subgroups_list = [
                s.strip() for s in text.split(",") if s.strip()
            ]
            data["subgroup_titles"] = subgroups_list
        else:
            data["subgroup_titles"] = []

        return data

    @staticmethod
    def import_groups(file_path, mode="append"):
        """ایمپورت گروه‌ها از فایل اکسل"""
        if mode not in ("append", "replace"):
            return {
                "success": False, "mode": mode, "total": 0,
                "success_count": 0, "error_count": 0,
                "error_rows": [], "message": "حالت ایمپورت نامعتبر است"
            }

        dataframe, error = DocumentGroupExcelService.read_import_file(
            file_path
        )
        if error:
            return {
                "success": False, "mode": mode, "total": 0,
                "success_count": 0, "error_count": 0,
                "error_rows": [], "message": error
            }

        total = len(dataframe)
        groups = []
        skipped_rows = []

        for index, row in dataframe.iterrows():
            data = DocumentGroupExcelService._prepare_import_row(row)
            if data:
                groups.append(data)
            else:
                skipped_rows.append(index + 2)

        if not groups:
            return {
                "success": False, "mode": mode, "total": total,
                "success_count": 0, "error_count": 0,
                "error_rows": skipped_rows,
                "message": "فایل فاقد اطلاعات قابل ورود است"
            }

        if mode == "append":
            return DocumentGroupExcelService._import_append(
                groups, total, skipped_rows
            )
        return DocumentGroupExcelService._import_replace(
            groups, total, skipped_rows
        )

    @staticmethod
    def _resolve_subgroup_ids(connection, subgroup_titles):
        """تبدیل لیست عنوان زیرگروه به لیست شناسه"""
        if not subgroup_titles:
            return []

        placeholders = ",".join("?" * len(subgroup_titles))
        rows = connection.execute(f"""
            SELECT id, title
            FROM document_subgroups
            WHERE title IN ({placeholders})
        """, tuple(subgroup_titles)).fetchall()

        # ★ نگاشت title → id
        title_to_id = {r["title"]: r["id"] for r in rows}

        # ★ حفظ ترتیب ورودی
        result = []
        for title in subgroup_titles:
            if title in title_to_id:
                result.append(title_to_id[title])
        return result

    @staticmethod
    def _import_append(groups, total, skipped_rows):
        """افزودن گروه‌ها به داده‌های موجود"""
        connection = get_connection()
        success_count = 0
        skipped_duplicates = 0
        error_rows = list(skipped_rows)

        try:
            for idx, group in enumerate(groups):
                row_number = idx + 2

                existing = connection.execute(
                    "SELECT id FROM document_groups WHERE title = ?",
                    (group["title"],)
                ).fetchone()

                if existing:
                    skipped_duplicates += 1
                    continue

                if group["code"]:
                    existing_code = connection.execute(
                        "SELECT id FROM document_groups WHERE code = ?",
                        (group["code"],)
                    ).fetchone()
                    if existing_code:
                        group["code"] = None

                try:
                    cursor = connection.execute("""
                        INSERT INTO document_groups
                        (title, code, color, description,
                         sort_order, is_active)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        group["title"],
                        group["code"],
                        group["color"],
                        group["description"],
                        group["sort_order"],
                        group["is_active"],
                    ))
                    group_id = cursor.lastrowid

                    # ★ اتصال زیرگروه‌ها (M:N)
                    subgroup_ids = DocumentGroupExcelService._resolve_subgroup_ids(
                        connection, group.get("subgroup_titles", [])
                    )
                    for sg_id in subgroup_ids:
                        connection.execute("""
                            INSERT OR IGNORE INTO group_subgroups
                            (group_id, subgroup_id, sort_order, is_active)
                            VALUES (?, ?, 0, 1)
                        """, (group_id, sg_id))

                    success_count += 1
                except Exception:
                    error_rows.append(row_number)

            connection.commit()

            message_parts = [f"{success_count} گروه اضافه شد"]
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
                "success": False, "mode": "append", "total": total,
                "success_count": 0, "error_count": total,
                "error_rows": error_rows,
                "message": f"خطا در ایمپورت: {error}"
            }
        finally:
            connection.close()

    @staticmethod
    def _import_replace(groups, total, skipped_rows):
        """حذف کامل و جایگزینی گروه‌ها"""
        connection = get_connection()
        success_count = 0
        error_rows = list(skipped_rows)

        try:
            # ★ چک وابستگی اسناد
            docs_count = connection.execute(
                "SELECT COUNT(*) AS cnt FROM documents "
                "WHERE group_id IS NOT NULL"
            ).fetchone()["cnt"]

            if docs_count > 0:
                return {
                    "success": False, "mode": "replace",
                    "total": total, "success_count": 0,
                    "error_count": 0, "error_rows": [],
                    "message": (
                        f"امکان جایگزینی کامل وجود ندارد. "
                        f"{docs_count} سند به گروه‌های موجود وابسته است."
                    )
                }

            connection.execute("BEGIN")

            # ★ حذف ارتباطات و گروه‌ها
            connection.execute("DELETE FROM group_subgroups")
            connection.execute("DELETE FROM document_groups")

            for idx, group in enumerate(groups):
                try:
                    cursor = connection.execute("""
                        INSERT INTO document_groups
                        (title, code, color, description,
                         sort_order, is_active)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        group["title"],
                        group["code"],
                        group["color"],
                        group["description"],
                        group["sort_order"],
                        group["is_active"],
                    ))
                    group_id = cursor.lastrowid

                    # ★ اتصال زیرگروه‌ها
                    subgroup_ids = DocumentGroupExcelService._resolve_subgroup_ids(
                        connection, group.get("subgroup_titles", [])
                    )
                    for sg_id in subgroup_ids:
                        connection.execute("""
                            INSERT OR IGNORE INTO group_subgroups
                            (group_id, subgroup_id, sort_order, is_active)
                            VALUES (?, ?, 0, 1)
                        """, (group_id, sg_id))

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
                    f"داده‌های قبلی حذف و {success_count} گروه جدید ایجاد شد"
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