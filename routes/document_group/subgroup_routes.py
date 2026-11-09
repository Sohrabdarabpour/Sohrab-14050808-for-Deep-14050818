import os
import tempfile
import json
from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    request,
    abort,
    send_file,
)
from . import document_group_bp
from forms.document_group import DocumentSubgroupForm
from services.document_group import (
    DocumentGroupService,
    DocumentSubgroupService,
    DocumentSubgroupExcelService,
)
from services.departments.department_service import DepartmentService
from security.decorators import role_required, login_required


# ============================================================
# ★ لیست زیرگروه‌ها
# ============================================================
@document_group_bp.route("/subgroups/", methods=["GET"])
@login_required
@role_required("admin", "manager")
def subgroup_list():
    """لیست همه زیرگروه‌ها"""

    search = request.args.get("search", "").strip()
    group_id = request.args.get("group_id", type=int)
    department_id = request.args.get("department_id", type=int)
    active_only = request.args.get("active", "") == "1"

    subgroups = DocumentSubgroupService.get_all(
        group_id=group_id,
        department_id=department_id,
        active_only=active_only,
        search=search if search else None,
    )

    groups = DocumentGroupService.get_all(active_only=False)
    departments = DepartmentService.get_all()

    return render_template(
        "document_group/subgroups/list.html",
        subgroups=subgroups,
        groups=groups,
        departments=departments,
        search=search,
        selected_group_id=group_id,
        selected_department_id=department_id,
        active_only=active_only,
    )


# ============================================================
# ★ ایجاد زیرگروه
# ============================================================
@document_group_bp.route("/subgroups/add", methods=["GET", "POST"])
@login_required
@role_required("admin")
def subgroup_add():
    """ایجاد زیرگروه جدید"""

    form = DocumentSubgroupForm()

    # ★ پر کردن choices گروه‌ها
    groups = DocumentGroupService.get_all_simple(active_only=True)
    form.group_ids.choices = [(g["id"], g["title"]) for g in groups]

    # ★ پر کردن choices دپارتمان‌ها
    departments = DepartmentService.get_all()
    form.department_ids.choices = [
        (d["id"], d["title"]) for d in departments
    ]

    # ★ پیش‌انتخاب گروه از URL
    preselected_group = request.args.get("group_id", type=int)
    if not form.is_submitted() and preselected_group:
        form.group_ids.data = [preselected_group]

    if form.validate_on_submit():
        # ★ پردازش group sort orders
        group_sort_orders = _parse_sort_orders(
            form.group_sort_orders.data
        )

        success, message, subgroup_id = DocumentSubgroupService.create(
            title=form.title.data,
            code=form.code.data,
            color=form.color.data,
            days_review=form.days_review.data,
            description=form.description.data,
            sort_order=form.sort_order.data,
            is_active=1 if form.is_active.data else 0,
            group_ids=form.group_ids.data or [],
            department_ids=form.department_ids.data or [],
            group_sort_orders=group_sort_orders,
        )

        if success:
            flash(message, "success")
            return redirect(url_for("document_group.subgroup_list"))

        flash(message, "danger")

    return render_template(
        "document_group/subgroups/form.html",
        form=form,
        subgroup=None,
        mode="add",
    )


# ============================================================
# ★ ویرایش زیرگروه
# ============================================================
@document_group_bp.route(
    "/subgroups/<int:subgroup_id>/edit", methods=["GET", "POST"]
)
@login_required
@role_required("admin")
def subgroup_edit(subgroup_id):
    """ویرایش زیرگروه"""

    subgroup = DocumentSubgroupService.get_by_id(subgroup_id)
    if not subgroup:
        flash("زیرگروه پیدا نشد", "danger")
        return redirect(url_for("document_group.subgroup_list"))

    form = DocumentSubgroupForm()

    # ★ پر کردن choices
    groups = DocumentGroupService.get_all_simple(active_only=True)
    form.group_ids.choices = [(g["id"], g["title"]) for g in groups]

    departments = DepartmentService.get_all()
    form.department_ids.choices = [
        (d["id"], d["title"]) for d in departments
    ]

    # ★ فقط وقتی فرم تازه باز شده، مقادیر رو از DB پر کن
    if not form.is_submitted():
        form.title.data = subgroup["title"]
        form.code.data = subgroup["code"]
        form.color.data = subgroup["color"]
        form.days_review.data = subgroup["days_review"]
        form.description.data = subgroup["description"]
        form.sort_order.data = subgroup["sort_order"]
        form.is_active.data = bool(subgroup["is_active"])

        # ★ گروه‌ها (M:N)
        form.group_ids.data = subgroup.get("group_ids", [])

        # ★ دپارتمان‌ها (M:N)
        form.department_ids.data = subgroup.get("department_ids", [])

        # ★ sort orders
        group_sort_orders = {}
        for g in subgroup.get("groups", []):
            group_sort_orders[g["id"]] = g.get("link_sort_order", 0)
        form.group_sort_orders.data = json.dumps(group_sort_orders)

    if form.validate_on_submit():
        group_sort_orders = _parse_sort_orders(
            form.group_sort_orders.data
        )

        success, message = DocumentSubgroupService.update(
            subgroup_id=subgroup_id,
            title=form.title.data,
            code=form.code.data,
            color=form.color.data,
            days_review=form.days_review.data,
            description=form.description.data,
            sort_order=form.sort_order.data,
            is_active=1 if form.is_active.data else 0,
            group_ids=form.group_ids.data or [],
            department_ids=form.department_ids.data or [],
            group_sort_orders=group_sort_orders,
        )

        if success:
            flash(message, "success")
            return redirect(url_for("document_group.subgroup_list"))

        flash(message, "danger")

    return render_template(
        "document_group/subgroups/form.html",
        form=form,
        subgroup=subgroup,
        mode="edit",
    )


