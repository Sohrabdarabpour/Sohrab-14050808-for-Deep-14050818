"""
سرویس مدیریت پیمانکاران
تمام منطق تجاری مربوط به پیمانکاران اینجا قرار می‌گیرد
"""
from database.init_db import (
    create_contractor,
    get_contractor,
    get_contractor_by_code,
    get_all_contractors,
    update_contractor,
    delete_contractor,
    search_contractors,
)
from .contractor_excel_service import (
    export_contractors_to_excel,
    import_contractors_from_excel,
    generate_import_template,
)


class ContractorService:
    """سرویس مدیریت پیمانکاران"""

    # ============================================================
    # ★ خواندن (Read)
    # ============================================================

    @staticmethod
    def list_contractors(only_active=False):
        """
        لیست همه پیمانکاران

        Args:
            only_active (bool): فقط پیمانکاران فعال

        Returns:
            list[dict]: لیست پیمانکاران
        """
        return get_all_contractors(only_active=only_active)

    # ------------------------------------------------------------
    @staticmethod
    def get(contractor_id):
        """
        دریافت پیمانکار با ID

        Args:
            contractor_id (int): شناسه پیمانکار

        Returns:
            dict | None
        """
        if not contractor_id:
            return None
        return get_contractor(contractor_id)

    # ------------------------------------------------------------
    @staticmethod
    def find_by_code(code):
        """
        دریافت پیمانکار با کد

        Args:
            code (str): کد پیمانکار

        Returns:
            dict | None
        """
        if not code:
            return None
        return get_contractor_by_code(code)

    # ------------------------------------------------------------
    @staticmethod
    def search(query, only_active=False):
        """
        جستجوی پیمانکاران

        Args:
            query (str): عبارت جستجو
            only_active (bool): فقط فعال‌ها

        Returns:
            list[dict]
        """
        query = (query or "").strip()
        if not query:
            return ContractorService.list_contractors(
                only_active=only_active
            )
        return search_contractors(query, only_active=only_active)

    # ============================================================
    # ★ ایجاد (Create)
    # ============================================================

    @staticmethod
    def create(data):
        """
        ایجاد پیمانکار جدید با اعتبارسنجی کامل

        Args:
            data (dict): داده‌های پیمانکار

        Returns:
            dict: {"success": bool, "id": int, "errors": dict}
        """
        # ---- ۱. اعتبارسنجی ----
        errors = ContractorService.validate(data)
        if errors:
            return {"success": False, "errors": errors}

        # ---- ۲. چک تکراری بودن کد ----
        code = (data.get("code") or "").strip()
        if code:
            existing = get_contractor_by_code(code)
            if existing:
                return {
                    "success": False,
                    "errors": {
                        "code": "این کد قبلاً برای پیمانکار دیگری ثبت شده است"
                    }
                }

        # ---- ۳. تمیزکاری داده‌ها ----
        clean_data = ContractorService._clean_data(data)

        # ---- ۴. ذخیره‌سازی ----
        new_id = create_contractor(**clean_data)
        if not new_id:
            return {
                "success": False,
                "errors": {"general": "خطا در ذخیره‌سازی پیمانکار"}
            }

        return {"success": True, "id": new_id}

    # ============================================================
    # ★ به‌روزرسانی (Update)
    # ============================================================

    @staticmethod
    def update(contractor_id, data):
        """
        به‌روزرسانی پیمانکار

        Args:
            contractor_id (int): شناسه پیمانکار
            data (dict): داده‌های جدید

        Returns:
            dict: {"success": bool, "errors": dict}
        """
        # ---- ۱. چک وجود پیمانکار ----
        contractor = get_contractor(contractor_id)
        if not contractor:
            return {
                "success": False,
                "errors": {"general": "پیمانکار یافت نشد"}
            }

        # ---- ۲. اعتبارسنجی ----
        errors = ContractorService.validate(data)
        if errors:
            return {"success": False, "errors": errors}

        # ---- ۳. چک تکراری بودن کد ----
        code = (data.get("code") or "").strip()
        if code:
            existing = get_contractor_by_code(code)
            if existing and existing["id"] != contractor_id:
                return {
                    "success": False,
                    "errors": {
                        "code": "این کد قبلاً برای پیمانکار دیگری ثبت شده است"
                    }
                }

        # ---- ۴. تمیزکاری داده‌ها ----
        clean_data = ContractorService._clean_data(data)

        # ---- ۵. ذخیره‌سازی ----
        ok = update_contractor(contractor_id, **clean_data)
        if not ok:
            return {
                "success": False,
                "errors": {"general": "خطا در به‌روزرسانی پیمانکار"}
            }

        return {"success": True}

    # ============================================================
    # ★ حذف (Delete)
    # ============================================================

    @staticmethod
    def delete(contractor_id):
        """
        حذف پیمانکار

        Args:
            contractor_id (int): شناسه پیمانکار

        Returns:
            dict: {"success": bool, "errors": dict}
        """
        # ---- ۱. چک وجود پیمانکار ----
        contractor = get_contractor(contractor_id)
        if not contractor:
            return {
                "success": False,
                "errors": {"general": "پیمانکار یافت نشد"}
            }

        # ---- ۲. چک استفاده در اسناد (اختیاری) ----
        # اگه خواستی جلوی حذف پیمانکاری که سند داره رو بگیری،
        # کامنت زیر رو باز کن:
        #
        # if ContractorService._has_documents(contractor_id):
        #     return {
        #         "success": False,
        #         "errors": {
        #             "general": "این پیمانکار دارای سند است و قابل حذف نیست"
        #         }
        #     }

        # ---- ۳. حذف ----
        ok = delete_contractor(contractor_id)
        if not ok:
            return {
                "success": False,
                "errors": {"general": "خطا در حذف پیمانکار"}
            }

        return {"success": True}

    # ============================================================
    # ★ تغییر وضعیت (فعال/غیرفعال)
    # ============================================================

    @staticmethod
    def toggle_active(contractor_id):
        """
        تغییر وضعیت فعال/غیرفعال پیمانکار

        Args:
            contractor_id (int): شناسه پیمانکار

        Returns:
            dict: {"success": bool, "is_active": int, "errors": dict}
        """
        contractor = get_contractor(contractor_id)
        if not contractor:
            return {
                "success": False,
                "errors": {"general": "پیمانکار یافت نشد"}
            }

        new_status = 0 if contractor.get("is_active") else 1
        ok = update_contractor(contractor_id, is_active=new_status)

        if not ok:
            return {
                "success": False,
                "errors": {"general": "خطا در تغییر وضعیت"}
            }

        return {"success": True, "is_active": new_status}

    # ============================================================
    # ★ آمار (Statistics)
    # ============================================================

    @staticmethod
    def get_statistics():
        """
        آمار پیمانکاران

        Returns:
            dict: {"total": int, "active": int, "inactive": int}
        """
        all_contractors = get_all_contractors(only_active=False)
        active = sum(1 for c in all_contractors if c.get("is_active"))
        return {
            "total": len(all_contractors),
            "active": active,
            "inactive": len(all_contractors) - active,
        }

    # ============================================================
    # ★ Excel — Export
    # ============================================================

    @staticmethod
    def export_excel(output_path=None):
        """
        خروجی اکسل از پیمانکاران

        Args:
            output_path (str): مسیر ذخیره (اختیاری)

        Returns:
            dict: {"success": bool, "path": str, "errors": dict}
        """
        try:
            path = export_contractors_to_excel(output_path)
            return {"success": True, "path": path}
        except Exception as e:
            return {
                "success": False,
                "errors": {"general": f"خطا در خروجی اکسل: {e}"}
            }

    # ============================================================
    # ★ Excel — Import
    # ============================================================

    @staticmethod
    def import_excel(file_path, update_existing=False):
        """
        ورود پیمانکاران از فایل اکسل

        Args:
            file_path (str): مسیر فایل اکسل
            update_existing (bool): به‌روزرسانی رکوردهای موجود

        Returns:
            dict: {
                "success": bool,
                "inserted": int,
                "updated": int,
                "skipped": int,
                "errors": list[str]
            }
        """
        try:
            result = import_contractors_from_excel(
                file_path, update_existing=update_existing
            )
            return result
        except Exception as e:
            return {
                "success": False,
                "inserted": 0,
                "updated": 0,
                "skipped": 0,
                "errors": [f"خطا در import: {e}"],
            }

    # ============================================================
    # ★ Excel — دانلود قالب
    # ============================================================

    @staticmethod
    def download_template(output_path=None):
        """
        ساخت و دانلود قالب اکسل

        Args:
            output_path (str): مسیر ذخیره (اختیاری)

        Returns:
            dict: {"success": bool, "path": str, "errors": dict}
        """
        try:
            path = generate_import_template(output_path)
            return {"success": True, "path": path}
        except Exception as e:
            return {
                "success": False,
                "errors": {"general": f"خطا در ساخت قالب: {e}"}
            }

    # ============================================================
    # ★ اعتبارسنجی (Validation)
    # ============================================================

    @staticmethod
    def validate(data):
        """
        اعتبارسنجی داده‌های پیمانکار

        Args:
            data (dict): داده‌های ورودی

        Returns:
            dict: دیکشنری خطاها (خالی = بدون خطا)
        """
        errors = {}

        # ---- ۱. نام (اجباری) ----
        name = (data.get("name") or "").strip()
        if not name:
            errors["name"] = "نام پیمانکار الزامی است"
        elif len(name) < 3:
            errors["name"] = "نام پیمانکار باید حداقل ۳ کاراکتر باشد"
        elif len(name) > 200:
            errors["name"] = "نام پیمانکار نباید بیشتر از ۲۰۰ کاراکتر باشد"

        # ---- ۲. کد (اختیاری - یکتا) ----
        code = (data.get("code") or "").strip()
        if code and len(code) > 50:
            errors["code"] = "کد پیمانکار نباید بیشتر از ۵۰ کاراکتر باشد"

        # ---- ۳. کد ملی / شناسه ملی ----
        national_id = (data.get("national_id") or "").strip()
        if national_id:
            if not national_id.isdigit():
                errors["national_id"] = "کد ملی باید فقط شامل اعداد باشد"
            elif len(national_id) not in (10, 11):
                errors["national_id"] = "کد ملی باید ۱۰ یا ۱۱ رقم باشد"

        # ---- ۴. کد اقتصادی ----
        economic_code = (data.get("economic_code") or "").strip()
        if economic_code and not economic_code.isdigit():
            errors["economic_code"] = "کد اقتصادی باید فقط شامل اعداد باشد"

        # ---- ۵. شماره ثبت ----
        registration_number = (
            data.get("registration_number") or ""
        ).strip()
        if registration_number and not registration_number.isdigit():
            errors["registration_number"] = (
                "شماره ثبت باید فقط شامل اعداد باشد"
            )

        # ---- ۶. موبایل ----
        mobile = (data.get("mobile") or "").strip()
        if mobile:
            if not mobile.isdigit():
                errors["mobile"] = "موبایل باید فقط شامل اعداد باشد"
            elif not mobile.startswith("09"):
                errors["mobile"] = "موبایل باید با ۰۹ شروع شود"
            elif len(mobile) != 11:
                errors["mobile"] = "موبایل باید ۱۱ رقم باشد"

        # ---- ۷. تلفن ----
        phone = (data.get("phone") or "").strip()
        if phone:
            clean_phone = phone.replace("-", "").replace(" ", "")
            if not clean_phone.isdigit():
                errors["phone"] = "تلفن باید فقط شامل اعداد باشد"

        # ---- ۸. ایمیل ----
        email = (data.get("email") or "").strip()
        if email:
            if "@" not in email or "." not in email.split("@")[-1]:
                errors["email"] = "ایمیل نامعتبر است"

        # ---- ۹. کد پستی ----
        postal_code = (data.get("postal_code") or "").strip()
        if postal_code:
            if not postal_code.isdigit():
                errors["postal_code"] = (
                    "کد پستی باید فقط شامل اعداد باشد"
                )
            elif len(postal_code) != 10:
                errors["postal_code"] = "کد پستی باید ۱۰ رقم باشد"

        # ---- ۱۰. استان / شهر ----
        province = (data.get("province") or "").strip()
        if province and len(province) > 100:
            errors["province"] = (
                "نام استان نباید بیشتر از ۱۰۰ کاراکتر باشد"
            )

        city = (data.get("city") or "").strip()
        if city and len(city) > 100:
            errors["city"] = "نام شهر نباید بیشتر از ۱۰۰ کاراکتر باشد"

        return errors

    # ============================================================
    # ★ توابع کمکی داخلی
    # ============================================================

    @staticmethod
    def _clean_data(data):
        """
        تمیزکاری داده‌ها قبل از ذخیره‌سازی
        - حذف فاصله‌های اضافی
        - تبدیل رشته خالی به None
        - تبدیل is_active به 0/1
        """
        cleaned = {}

        for key, value in data.items():
            # ---- is_active → 0/1 ----
            if key == "is_active":
                cleaned[key] = 1 if value else 0
                continue

            # ---- sort_order → int ----
            if key == "sort_order":
                try:
                    cleaned[key] = int(value) if value else 0
                except (ValueError, TypeError):
                    cleaned[key] = 0
                continue

            # ---- رشته‌ها → strip + خالی = None ----
            if isinstance(value, str):
                value = value.strip()
                cleaned[key] = value if value else None
            else:
                cleaned[key] = value

        return cleaned

    # ------------------------------------------------------------
    @staticmethod
    def _has_documents(contractor_id):
        """
        چک اینکه آیا پیمانکار در جدول documents استفاده شده یا نه

        Args:
            contractor_id (int): شناسه پیمانکار

        Returns:
            bool
        """
        from database.connection import get_connection
        connection = get_connection()
        try:
            # چک وجود ستون contractor_id در documents
            columns = connection.execute(
                "PRAGMA table_info(documents)"
            ).fetchall()
            column_names = [c["name"] for c in columns]

            if "contractor_id" not in column_names:
                return False

            row = connection.execute(
                "SELECT COUNT(*) AS cnt "
                "FROM documents WHERE contractor_id = ?",
                (contractor_id,)
            ).fetchone()

            return row["cnt"] > 0
        except Exception:
            return False
        finally:
            connection.close()