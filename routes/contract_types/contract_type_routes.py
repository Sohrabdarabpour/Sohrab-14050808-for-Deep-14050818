from flask import (
    render_template, request, redirect, url_for,
    flash, session
)
from . import contract_types_bp
from services.contract_types import ContractTypeService


# ================================================================
def _require_login():
    if not session.get("user_id"):
        flash("لطفاً وارد شوید", "warning")
        return redirect(url_for("auth.login"))
    return None


def _require_admin():
    """فقط admin و manager"""
    if session.get("role") not in ("admin", "manager"):
        flash("دسترسی غیرمجاز", "danger")
        return redirect(url_for("main.index"))
    return None


# ================================================================
# لیست انواع قرارداد
# ================================================================
@contract_types_bp.route("/", methods=["GET"])
def list_types():
    guard = _require_login()
    if guard:
        return guard

    only_active = request.args.get("active") == "1"
    types = ContractTypeService.list_all(only_active=only_active)

    return render_template(
        "contract_types/list.html",
        types=types,
        only_active=only_active,
    )


# ================================================================
# افزودن
# ================================================================
@contract_types_bp.route("/add", methods=["GET", "POST"])
def add_type():
    guard = _require_login() or _require_admin()
    if guard:
        return guard

    if request.method == "POST":
        data = _extract_form_data(request.form)
        result = ContractTypeService.create(data)

        if result["success"]:
            flash("نوع قرارداد با موفقیت ایجاد شد", "success")
            return redirect(url_for("contract_types.list_types"))

        for field, msg in result.get("errors", {}).items():
            flash(f"{field}: {msg}", "danger")

        return render_template(
            "contract_types/form.html",
            mode="add",
            contract_type=data,
        )

    return render_template(
        "contract_types/form.html",
        mode="add",
        contract_type={
            "title": "", "code": "", "color": "#1b698b",
            "description": "", "sort_order": 0, "is_active": 1,
        },
    )


# ================================================================
# ویرایش
# ================================================================
@contract_types_bp.route(
    "/edit/<int:type_id>", methods=["GET", "POST"]
)
def edit_type(type_id):
    guard = _require_login() or _require_admin()
    if guard:
        return guard

    contract_type = ContractTypeService.get(type_id)
    if not contract_type:
        flash("نوع قرارداد یافت نشد", "danger")
        return redirect(url_for("contract_types.list_types"))

    if request.method == "POST":
        data = _extract_form_data(request.form)
        result = ContractTypeService.update(type_id, data)

        if result["success"]:
            flash("نوع قرارداد با موفقیت به‌روزرسانی شد", "success")
            return redirect(url_for("contract_types.list_types"))

        for field, msg in result.get("errors", {}).items():
            flash(f"{field}: {msg}", "danger")

        return render_template(
            "contract_types/form.html",
            mode="edit",
            contract_type=data,
            type_id=type_id,
        )

    return render_template(
        "contract_types/form.html",
        mode="edit",
        contract_type=contract_type,
        type_id=type_id,
    )


# ================================================================
# حذف
# ================================================================
@contract_types_bp.route(
    "/delete/<int:type_id>", methods=["POST"]
)
def delete_type(type_id):
    guard = _require_login() or _require_admin()
    if guard:
        return guard

    result = ContractTypeService.delete(type_id)
    if result["success"]:
        flash("نوع قرارداد حذف شد", "success")
    else:
        for msg in result.get("errors", {}).values():
            flash(msg, "danger")

    return redirect(url_for("contract_types.list_types"))


# ================================================================
# تغییر وضعیت
# ================================================================
@contract_types_bp.route(
    "/toggle/<int:type_id>", methods=["POST"]
)
def toggle_type(type_id):
    guard = _require_login() or _require_admin()
    if guard:
        return guard

    result = ContractTypeService.toggle_active(type_id)
    if result["success"]:
        status = "فعال" if result["is_active"] else "غیرفعال"
        flash(f"وضعیت به «{status}» تغییر یافت", "success")
    else:
        flash("خطا در تغییر وضعیت", "danger")

    return redirect(url_for("contract_types.list_types"))


# ================================================================
def _extract_form_data(form):
    return {
        "title": form.get("title", "").strip(),
        "code": form.get("code", "").strip(),
        "color": form.get("color", "#1b698b").strip(),
        "description": form.get("description", "").strip(),
        "sort_order": form.get("sort_order", "0"),
        "is_active": form.get("is_active") == "1",
    }