"""
سرویس مدیریت پروژه‌ها
"""
from database.init_db import (
    create_project,
    get_project,
    get_project_by_code,
    get_all_projects,
    update_project,
    delete_project,
    search_projects,
    get_projects_statistics,
    get_all_contractors,
    get_all_contract_types,
    get_all_areas,
)


class ProjectService:
    """سرویس پروژه‌ها"""

    # ============================================================
    # ★ خواندن
    # ============================================================
    @staticmethod
    def list_projects(only_active=False, contractor_id=None,
                      contract_type_id=None, area_id=None,
                      status=None):
        return get_all_projects(
            only_active=only_active,
            contractor_id=contractor_id,
            contract_type_id=contract_type_id,
            area_id=area_id,
            status=status,
        )

    @staticmethod
    def get(project_id):
        if not project_id:
            return None
        return get_project(project_id)

    @staticmethod
    def find_by_code(code):
        if not code:
            return None
        return get_project_by_code(code)

    @staticmethod
    def search(query, only_active=False):
        query = (query or "").strip()
        if not query:
            return ProjectService.list_projects(only_active=only_active)
        return search_projects(query, only_active=only_active)

    @staticmethod
    def get_statistics():
        return get_projects_statistics()

    # ============================================================
    # ★ داده‌های کمکی برای فرم
    # ============================================================
    @staticmethod
    def get_form_choices():
        return {
            "contractors": get_all_contractors(only_active=True),
            "contract_types": get_all_contract_types(only_active=True),
            "areas": get_all_areas(only_active=True),
        }

    # ============================================================
    # ★ ایجاد
    # ============================================================
    @staticmethod
    def create(data, created_by=None):
        errors = ProjectService.validate(data)
        if errors:
            return {"success": False, "errors": errors}

        code = (data.get("code") or "").strip()
        if code:
            existing = get_project_by_code(code)
            if existing:
                return {
                    "success": False,
                    "errors": {"code": "این کد قبلاً استفاده شده است"}
                }

        clean_data = ProjectService._clean_data(data)
        clean_data["created_by"] = created_by

        new_id = create_project(**clean_data)
        if not new_id:
            return {
                "success": False,
                "errors": {"general": "خطا در ذخیره‌سازی پروژه"}
            }
        return {"success": True, "id": new_id}

    # ============================================================
    # ★ ویرایش
    # ============================================================
    @staticmethod
    def update(project_id, data):
        existing = get_project(project_id)
        if not existing:
            return {
                "success": False,
                "errors": {"general": "پروژه یافت نشد"}
            }

        errors = ProjectService.validate(data)
        if errors:
            return {"success": False, "errors": errors}

        code = (data.get("code") or "").strip()
        if code:
            dup = get_project_by_code(code)
            if dup and dup["id"] != project_id:
                return {
                    "success": False,
                    "errors": {"code": "این کد قبلاً استفاده شده است"}
                }

        clean_data = ProjectService._clean_data(data)
        ok = update_project(project_id, **clean_data)

        if not ok:
            return {
                "success": False,
                "errors": {"general": "خطا در به‌روزرسانی"}
            }
        return {"success": True}

    # ============================================================
    # ★ حذف
    # ============================================================
    @staticmethod
    def delete(project_id):
        existing = get_project(project_id)
        if not existing:
            return {
                "success": False,
                "errors": {"general": "پروژه یافت نشد"}
            }
        ok = delete_project(project_id)
        if not ok:
            return {
                "success": False,
                "errors": {"general": "خطا در حذف"}
            }
        return {"success": True}

    # ============================================================
    # ★ تغییر وضعیت
    # ============================================================
    @staticmethod
    def toggle_active(project_id):
        existing = get_project(project_id)
        if not existing:
            return {"success": False}
        new_status = 0 if existing.get("is_active") else 1
        ok = update_project(project_id, is_active=new_status)
        return {"success": ok, "is_active": new_status}

    # ============================================================
    # ★ اعتبارسنجی
    # ============================================================
    @staticmethod
    def validate(data):
        errors = {}

        name = (data.get("name") or "").strip()
        if not name:
            errors["name"] = "نام پروژه الزامی است"
        elif len(name) < 3:
            errors["name"] = "نام پروژه باید حداقل ۳ کاراکتر باشد"
        elif len(name) > 250:
            errors["name"] = "نام پروژه نباید بیشتر از ۲۵۰ کاراکتر باشد"

        code = (data.get("code") or "").strip()
        if code and len(code) > 50:
            errors["code"] = "کد پروژه نباید بیشتر از ۵۰ کاراکتر باشد"

        # چک درصد پیشرفت
        progress = data.get("progress_percent")
        if progress not in (None, ""):
            try:
                p = int(progress)
                if p < 0 or p > 100:
                    errors["progress_percent"] = "درصد پیشرفت باید بین ۰ تا ۱۰۰ باشد"
            except (ValueError, TypeError):
                errors["progress_percent"] = "درصد پیشرفت نامعتبر است"

        # چک مبلغ
        amount = data.get("contract_amount")
        if amount not in (None, ""):
            try:
                float(amount)
            except (ValueError, TypeError):
                errors["contract_amount"] = "مبلغ قرارداد نامعتبر است"

        return errors

    # ============================================================
    # ★ کمکی
    # ============================================================
    @staticmethod
    def _clean_data(data):
        cleaned = {}
        numeric_fields = {"contract_amount", "budget", "latitude", "longitude"}
        int_fields = {
            "progress_percent", "physical_progress", "financial_progress",
            "duration_days", "sort_order", "is_active",
            "contractor_id", "contract_type_id", "area_id",
        }

        for key, value in data.items():
            if key == "is_active":
                cleaned[key] = 1 if value else 0
                continue

            if key in int_fields:
                try:
                    cleaned[key] = int(value) if value not in (None, "") else None
                except (ValueError, TypeError):
                    cleaned[key] = None
                continue

            if key in numeric_fields:
                try:
                    cleaned[key] = float(value) if value not in (None, "") else None
                except (ValueError, TypeError):
                    cleaned[key] = None
                continue

            if isinstance(value, str):
                value = value.strip()
                cleaned[key] = value if value else None
            else:
                cleaned[key] = value

        return cleaned


    # ============================================================
    # ★ Excel — Export
    # ============================================================
    @staticmethod
    def export_excel(output_path=None, **filters):
        try:
            from .project_excel_service import export_projects_to_excel
            path = export_projects_to_excel(output_path, **filters)
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
        try:
            from .project_excel_service import import_projects_from_excel
            return import_projects_from_excel(
                file_path, update_existing=update_existing
            )
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
        try:
            from .project_excel_service import generate_import_template
            path = generate_import_template(output_path)
            return {"success": True, "path": path}
        except Exception as e:
            return {
                "success": False,
                "errors": {"general": f"خطا در ساخت قالب: {e}"}
            }