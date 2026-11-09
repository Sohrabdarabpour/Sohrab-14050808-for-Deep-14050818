import io
from datetime import datetime

import jdatetime
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from config import Config
from helpers.date_helper import DateHelper
from database.connection import get_connection
from database.users import (
    get_all_users,
    get_user_by_id,
)
from services.users.user_service import UserService


class UserExcelService:

    # ============================================================
    # ★ ستون‌های خروجی کاربران — تمام ستون‌های دیتابیس ★
    # ============================================================
    EXPORT_COLUMNS = [
        ("id",                "شناسه"),
        ("row",               "ردیف"),
        ("username",          "نام کاربری"),
        ("full_name",         "نام و نام خانوادگی"),
        ("role_label",        "نقش"),
        ("email",             "ایمیل"),
        ("phone",             "تلفن"),
        ("national_code",     "کد ملی"),
        ("position",          "سمت"),
        ("department_id",     "شناسه واحد"),        # ★ جدید
        ("department_name",   "نام واحد"),          # ★ جدید (اختیاری)
        ("avatar",            "تصویر"),             # ★ جدید
        ("is_active_label",   "وضعیت حساب"),
        ("online_label",      "وضعیت آنلاین"),
        ("is_online",         "کد آنلاین"),         # ★ جدید (0/1)
        ("last_login_jalali", "آخرین ورود"),
        ("last_seen_jalali",  "آخرین فعالیت"),
        ("created_at_jalali", "تاریخ ایجاد"),
        ("updated_at_jalali", "آخرین بروزرسانی"),
    ]

    EXPORT_WIDTHS = {
        1: 8,     # شناسه
        2: 6,     # ردیف
        3: 16,    # نام کاربری
        4: 24,    # نام و نام خانوادگی
        5: 14,    # نقش
        6: 24,    # ایمیل
        7: 16,    # تلفن
        8: 14,    # کد ملی
        9: 18,    # سمت
        10: 12,   # شناسه واحد
        11: 20,   # نام واحد
        12: 20,   # تصویر
        13: 12,   # وضعیت حساب
        14: 14,   # وضعیت آنلاین
        15: 10,   # کد آنلاین
        16: 22,   # آخرین ورود
        17: 22,   # آخرین فعالیت
        18: 22,   # تاریخ ایجاد
        19: 22,   # آخرین بروزرسانی
    }

    # ★ ستون‌های ورودی (Import)
    IMPORT_COLUMNS = {
        "شناسه": "id",
        "نام کاربری": "username",
        "نام و نام خانوادگی": "full_name",
        "نقش": "role",
        "ایمیل": "email",
        "تلفن": "phone",
        "کد ملی": "national_code",
        "سمت": "position",
        "شناسه واحد": "department_id",   # ★ جدید
    }

    ROLE_MAP = {
        "admin": "مدیر سیستم",
        "manager": "مدیر",
        "supervisor": "سرپرست",
        "expert": "کارشناس",
    }

    ROLE_MAP_REVERSE = {v: k for k, v in ROLE_MAP.items()}

    # ============================================================
    # ★★★ خروجی اکسل ★★★
    # ============================================================
    @staticmethod
    def export_users(file_path=None):
        users_list = [dict(u) for u in get_all_users()]
        workbook = UserExcelService._create_users_workbook(users_list)

        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)

        if file_path:
            with open(file_path, "wb") as f:
                f.write(output.getvalue())
            return file_path

        return output

    # ============================================================
    # ★ دریافت نام واحد (اختیاری — اگر جدول departments دارید)
    # ============================================================
    @staticmethod
    def _get_department_name(department_id):
        """دریافت نام واحد از جدول departments"""
        if not department_id:
            return ""
        try:
            with get_connection() as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "SELECT name FROM departments WHERE id = ?",
                    (department_id,)
                )
                row = cursor.fetchone()
                return row["name"] if row else ""
        except Exception:
            return ""

    # ============================================================
    # ★ ساخت workbook کاربران ★
    # ============================================================
    @staticmethod
    def _create_users_workbook(users_list):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "کاربران"

        # ★ استایل‌ها
        header_fill = PatternFill(fill_type="solid", fgColor="3D8499")
        header_font = Font(name="Segoe UI", size=9, bold=True, color="FFFFFF")
        body_font = Font(name="Segoe UI", size=9, bold=False, color="000000")

        header_alignment = Alignment(
            horizontal="center",
            vertical="center",
            readingOrder=2,
            wrap_text=True,
        )
        body_alignment_center = Alignment(
            horizontal="center",
            vertical="center",
            readingOrder=2,
        )
        body_alignment_right = Alignment(
            horizontal="right",
            vertical="center",
            readingOrder=2,
            wrap_text=True,
        )

        thin_border = Border(
            left=Side(style="thin", color="D9E2E5"),
            right=Side(style="thin", color="D9E2E5"),
            top=Side(style="thin", color="D9E2E5"),
            bottom=Side(style="thin", color="D9E2E5"),
        )

        # ★ رنگ‌ها
        online_font = Font(name="Segoe UI", size=9, bold=True, color="276749")
        offline_font = Font(name="Segoe UI", size=9, bold=True, color="C05621")
        active_font = Font(name="Segoe UI", size=9, bold=True, color="276749")
        inactive_font = Font(name="Segoe UI", size=9, bold=True, color="C05621")
        id_font = Font(name="Segoe UI", size=9, bold=True, color="3D8499")
        dept_font = Font(name="Segoe UI", size=9, bold=True, color="2b6cb0")

        # ★ هدرها
        total_columns = len(UserExcelService.EXPORT_COLUMNS)
        for column_index, (_, persian_name) in enumerate(
            UserExcelService.EXPORT_COLUMNS, start=1
        ):
            cell = worksheet.cell(
                row=1, column=column_index, value=persian_name
            )
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border

        # ★ بدنه
        for index, user in enumerate(users_list, start=1):
            is_online = UserExcelService._safe_is_online(user["id"])

            last_login_jalali = DateHelper.format_jalali_datetime(
                user.get("last_login")
            ) or "—"
            last_seen_jalali = DateHelper.format_jalali_datetime(
                user.get("last_seen")
            ) or "—"
            created_at_jalali = DateHelper.format_jalali_datetime(
                user.get("created_at")
            ) or "—"
            updated_at_jalali = DateHelper.format_jalali_datetime(
                user.get("updated_at")
            ) or "—"

            # ★ نام واحد (اختیاری)
            department_id = user.get("department_id")
            department_name = UserExcelService._get_department_name(department_id)

            row_data = {
                "id": user.get("id"),
                "row": index,
                "username": user.get("username") or "",
                "full_name": user.get("full_name") or "",
                "role_label": UserExcelService.ROLE_MAP.get(
                    user.get("role"), user.get("role") or ""
                ),
                "email": user.get("email") or "",
                "phone": user.get("phone") or "",
                "national_code": user.get("national_code") or "",
                "position": user.get("position") or "",
                "department_id": department_id if department_id else "—",
                "department_name": department_name or "—",
                "avatar": user.get("avatar") or "—",
                "is_active_label": (
                    "فعال" if user.get("is_active") == 1 else "غیرفعال"
                ),
                "online_label": "آنلاین" if is_online else "آفلاین",
                "is_online": is_online if is_online is not None else 0,
                "last_login_jalali": last_login_jalali,
                "last_seen_jalali": last_seen_jalali,
                "created_at_jalali": created_at_jalali,
                "updated_at_jalali": updated_at_jalali,
            }

            current_row = index + 1
            for column_index, (field, _) in enumerate(
                UserExcelService.EXPORT_COLUMNS, start=1
            ):
                cell = worksheet.cell(
                    row=current_row,
                    column=column_index,
                    value=row_data[field],
                )
                cell.font = body_font
                cell.border = thin_border

                # ★ تراز
                if field in (
                    "id",
                    "row",
                    "role_label",
                    "is_active_label",
                    "online_label",
                    "national_code",
                    "department_id",
                    "is_online",
                ):
                    cell.alignment = body_alignment_center
                else:
                    cell.alignment = body_alignment_right

                # ★ رنگ‌بندی
                if field == "id":
                    cell.font = id_font
                elif field == "is_active_label":
                    cell.font = (
                        active_font
                        if user.get("is_active") == 1
                        else inactive_font
                    )
                elif field == "online_label":
                    cell.font = online_font if is_online else offline_font
                elif field in ("department_id", "department_name"):
                    cell.font = dept_font

        # ★ ارتفاع هدر
        worksheet.row_dimensions[1].height = 32

        # ★ عرض ستون‌ها
        for column_index, width in UserExcelService.EXPORT_WIDTHS.items():
            worksheet.column_dimensions[
                get_column_letter(column_index)
            ].width = width

        # ★ Freeze + Filter + RTL
        last_column = get_column_letter(total_columns)
        last_row = len(users_list) + 1
        worksheet.freeze_panes = "C2"
        worksheet.auto_filter.ref = f"A1:{last_column}{last_row}"
        worksheet.sheet_view.rightToLeft = True

        # ★ تنظیمات چاپ
        worksheet.sheet_properties.pageSetUpPr.fitToPage = True
        worksheet.page_setup.orientation = "landscape"
        worksheet.page_setup.fitToWidth = 1
        worksheet.page_setup.fitToHeight = 0
        worksheet.print_title_rows = "1:1"

        return workbook

    # ============================================================
    # ★ نام فایل خروجی ★
    # ============================================================
    @staticmethod
    def build_export_filename():
        now = datetime.now()
        jalali_now = jdatetime.datetime.fromgregorian(datetime=now)
        return f"users_{jalali_now.strftime('%Y%m%d_%H%M%S')}.xlsx"

    # ============================================================
    # ★ قالب خالی برای ورود اطلاعات ★
    # ============================================================
    TEMPLATE_ROWS = 100

    @staticmethod
    def export_import_template():
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "کاربران"

        header_fill = PatternFill(fill_type="solid", fgColor="3D8499")
        header_font = Font(name="Segoe UI", size=9, bold=True, color="FFFFFF")
        body_font = Font(name="Segoe UI", size=9, bold=False, color="000000")

        header_alignment = Alignment(
            horizontal="center",
            vertical="center",
            readingOrder=2,
            wrap_text=True,
        )
        body_alignment = Alignment(
            horizontal="right",
            vertical="center",
            readingOrder=2,
            wrap_text=True,
        )

        thin_border = Border(
            left=Side(style="thin", color="D9E2E5"),
            right=Side(style="thin", color="D9E2E5"),
            top=Side(style="thin", color="D9E2E5"),
            bottom=Side(style="thin", color="D9E2E5"),
        )

        columns = list(UserExcelService.IMPORT_COLUMNS.keys())
        total_columns = len(columns)

        for column_index, persian_name in enumerate(columns, start=1):
            cell = worksheet.cell(
                row=1, column=column_index, value=persian_name
            )
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border

        for row in worksheet.iter_rows(
            min_row=2,
            max_row=UserExcelService.TEMPLATE_ROWS + 1,
            min_col=1,
            max_col=total_columns,
        ):
            for cell in row:
                cell.font = body_font
                cell.alignment = body_alignment
                cell.border = thin_border

        worksheet.row_dimensions[1].height = 32
        for row_index in range(2, UserExcelService.TEMPLATE_ROWS + 2):
            worksheet.row_dimensions[row_index].height = 22

        # ★ عرض ستون‌ها (شامل شناسه واحد)
        import_widths = {
            1: 8,    # شناسه
            2: 18,   # نام کاربری
            3: 28,   # نام و نام خانوادگی
            4: 16,   # نقش
            5: 26,   # ایمیل
            6: 16,   # تلفن
            7: 14,   # کد ملی
            8: 22,   # سمت
            9: 14,   # شناسه واحد  ★ جدید
        }
        for column_index, width in import_widths.items():
            worksheet.column_dimensions[
                get_column_letter(column_index)
            ].width = width

        last_column = get_column_letter(total_columns)
        last_row = UserExcelService.TEMPLATE_ROWS + 1
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = f"A1:{last_column}{last_row}"
        worksheet.sheet_view.rightToLeft = True

        worksheet.sheet_properties.pageSetUpPr.fitToPage = True
        worksheet.page_setup.orientation = "landscape"
        worksheet.page_setup.fitToWidth = 1
        worksheet.page_setup.fitToHeight = 0
        worksheet.print_title_rows = "1:1"

        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)
        return output

    # ============================================================
    # ★ ورود از اکسل ★
    # ============================================================
    # ============================================================
    # ★ ورود از اکسل ★
    # ============================================================
    @staticmethod
    def import_users(file_path):
        """
        ورود کاربران از فایل Excel.
        
        منطق:
        - اگر «شناسه» پر باشد → بروزرسانی کاربر موجود
        - اگر «شناسه» خالی باشد → ایجاد کاربر جدید
        - مقادیر «—» یا خالی → نادیده گرفته می‌شوند (در حالت update)
        """
        try:
            dataframe = pd.read_excel(file_path)
        except Exception as error:
            return UserExcelService._error_result(
                f"خطا در خواندن فایل Excel: {error}"
            )

        dataframe = UserExcelService._rename_import_columns(dataframe)
        total = len(dataframe)

        success_count = 0
        updated_count = 0
        created_count = 0
        skipped_count = 0
        error_rows = []
        errors = []

        for index, row in dataframe.iterrows():
            excel_row = index + 2  # ★ شماره ردیف واقعی در اکسل
            data = UserExcelService._prepare_user_row(row)

            # ★ رد کردن ردیف‌های کاملاً خالی
            if not any(data.values()):
                skipped_count += 1
                continue

            # ★ اعتبارسنجی
            if not data.get("username") or not data.get("full_name"):
                error_rows.append(excel_row)
                errors.append(
                    f"ردیف {excel_row}: نام کاربری و نام کامل الزامی است"
                )
                continue

            # ★ تبدیل نقش فارسی → انگلیسی
            role = UserExcelService.ROLE_MAP_REVERSE.get(
                data.get("role"), data.get("role")
            )
            if role not in UserExcelService.ROLE_MAP:
                role = "expert"

            # ★ تبدیل department_id به عدد
            department_id = data.get("department_id")
            if department_id is not None:
                try:
                    department_id = int(department_id)
                except (TypeError, ValueError):
                    department_id = None

            # ★ تبدیل id به عدد
            user_id = data.get("id")
            if user_id is not None:
                try:
                    user_id = int(user_id)
                except (TypeError, ValueError):
                    user_id = None

            # ============================================================
            # ★ حالت ۱: شناسه پر است → بروزرسانی
            # ============================================================
            if user_id:
                try:
                    success = UserService.update(
                        user_id=user_id,
                        username=data.get("username"),
                        full_name=data.get("full_name"),
                        role=role,
                        password=None,
                        email=data.get("email"),
                        phone=data.get("phone"),
                        national_code=data.get("national_code"),
                        position=data.get("position"),
                        department_id=department_id,
                    )
                except Exception as e:
                    success = False
                    errors.append(
                        f"ردیف {excel_row}: خطای غیرمنتظره — {e}"
                    )

                if success:
                    updated_count += 1
                    success_count += 1
                else:
                    error_rows.append(excel_row)
                    if not any(
                        f"ردیف {excel_row}" in e for e in errors
                    ):
                        errors.append(
                            f"ردیف {excel_row}: بروزرسانی کاربر با شناسه "
                            f"{user_id} انجام نشد (کاربر یافت نشد یا نام کاربری تکراری است)"
                        )
                continue

            # ============================================================
            # ★ حالت ۲: شناسه خالی → ایجاد کاربر جدید
            # ============================================================
            try:
                success = UserService.create(
                    username=data["username"],
                    password="123456",
                    full_name=data["full_name"],
                    role=role,
                    email=data.get("email"),
                    phone=data.get("phone"),
                    national_code=data.get("national_code"),
                    position=data.get("position"),
                    department_id=department_id,
                )
            except Exception as e:
                success = False
                errors.append(
                    f"ردیف {excel_row}: خطای غیرمنتظره — {e}"
                )

            if success:
                created_count += 1
                success_count += 1
            else:
                error_rows.append(excel_row)
                errors.append(
                    f"ردیف {excel_row}: نام کاربری «{data['username']}» تکراری است"
                )

        error_count = len(error_rows)

        # ★ پیام نهایی
        parts = []
        if created_count:
            parts.append(f"{created_count} کاربر جدید ایجاد شد")
        if updated_count:
            parts.append(f"{updated_count} کاربر بروزرسانی شد")
        if error_count:
            parts.append(f"{error_count} ردیف خطا داشت")
        if skipped_count:
            parts.append(f"{skipped_count} ردیف خالی رد شد")

        message = "، ".join(parts) if parts else "هیچ داده‌ای پردازش نشد"

        return {
            "success": error_count == 0 and success_count > 0,
            "total": total,
            "success_count": success_count,
            "updated_count": updated_count,
            "created_count": created_count,
            "skipped_count": skipped_count,
            "error_count": error_count,
            "error_rows": error_rows,
            "errors": errors,
            "message": message,
        }
        
        
    @staticmethod
    def _rename_import_columns(dataframe):
        mapping = {}
        for column in dataframe.columns:
            column_name = str(column).strip()
            mapping[column] = UserExcelService.IMPORT_COLUMNS.get(
                column_name, column_name
            )
        return dataframe.rename(columns=mapping)

    @staticmethod
    def _prepare_user_row(row):
        data = {}
        for field, value in row.items():
            if field not in UserExcelService.IMPORT_COLUMNS.values():
                continue
            data[field] = UserExcelService._clean_value(value)
        return data

    @staticmethod
    def _clean_value(value):
        """پاکسازی مقدار — «—»، «-» و خالی → None"""
        if pd.isna(value):
            return None
        if isinstance(value, str):
            value = value.strip()
            # ★ مقادیر نمادین که به معنی خالی هستند
            if value in ("", "—", "-", "–", "N/A", "n/a"):
                return None
            return value
        return value
    
    @staticmethod
    def _safe_is_online(user_id):
        try:
            return UserService.is_online(user_id)
        except Exception:
            return False

    @staticmethod
    def _error_result(message):
        return {
            "success": False,
            "total": 0,
            "success_count": 0,
            "updated_count": 0,
            "created_count": 0,
            "error_count": 0,
            "error_rows": [],
            "errors": [message],
            "message": message,
        }