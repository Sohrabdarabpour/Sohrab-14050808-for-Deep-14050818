"""
سرویس اعضای تیم پروژه
"""
from database.init_db import (
    get_project_members,
    get_user_projects,
    get_project_role_members,
    is_project_member,
    add_project_member,
    update_project_member,
    remove_project_member,
    get_project_role,
    get_project,
    get_project_roles,
)


class ProjectMemberService:
    """سرویس اعضای تیم پروژه"""

    # ============================================================
    # ★ خواندن
    # ============================================================
    @staticmethod
    def list_members(project_id):
        return get_project_members(project_id)

    @staticmethod
    def list_user_projects(user_id):
        return get_user_projects(user_id)

    @staticmethod
    def list_role_members(project_id, role_id):
        return get_project_role_members(project_id, role_id)

    # ============================================================
    # ★ افزودن عضو
    # ============================================================
    @staticmethod
    def add_member(project_id, user_id, role_id, responsibility=None,
                   notes=None, assigned_by=None):
        # چک وجود پروژه
        if not get_project(project_id):
            return {
                "success": False,
                "errors": {"general": "پروژه یافت نشد"}
            }

        # چک وجود نقش
        role = get_project_role(role_id)
        if not role:
            return {
                "success": False,
                "errors": {"role_id": "نقش یافت نشد"}
            }

        # چک تکراری بودن
        if is_project_member(project_id, user_id, role_id):
            return {
                "success": False,
                "errors": {
                    "general": "این کاربر قبلاً در این نقش ثبت شده است"
                }
            }

        # اگه نقش انحصاریه — چک کن کسی دیگه این نقش رو نداشته باشه
        if role.get("is_exclusive"):
            existing = get_project_role_members(project_id, role_id)
            if existing:
                return {
                    "success": False,
                    "errors": {
                        "role_id": f"نقش «{role['title']}» قبلاً به "
                                   f"«{existing[0].get('full_name', '')}» "
                                   f"تخصیص یافته است"
                    }
                }

        new_id = add_project_member(
            project_id=project_id,
            user_id=user_id,
            role_id=role_id,
            responsibility=responsibility,
            notes=notes,
            assigned_by=assigned_by,
        )

        if not new_id:
            return {
                "success": False,
                "errors": {"general": "خطا در افزودن عضو"}
            }
        return {"success": True, "id": new_id}

    # ============================================================
    # ★ ویرایش عضو
    # ============================================================
    @staticmethod
    def update_member(member_id, data):
        ok = update_project_member(
            member_id,
            responsibility=data.get("responsibility"),
            notes=data.get("notes"),
        )
        if not ok:
            return {
                "success": False,
                "errors": {"general": "خطا در به‌روزرسانی"}
            }
        return {"success": True}

    # ============================================================
    # ★ حذف عضو
    # ============================================================
    @staticmethod
    def remove_member(member_id):
        ok = remove_project_member(member_id)
        if not ok:
            return {
                "success": False,
                "errors": {"general": "خطا در حذف عضو"}
            }
        return {"success": True}