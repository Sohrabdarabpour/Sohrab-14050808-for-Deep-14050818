from flask import (
    render_template, request, redirect, url_for,
    flash, session
)
from . import project_roles_bp
from services.project_roles import ProjectRoleService


# ================================================================
def _require_login():
    if not session.get("user_id"):
        flash("لطفاً وارد شوید", "warning")
        return redirect(url_for("auth.login"))
    return None


def _require_admin():
    if session.get("role") not in ("admin", "manager"):
        flash("دسترسی غیرمجاز", "danger")
        return redirect(url_for("main.index"))
    return None


# ================================================================
# لیست نقش‌ها
# ================================================================
@project_roles_bp.route("/", methods=["GET"])
def list_roles():
    guard = _require_login()
    if guard:
        return guard

    only_active = request.args.get("active") == "1"
    roles = ProjectRoleService.list_all(only_active=only_active)

    return render_template(
        "project_roles/list.html",
        roles=roles,
        only_active=only_active,
    )


# ================================================================
# افزودن
# ================================================================
@project_roles_bp.route("/add", methods=["GET", "POST"])
def add_role():
    guard = _require_login() or _require_admin()
    if guard:
        return guard

    if request.method == "POST":
        data = _extract_form_data(request.form)
        result = ProjectRoleService.create(data)

        if result["success"]:
            flash("نقش با موفقیت ایجاد شد", "success")
            return redirect(url_for("project_roles.list_roles"))

        for field, msg in result.get("errors", {}).items():
            flash(f"{field}: {msg}", "danger")

        return render_template(
            "project_roles/form.html",
            mode="add",
            role=data,
        )

    return render_template(
        "project_roles/form.html",
        mode="add",
        role={
            "title": "", "code": "", "color": "#1b698b",
            "description": "", "is_exclusive": 0,
            "is_required": 0, "sort_order": 0, "is_active": 1,
        },
    )


# ================================================================
# ویرایش
# ================================================================
@project_roles_bp.route(
    "/edit/<int:role_id>", methods=["GET", "POST"]
)
def edit_role(role_id):
    guard = _require_login() or _require_admin()
    if guard:
        return guard

    role = ProjectRoleService.get(role_id)
    if not role:
        flash("نقش یافت نشد", "danger")
        return redirect(url_for("project_roles.list_roles"))

    if request.method == "POST":
        data = _extract_form_data(request.form)
        result = ProjectRoleService.update(role_id, data)

        if result["success"]:
            flash("نقش با موفقیت به‌روزرسانی شد", "success")
            return redirect(url_for("project_roles.list_roles"))

        for field, msg in result.get("errors", {}).items():
            flash(f"{field}: {msg}", "danger")

        return render_template(
            "project_roles/form.html",
            mode="edit",
            role=data,
            role_id=role_id,
        )

    return render_template(
        "project_roles/form.html",
        mode="edit",
        role=role,
        role_id=role_id,
    )


# ================================================================
# حذف
# ================================================================
@project_roles_bp.route(
    "/delete/<int:role_id>", methods=["POST"]
)
def delete_role(role_id):
    guard = _require_login() or _require_admin()
    if guard:
        return guard

    result = ProjectRoleService.delete(role_id)
    if result["success"]:
        flash("نقش حذف شد", "success")
    else:
        for msg in result.get("errors", {}).values():
            flash(msg, "danger")

    return redirect(url_for("project_roles.list_roles"))


# ================================================================
# تغییر وضعیت
# ================================================================
@project_roles_bp.route(
    "/toggle/<int:role_id>", methods=["POST"]
)
def toggle_role(role_id):
    guard = _require_login() or _require_admin()
    if guard:
        return guard

    result = ProjectRoleService.toggle_active(role_id)
    if result["success"]:
        status = "فعال" if result["is_active"] else "غیرفعال"
        flash(f"وضعیت به «{status}» تغییر یافت", "success")
    else:
        flash("خطا در تغییر وضعیت", "danger")

    return redirect(url_for("project_roles.list_roles"))


# ================================================================
def _extract_form_data(form):
    return {
        "title": form.get("title", "").strip(),
        "code": form.get("code", "").strip(),
        "color": form.get("color", "#1b698b").strip(),
        "description": form.get("description", "").strip(),
        "is_exclusive": form.get("is_exclusive") == "1",
        "is_required": form.get("is_required") == "1",
        "sort_order": form.get("sort_order", "0"),
        "is_active": form.get("is_active") == "1",
    }