# ============================================================
# ★ جزئیات زیرگروه
# ============================================================
@document_group_bp.route(
    "/subgroups/<int:subgroup_id>", methods=["GET"]
)
@login_required
@role_required("admin", "manager")
def subgroup_detail(subgroup_id):
    """نمایش جزئیات زیرگروه"""

    subgroup = DocumentSubgroupService.get_by_id(subgroup_id)
    if not subgroup:
        flash("زیرگروه پیدا نشد", "danger")
        return redirect(url_for("document_group.subgroup_list"))

    return render_template(
        "document_group/subgroups/detail.html",
        subgroup=subgroup,
    )


# ============================================================
# ★ حذف زیرگروه
# ============================================================
@document_group_bp.route(
    "/subgroups/<int:subgroup_id>/delete", methods=["POST"]
)
@login_required
@role_required("admin")
def subgroup_delete(subgroup_id):
    """حذف زیرگروه"""

    success, message = DocumentSubgroupService.delete(subgroup_id)
    flash(message, "success" if success else "danger")
    return redirect(url_for("document_group.subgroup_list"))


# ============================================================
# ★ تغییر وضعیت فعال/غیرفعال زیرگروه
# ============================================================
@document_group_bp.route(
    "/subgroups/<int:subgroup_id>/toggle", methods=["POST"]
)
@login_required
@role_required("admin")
def subgroup_toggle(subgroup_id):
    """تغییر وضعیت فعال/غیرفعال زیرگروه"""

    success, message = DocumentSubgroupService.toggle_active(subgroup_id)
    flash(message, "success" if success else "danger")
    return redirect(url_for("document_group.subgroup_list"))


# ============================================================
# ★★★ افزودن گروه به زیرگروه ★★★
# ============================================================
@document_group_bp.route(
    "/subgroups/<int:subgroup_id>/add-group", methods=["POST"]
)
@login_required
@role_required("admin")
def subgroup_add_group(subgroup_id):
    """افزودن گروه به زیرگروه (بدون حذف قبلی‌ها)"""
    group_id = request.form.get("group_id", type=int)
    if not group_id:
        flash("گروه انتخاب نشده", "danger")
        return redirect(
            url_for("document_group.subgroup_edit", subgroup_id=subgroup_id)
        )

    success, message = DocumentSubgroupService.add_groups(
        subgroup_id, [group_id]
    )
    flash(message, "success" if success else "danger")
    return redirect(
        url_for("document_group.subgroup_edit", subgroup_id=subgroup_id)
    )


# ============================================================
# ★★★ حذف گروه از زیرگروه ★★★
# ============================================================
@document_group_bp.route(
    "/subgroups/<int:subgroup_id>/remove-group/<int:group_id>",
    methods=["POST"]
)
@login_required
@role_required("admin")
def subgroup_remove_group(subgroup_id, group_id):
    """حذف یک گروه از زیرگروه"""
    success, message = DocumentSubgroupService.remove_group(
        subgroup_id, group_id
    )
    flash(message, "success" if success else "danger")
    return redirect(
        url_for("document_group.subgroup_edit", subgroup_id=subgroup_id)
    )


# ============================================================
# ★★★ افزودن دپارتمان به زیرگروه ★★★
# ============================================================
@document_group_bp.route(
    "/subgroups/<int:subgroup_id>/add-department", methods=["POST"]
)
@login_required
@role_required("admin")
def subgroup_add_department(subgroup_id):
    """افزودن دپارتمان به زیرگروه (بدون حذف قبلی‌ها)"""
    department_id = request.form.get("department_id", type=int)
    if not department_id:
        flash("دپارتمان انتخاب نشده", "danger")
        return redirect(
            url_for("document_group.subgroup_edit", subgroup_id=subgroup_id)
        )

    success, message = DocumentSubgroupService.add_department(
        subgroup_id, department_id
    )
    flash(message, "success" if success else "danger")
    return redirect(
        url_for("document_group.subgroup_edit", subgroup_id=subgroup_id)
    )


