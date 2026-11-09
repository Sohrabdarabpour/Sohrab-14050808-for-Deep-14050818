"""
سرویس مدیریت نقش‌های پروژه
"""
from database.init_db import (
    get_all_project_roles,
    get_project_role,
    get_project_role_by_code,
    create_project_role,
    update_project_role,
    delete_project_role,
)


class ProjectRoleService:
    """سرویس نقش‌های پروژه"""

    # ============================================================
    # ★ خواندن
    # ============================================================
    @staticmethod
    def list_all(only_active=False):
        return get_all_project_roles(only_active=only_active)

    @staticmethod
    def get(role_id):
        if not role_id:
            return None
        return get_project_role(role_id)

    @staticmethod
    def find_by_code(code):
        if not code:
            return None
        return get_project_role_by_code(code)

    # ============================================================
    # ★ ایجاد
    # ============================================================
    @staticmethod
    def create(data):
        errors = ProjectRoleService.validate(data)
        if errors:
            return {"success": False, "errors": errors}

        title = (data.get("title") or "").strip()
        code = (data.get("code") or "").strip()

        # چک تکراری code
        if code:
            existing = get_project_role_by_code(code)
            if existing:
                return {
                    "success": False,
                    "errors": {"code": "این کد قبلاً استفاده شده است"}
                }

        # چک تکراری title
        all_roles = get_all_project_roles()
        for r in all_roles:
            if r["title"] == title:
                return {
                    "success": False,
                    "errors": {"title": "این عنوان قبلاً ثبت شده است"}
                }

        new_id = create_project_role(
            title=title,
            code=code or None,
            color=data.get("color") or "#1b698b",
            description=data.get("description") or None,
            is_exclusive=1 if data.get("is_exclusive") else 0,
            is_required=1 if data.get("is_required") else 0,
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
    def update(role_id, data):
        existing = get_project_role(role_id)
        if not existing:
            return {
                "success": False,
                "errors": {"general": "نقش یافت نشد"}
            }

        errors = ProjectRoleService.validate(data)
        if errors:
            return {"success": False, "errors": errors}

        code = (data.get("code") or "").strip()
        if code:
            dup = get_project_role_by_code(code)
            if dup and dup["id"] != role_id:
                return {
                    "success": False,
                    "errors": {"code": "این کد قبلاً استفاده شده است"}
                }

        ok = update_project_role(
            role_id,
            title=(data.get("title") or "").strip(),
            code=code or None,
            color=data.get("color") or "#1b698b",
            description=data.get("description") or None,
            is_exclusive=1 if data.get("is_exclusive") else 0,
            is_required=1 if data.get("is_required") else 0,
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
    def delete(role_id):
        existing = get_project_role(role_id)
        if not existing:
            return {
                "success": False,
                "errors": {"general": "نقش یافت نشد"}
            }

        # چک استفاده در پروژه‌ها
        from database.connection import get_connection
        connection = get_connection()
        try:
            row = connection.execute(
                "SELECT COUNT(*) AS c FROM project_members "
                "WHERE role_id = ? AND is_active = 1",
                (role_id,)
            ).fetchone()
            if row and row["c"] > 0:
                return {
                    "success": False,
                    "errors": {
                        "general": f"این نقش در {row['c']} پروژه "
                                   f"استفاده شده و قابل حذف نیست"
                    }
                }
        finally:
            connection.close()

        ok = delete_project_role(role_id)
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
    def toggle_active(role_id):
        existing = get_project_role(role_id)
        if not existing:
            return {"success": False}
        new_status = 0 if existing.get("is_active") else 1
        ok = update_project_role(role_id, is_active=new_status)
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