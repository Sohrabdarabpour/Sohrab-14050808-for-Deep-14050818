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
from forms.document_group import DocumentGroupForm
from services.document_group import (
    DocumentGroupService,
    DocumentSubgroupService,
    DocumentGroupExcelService,
)
from services.departments.department_service import DepartmentService
from security.decorators import role_required, login_required


# ============================================================
# ★ لیست گروه‌های سند
# ============================================================
@document_group_bp.route("/", methods=["GET"])
@login_required
@role_required("admin", "manager")
def group_list():
    """لیست همه گروه‌های سند"""

    search = request.args.get("search", "").strip()
    active_only = request.args.get("active", "") == "1"
    department_id = request.args.get("department_id", type=int)

    groups = DocumentGroupService.get_all(
        active_only=active_only,
        search=search if search else None,
        department_id=department_id,
        with_subgroups=True,
    )

    stats = DocumentGroupService.get_stats()
    departments = DepartmentService.get_all()

    return render_template(
        "document_group/groups/list.html",
        groups=groups,
        stats=stats,
        search=search,
        active_only=active_only,
        departments=departments,
        selected_department_id=department_id,
    )


# ============================================================
# ★ ایجاد گروه سند
# ============================================================
@document_group_bp.route("/add", methods=["GET", "POST"])
@login_required
@role_required("admin")
def group_add():
    """ایجاد گروه سند جدید"""

    form = DocumentGroupForm()

    # ★ پر کردن choices زیرگروه‌ها
    subgroups = DocumentSubgroupService.get_all_simple(active_only=True)
    form.subgroup_ids.choices = [
        (sg["id"], sg["title"]) for sg in subgroups
    ]

    if form.validate_on_submit():
        # ★ پردازش sort orders
        subgroup_sort_orders = _parse_sort_orders(
            form.subgroup_sort_orders.data
        )

        success, message, group_id = DocumentGroupService.create(
            title=form.title.data,
            code=form.code.data,
            color=form.color.data,
            description=form.description.data,
            sort_order=form.sort_order.data,
            is_active=1 if form.is_active.data else 0,
            subgroup_ids=form.subgroup_ids.data or [],
            subgroup_sort_orders=subgroup_sort_orders,
        )

        if success:
            flash(message, "success")
            return redirect(url_for("document_group.group_list"))

        flash(message, "danger")

    return render_template(
        "document_group/groups/form.html",
        form=form,
        group=None,
        mode="add",
    )


