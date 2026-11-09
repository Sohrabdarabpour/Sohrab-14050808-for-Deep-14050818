"""
سرویس مدیریت انواع قرارداد
"""
from database.init_db import (
    get_all_contract_types,
    get_contract_type,
    get_contract_type_by_code,
    create_contract_type,
    update_contract_type,
    delete_contract_type,
)


class ContractTypeService:
    """سرویس انواع قرارداد"""

    # ============================================================
    # ★ خواندن
    # ============================================================
    @staticmethod
    def list_all(only_active=False):
        return get_all_contract_types(only_active=only_active)

    @staticmethod
    def get(contract_type_id):
        if not contract_type_id:
            return None
        return get_contract_type(contract_type_id)

    @staticmethod
    def find_by_code(code):
        if not code:
            return None
        return get_contract_type_by_code(code)

    # ============================================================
    # ★ ایجاد
    # ============================================================
    @staticmethod
    def create(data):
        errors = ContractTypeService.validate(data)
        if errors:
            return {"success": False, "errors": errors}

        title = (data.get("title") or "").strip()
        code = (data.get("code") or "").strip()

        # چک تکراری
        if code:
            existing = get_contract_type_by_code(code)
            if existing:
                return {
                    "success": False,
                    "errors": {"code": "این کد قبلاً استفاده شده است"}
                }

        # چک تکراری بودن title
        all_types = get_all_contract_types()
        for t in all_types:
            if t["title"] == title:
                return {
                    "success": False,
                    "errors": {"title": "این عنوان قبلاً ثبت شده است"}
                }

        new_id = create_contract_type(
            title=title,
            code=code or None,
            color=data.get("color") or "#1b698b",
            description=data.get("description") or None,
            sort_order=int(data.get("sort_order") or 0),
            is_active=1 if data.get("is_active") else 0,
        )

        if not new_id:
            return {
                "success": False,
                "errors": {"general": "خطا در ذخیره‌سازی"}
            }
        return {"success": True, "id": new_id}

    # ============================================================
    # ★ ویرایش
    # ============================================================
    @staticmethod
    def update(contract_type_id, data):
        existing = get_contract_type(contract_type_id)
        if not existing:
            return {
                "success": False,
                "errors": {"general": "نوع قرارداد یافت نشد"}
            }

        errors = ContractTypeService.validate(data)
        if errors:
            return {"success": False, "errors": errors}

        code = (data.get("code") or "").strip()
        if code:
            dup = get_contract_type_by_code(code)
            if dup and dup["id"] != contract_type_id:
                return {
                    "success": False,
                    "errors": {"code": "این کد قبلاً استفاده شده است"}
                }

        ok = update_contract_type(
            contract_type_id,
            title=(data.get("title") or "").strip(),
            code=code or None,
            color=data.get("color") or "#1b698b",
            description=data.get("description") or None,
            sort_order=int(data.get("sort_order") or 0),
            is_active=1 if data.get("is_active") else 0,
        )

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
    def delete(contract_type_id):
        existing = get_contract_type(contract_type_id)
        if not existing:
            return {
                "success": False,
                "errors": {"general": "نوع قرارداد یافت نشد"}
            }

        # چک استفاده در پروژه‌ها
        from database.connection import get_connection
        connection = get_connection()
        try:
            row = connection.execute(
                "SELECT COUNT(*) AS c FROM projects WHERE contract_type_id = ?",
                (contract_type_id,)
            ).fetchone()
            if row and row["c"] > 0:
                return {
                    "success": False,
                    "errors": {
                        "general": f"این نوع قرارداد در {row['c']} پروژه "
                                   f"استفاده شده و قابل حذف نیست"
                    }
                }
        finally:
            connection.close()

        ok = delete_contract_type(contract_type_id)
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
    def toggle_active(contract_type_id):
        existing = get_contract_type(contract_type_id)
        if not existing:
            return {"success": False}
        new_status = 0 if existing.get("is_active") else 1
        ok = update_contract_type(contract_type_id, is_active=new_status)
        return {"success": ok, "is_active": new_status}

    # ============================================================
    # ★ اعتبارسنجی
    # ============================================================
    @staticmethod
    def validate(data):
        errors = {}
        title = (data.get("title") or "").strip()
        if not title:
            errors["title"] = "عنوان الزامی است"
        elif len(title) > 150:
            errors["title"] = "عنوان نباید بیشتر از ۱۵۰ کاراکتر باشد"

        code = (data.get("code") or "").strip()
        if code and len(code) > 50:
            errors["code"] = "کد نباید بیشتر از ۵۰ کاراکتر باشد"

        return errors