# ============================================================
# ★★★ حذف دپارتمان از زیرگروه ★★★
# ============================================================
@document_group_bp.route(
    "/subgroups/<int:subgroup_id>/remove-department/<int:department_id>",
    methods=["POST"]
)
@login_required
@role_required("admin")
def subgroup_remove_department(subgroup_id, department_id):
    """حذف یک دپارتمان از زیرگروه"""
    success, message = DocumentSubgroupService.remove_department(
        subgroup_id, department_id
    )
    flash(message, "success" if success else "danger")
    return redirect(
        url_for("document_group.subgroup_edit", subgroup_id=subgroup_id)
    )


# ============================================================
# ★★★ خروجی اکسل زیرگروه‌ها ★★★
# ============================================================
@document_group_bp.route("/subgroups/export/excel", methods=["GET"])
@login_required
@role_required("admin", "manager")
def subgroup_export_excel():
    """خروجی اکسل از لیست زیرگروه‌ها"""

    group_id = request.args.get("group_id", type=int)
    department_id = request.args.get("department_id", type=int)

    output = DocumentSubgroupExcelService.export_subgroups(
        group_id=group_id,
        department_id=department_id,
    )
    filename = DocumentSubgroupExcelService.build_export_filename(
        group_id=group_id,
        department_id=department_id,
    )

    return send_file(
        output,
        mimetype=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
        as_attachment=True,
        download_name=filename
    )


# ============================================================
# ★★★ صفحه ایمپورت زیرگروه‌ها ★★★
# ============================================================
@document_group_bp.route("/subgroups/import", methods=["GET"])
@login_required
@role_required("admin")
def subgroup_import():
    """صفحه ایمپورت زیرگروه‌ها از اکسل"""
    return render_template("document_group/subgroups/import.html")


# ============================================================
# ★★★ دانلود قالب ایمپورت زیرگروه‌ها ★★★
# ============================================================
@document_group_bp.route("/subgroups/import/template", methods=["GET"])
@login_required
@role_required("admin")
def subgroup_import_template():
    """دانلود قالب اکسل برای ایمپورت زیرگروه‌ها"""

    output = DocumentSubgroupExcelService.export_subgroups()
    return send_file(
        output,
        mimetype=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
        as_attachment=True,
        download_name="document_subgroups_template.xlsx"
    )


# ============================================================
# ★★★ پردازش آپلود فایل اکسل زیرگروه‌ها ★★★
# ============================================================
@document_group_bp.route("/subgroups/import", methods=["POST"])
@login_required
@role_required("admin")
def subgroup_import_process():
    """پردازش آپلود فایل اکسل زیرگروه‌ها"""

    if "file" not in request.files:
        flash("فایلی انتخاب نشده است", "danger")
        return redirect(url_for("document_group.subgroup_import"))

    file = request.files["file"]
    if not file.filename:
        flash("فایلی انتخاب نشده است", "danger")
        return redirect(url_for("document_group.subgroup_import"))

    if not file.filename.lower().endswith((".xlsx", ".xls")):
        flash("فرمت فایل باید Excel باشد (.xlsx یا .xls)", "danger")
        return redirect(url_for("document_group.subgroup_import"))

    mode = request.form.get("mode", "append")
    if mode not in ("append", "replace"):
        flash("حالت ایمپورت نامعتبر است", "danger")
        return redirect(url_for("document_group.subgroup_import"))

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".xlsx"
        ) as tmp:
            file.save(tmp.name)
            temp_path = tmp.name

        result = DocumentSubgroupExcelService.import_subgroups(
            temp_path, mode=mode
        )

        if result["success"]:
            flash(result["message"], "success")
        else:
            flash(result["message"], "warning")
            for err in result.get("error_rows", [])[:5]:
                flash(f"ردیف {err} خطا داشت", "danger")

    except Exception as e:
        flash(f"خطا در پردازش فایل: {e}", "danger")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

    return redirect(url_for("document_group.subgroup_list"))


# ============================================================
# ★ HELPER: پردازش sort orders از JSON
# ============================================================
def _parse_sort_orders(raw):
    """تبدیل JSON string به دیکشنری {int: int}"""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return {int(k): int(v) for k, v in data.items()}
    except (ValueError, TypeError, AttributeError):
        return {}


# ============================================================
# ★★★ خروجی اکسل Flat زیرگروه‌ها (هر ترکیب یک ردیف) ★★★
# ============================================================
@document_group_bp.route("/subgroups/export/excel-flat", methods=["GET"])
@login_required
@role_required("admin", "manager")
def subgroup_export_excel_flat():
    """خروجی اکسل Flat (هر دپارتمان/گروه یک ردیف جدا)"""

    from services.document_group.subgroup_excel_flat_service import (
        DocumentSubgroupExcelFlatService,
    )

    group_id = request.args.get("group_id", type=int)
    department_id = request.args.get("department_id", type=int)

    output = DocumentSubgroupExcelFlatService.export_subgroups_flat(
        group_id=group_id,
        department_id=department_id,
    )
    filename = DocumentSubgroupExcelFlatService.build_flat_filename(
        group_id=group_id,
        department_id=department_id,
    )

    return send_file(
        output,
        mimetype=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
        as_attachment=True,
        download_name=filename
    )