# ============================================================
# ★ ویرایش گروه سند
# ============================================================
@document_group_bp.route("/<int:group_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def group_edit(group_id):
    """ویرایش گروه سند"""

    group = DocumentGroupService.get_by_id(group_id)
    if not group:
        flash("گروه پیدا نشد", "danger")
        return redirect(url_for("document_group.group_list"))

    form = DocumentGroupForm()

    # ★ پر کردن choices زیرگروه‌ها
    subgroups = DocumentSubgroupService.get_all_simple(active_only=True)
    form.subgroup_ids.choices = [
        (sg["id"], sg["title"]) for sg in subgroups
    ]

    # ★ فقط وقتی فرم تازه باز شده، مقادیر رو از DB پر کن
    if not form.is_submitted():
        form.title.data = group["title"]
        form.code.data = group["code"]
        form.color.data = group["color"]
        form.description.data = group["description"]
        form.sort_order.data = group["sort_order"]
        form.is_active.data = bool(group["is_active"])

        # ★ زیرگروه‌های مرتبط (M:N)
        form.subgroup_ids.data = group.get("subgroup_ids", [])

        # ★ sort orders
        subgroup_sort_orders = {}
        for sg in group.get("subgroups", []):
            subgroup_sort_orders[sg["id"]] = sg.get("link_sort_order", 0)
        form.subgroup_sort_orders.data = json.dumps(subgroup_sort_orders)

    if form.validate_on_submit():
        subgroup_sort_orders = _parse_sort_orders(
            form.subgroup_sort_orders.data
        )

        success, message = DocumentGroupService.update(
            group_id=group_id,
            title=form.title.data,
            code=form.code.data,
            color=form.color.data,
            description=form.description.data,
            sort_order=form.sort_order.data,
            is_active=1 if form.is_active.data else 0,
            subgroup_ids=form.subgroup_ids.data or [],
            subgroup_sort_orders=subgroup_sort_orders,
        )

        if success:
            flash(message, "success")
            return redirect(url_for("document_group.group_list"))

        flash(message, "danger")

    return render_template(
        "document_group/groups/form.html",
        form=form,
        group=group,
        mode="edit",
    )


# ============================================================
# ★ جزئیات گروه سند
# ============================================================
@document_group_bp.route("/<int:group_id>", methods=["GET"])
@login_required
@role_required("admin", "manager")
def group_detail(group_id):
    """نمایش جزئیات گروه به همراه زیرگروه‌ها"""

    group = DocumentGroupService.get_by_id(group_id)
    if not group:
        flash("گروه پیدا نشد", "danger")
        return redirect(url_for("document_group.group_list"))

    subgroups = DocumentGroupService.get_subgroups(group_id)

    return render_template(
        "document_group/groups/detail.html",
        group=group,
        subgroups=subgroups,
    )


# ============================================================
# ★ حذف گروه سند
# ============================================================
@document_group_bp.route("/<int:group_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def group_delete(group_id):
    """حذف گروه سند"""

    success, message = DocumentGroupService.delete(group_id)
    flash(message, "success" if success else "danger")
    return redirect(url_for("document_group.group_list"))


# ============================================================
# ★ تغییر وضعیت فعال/غیرفعال گروه
# ============================================================
@document_group_bp.route("/<int:group_id>/toggle", methods=["POST"])
@login_required
@role_required("admin")
def group_toggle(group_id):
    """تغییر وضعیت فعال/غیرفعال گروه"""

    success, message = DocumentGroupService.toggle_active(group_id)
    flash(message, "success" if success else "danger")
    return redirect(url_for("document_group.group_list"))


# ============================================================
# ★★★ افزودن زیرگروه به گروه ★★★
# ============================================================
@document_group_bp.route(
    "/<int:group_id>/add-subgroup", methods=["POST"]
)
@login_required
@role_required("admin")
def group_add_subgroup(group_id):
    """افزودن زیرگروه به گروه (بدون حذف قبلی‌ها)"""

    subgroup_id = request.form.get("subgroup_id", type=int)
    if not subgroup_id:
        flash("زیرگروه انتخاب نشده", "danger")
        return redirect(
            url_for("document_group.group_edit", group_id=group_id)
        )

    success, message = DocumentGroupService.add_subgroups(
        group_id, [subgroup_id]
    )
    flash(message, "success" if success else "danger")
    return redirect(url_for("document_group.group_edit", group_id=group_id))


# ============================================================
# ★★★ حذف زیرگروه از گروه ★★★
# ============================================================
@document_group_bp.route(
    "/<int:group_id>/remove-subgroup/<int:subgroup_id>",
    methods=["POST"]
)
@login_required
@role_required("admin")
def group_remove_subgroup(group_id, subgroup_id):
    """حذف یک زیرگروه از گروه"""

    success, message = DocumentGroupService.remove_subgroup(
        group_id, subgroup_id
    )
    flash(message, "success" if success else "danger")
    return redirect(url_for("document_group.group_edit", group_id=group_id))


# ============================================================
# ★★★ خروجی اکسل گروه‌ها ★★★
# ============================================================
@document_group_bp.route("/export/excel", methods=["GET"])
@login_required
@role_required("admin", "manager")
def group_export_excel():
    """خروجی اکسل از لیست گروه‌های سند"""

    output = DocumentGroupExcelService.export_groups()
    filename = DocumentGroupExcelService.build_export_filename()

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
# ★★★ صفحه ایمپورت گروه‌ها ★★★
# ============================================================
@document_group_bp.route("/import", methods=["GET"])
@login_required
@role_required("admin")
def group_import():
    """صفحه ایمپورت گروه‌ها از اکسل"""
    return render_template("document_group/groups/import.html")


# ============================================================
# ★★★ دانلود قالب ایمپورت گروه‌ها ★★★
# ============================================================
@document_group_bp.route("/import/template", methods=["GET"])
@login_required
@role_required("admin")
def group_import_template():
    """دانلود قالب اکسل برای ایمپورت گروه‌ها"""

    output = DocumentGroupExcelService.export_groups()
    return send_file(
        output,
        mimetype=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
        as_attachment=True,
        download_name="document_groups_template.xlsx"
    )


# ============================================================
# ★★★ پردازش آپلود فایل اکسل گروه‌ها ★★★
# ============================================================
@document_group_bp.route("/import", methods=["POST"])
@login_required
@role_required("admin")
def group_import_process():
    """پردازش آپلود فایل اکسل گروه‌ها"""

    # ★ چک وجود فایل
    if "file" not in request.files:
        flash("فایلی انتخاب نشده است", "danger")
        return redirect(url_for("document_group.group_import"))

    file = request.files["file"]
    if not file.filename:
        flash("فایلی انتخاب نشده است", "danger")
        return redirect(url_for("document_group.group_import"))

    # ★ چک فرمت
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        flash("فرمت فایل باید Excel باشد (.xlsx یا .xls)", "danger")
        return redirect(url_for("document_group.group_import"))

    # ★ چک حالت
    mode = request.form.get("mode", "append")
    if mode not in ("append", "replace"):
        flash("حالت ایمپورت نامعتبر است", "danger")
        return redirect(url_for("document_group.group_import"))

    temp_path = None
    try:
        # ★ ذخیره موقت
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".xlsx"
        ) as tmp:
            file.save(tmp.name)
            temp_path = tmp.name

        # ★ پردازش
        result = DocumentGroupExcelService.import_groups(
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
        # ★ پاک کردن فایل موقت
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

    return redirect(url_for("document_group.group_list"))


# ============================================================
# ★ HELPER: پردازش sort orders از JSON
# ============================================================
def _parse_sort_orders(raw):
    """
    تبدیل JSON string به دیکشنری {int: int}
    اگه خطا داد، دیکشنری خالی برمی‌گردونه
    """
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return {int(k): int(v) for k, v in data.items()}
    except (ValueError, TypeError, AttributeError):
        return {}