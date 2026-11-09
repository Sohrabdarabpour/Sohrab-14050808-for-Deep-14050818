import os
from datetime import datetime
from flask import (
    render_template, request, redirect, url_for,
    flash, session, jsonify, send_file
)
from werkzeug.utils import secure_filename

from . import projects_bp
from services.projects import ProjectService, ProjectMemberService
from services.project_roles import ProjectRoleService
from database.init_db import get_all_users_for_select
from forms.projects import ProjectForm


# ================================================================
# تنظیمات آپلود
# ================================================================
ALLOWED_EXTENSIONS = {"xlsx", "xls"}


def _require_login():
    if not session.get("user_id"):
        flash("لطفاً وارد شوید", "warning")
        return redirect(url_for("auth.login"))
    return None


def _allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# ================================================================
# لیست پروژه‌ها
# ================================================================
@projects_bp.route("/", methods=["GET"])
def list_projects():
    guard = _require_login()
    if guard:
        return guard

    query = request.args.get("q", "").strip()
    only_active = request.args.get("active") == "1"
    contractor_id = request.args.get("contractor_id", type=int)
    contract_type_id = request.args.get("contract_type_id", type=int)
    area_id = request.args.get("area_id", type=int)
    status = request.args.get("status") or None

    if query:
        projects = ProjectService.search(query, only_active=only_active)
    else:
        projects = ProjectService.list_projects(
            only_active=only_active,
            contractor_id=contractor_id,
            contract_type_id=contract_type_id,
            area_id=area_id,
            status=status,
        )

    stats = ProjectService.get_statistics()
    choices = ProjectService.get_form_choices()

    return render_template(
        "projects/list.html",
        projects=projects,
        stats=stats,
        total=len(projects),
        query=query,
        only_active=only_active,
        contractor_id=contractor_id,
        contract_type_id=contract_type_id,
        area_id=area_id,
        status=status,
        contractors=choices["contractors"],
        contract_types=choices["contract_types"],
        areas=choices["areas"],
    )


# ================================================================
# مشاهده جزئیات + تیم
# ================================================================
@projects_bp.route("/view/<int:project_id>", methods=["GET"])
def view_project(project_id):
    guard = _require_login()
    if guard:
        return guard

    project = ProjectService.get(project_id)
    if not project:
        flash("پروژه یافت نشد", "danger")
        return redirect(url_for("projects.list_projects"))

    members = ProjectMemberService.list_members(project_id)
    all_roles = ProjectRoleService.list_all(only_active=True)
    all_users = get_all_users_for_select()

    return render_template(
        "projects/view.html",
        project=project,
        members=members,
        all_roles=all_roles,
        all_users=all_users,
    )


# ================================================================
# افزودن
# ================================================================
@projects_bp.route("/add", methods=["GET", "POST"])
def add_project():
    guard = _require_login()
    if guard:
        return guard

    if request.method == "POST":
        data = _extract_form_data(request.form)
        result = ProjectService.create(
            data, created_by=session.get("user_id")
        )

        if result["success"]:
            flash("پروژه با موفقیت ایجاد شد", "success")
            return redirect(url_for(
                "projects.view_project",
                project_id=result["id"]
            ))

        for field, msg in result.get("errors", {}).items():
            flash(f"{field}: {msg}", "danger")

        return render_template(
            "projects/form.html",
            mode="add",
            project=data,
            form=ProjectForm,
            **ProjectService.get_form_choices(),
        )

    return render_template(
        "projects/form.html",
        mode="add",
        project={},
        form=ProjectForm,
        **ProjectService.get_form_choices(),
    )


# ================================================================
# ویرایش
# ================================================================
@projects_bp.route("/edit/<int:project_id>", methods=["GET", "POST"])
def edit_project(project_id):
    guard = _require_login()
    if guard:
        return guard

    project = ProjectService.get(project_id)
    if not project:
        flash("پروژه یافت نشد", "danger")
        return redirect(url_for("projects.list_projects"))

    if request.method == "POST":
        data = _extract_form_data(request.form)
        result = ProjectService.update(project_id, data)

        if result["success"]:
            flash("پروژه با موفقیت به‌روزرسانی شد", "success")
            return redirect(url_for(
                "projects.view_project",
                project_id=project_id
            ))

        for field, msg in result.get("errors", {}).items():
            flash(f"{field}: {msg}", "danger")

        return render_template(
            "projects/form.html",
            mode="edit",
            project=data,
            project_id=project_id,
            form=ProjectForm,
            **ProjectService.get_form_choices(),
        )

    return render_template(
        "projects/form.html",
        mode="edit",
        project=project,
        project_id=project_id,
        form=ProjectForm,
        **ProjectService.get_form_choices(),
    )


# ================================================================
# حذف
# ================================================================
@projects_bp.route("/delete/<int:project_id>", methods=["POST"])
def delete_project(project_id):
    guard = _require_login()
    if guard:
        return guard

    result = ProjectService.delete(project_id)
    if result["success"]:
        flash("پروژه حذف شد", "success")
    else:
        for msg in result.get("errors", {}).values():
            flash(msg, "danger")

    return redirect(url_for("projects.list_projects"))


# ================================================================
# تغییر وضعیت
# ================================================================
@projects_bp.route("/toggle/<int:project_id>", methods=["POST"])
def toggle_project(project_id):
    guard = _require_login()
    if guard:
        return guard

    result = ProjectService.toggle_active(project_id)
    if result["success"]:
        status = "فعال" if result["is_active"] else "غیرفعال"
        flash(f"وضعیت به «{status}» تغییر یافت", "success")
    else:
        flash("خطا در تغییر وضعیت", "danger")

    return redirect(url_for("projects.list_projects"))


# ================================================================
# ★ Excel — Export
# ================================================================
@projects_bp.route("/export", methods=["GET"])
def export_excel():
    guard = _require_login()
    if guard:
        return guard

    # فیلترهای اختیاری
    filters = {
        "only_active": request.args.get("active") == "1",
        "contractor_id": request.args.get("contractor_id", type=int),
        "contract_type_id": request.args.get("contract_type_id", type=int),
        "area_id": request.args.get("area_id", type=int),
        "status": request.args.get("status") or None,
    }

    result = ProjectService.export_excel(**filters)
    if not result["success"]:
        flash("خطا در خروجی اکسل", "danger")
        return redirect(url_for("projects.list_projects"))

    file_path = result["path"]
    if not os.path.exists(file_path):
        flash("فایل خروجی یافت نشد", "danger")
        return redirect(url_for("projects.list_projects"))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    download_name = f"projects_{timestamp}.xlsx"

    return send_file(
        file_path,
        as_attachment=True,
        download_name=download_name,
        mimetype=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
    )


# ================================================================
# ★ Excel — دانلود قالب
# ================================================================
@projects_bp.route("/template", methods=["GET"])
def download_template():
    guard = _require_login()
    if guard:
        return guard

    result = ProjectService.download_template()
    if not result["success"]:
        flash("خطا در ساخت قالب", "danger")
        return redirect(url_for("projects.list_projects"))

    return send_file(
        result["path"],
        as_attachment=True,
        download_name="projects_template.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
    )


# ================================================================
# ★ Excel — Import
# ================================================================
@projects_bp.route("/import", methods=["POST"])
def import_excel():
    guard = _require_login()
    if guard:
        return guard

    if "file" not in request.files:
        flash("فایلی انتخاب نشده", "danger")
        return redirect(url_for("projects.list_projects"))

    file = request.files["file"]
    if not file or file.filename == "":
        flash("فایلی انتخاب نشده", "danger")
        return redirect(url_for("projects.list_projects"))

    if not _allowed_file(file.filename):
        flash("فقط فایل‌های xlsx و xls مجاز هستند", "danger")
        return redirect(url_for("projects.list_projects"))

    # ---- ذخیره موقت ----
    upload_dir = os.path.join(
        "static", "uploads", "projects", "temp"
    )
    os.makedirs(upload_dir, exist_ok=True)

    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_name = f"{timestamp}_{filename}"
    file_path = os.path.join(upload_dir, saved_name)
    file.save(file_path)

    # ---- Import ----
    update_existing = request.form.get("update_existing") == "1"
    result = ProjectService.import_excel(
        file_path, update_existing=update_existing
    )

    # ---- پاک کردن فایل موقت ----
    try:
        os.remove(file_path)
    except Exception:
        pass

    # ---- نمایش نتیجه ----
    if result.get("success"):
        parts = []
        if result["inserted"]:
            parts.append(f"{result['inserted']} ایجاد")
        if result["updated"]:
            parts.append(f"{result['updated']} به‌روزرسانی")
        if result["skipped"]:
            parts.append(f"{result['skipped']} رد شده")

        msg = "، ".join(parts) if parts else "تغییری اعمال نشد"
        flash(f"نتیجه import: {msg}", "success")

        if result.get("errors"):
            for err in result["errors"][:5]:
                flash(err, "warning")
    else:
        for err in result.get("errors", []):
            flash(err, "danger")

    return redirect(url_for("projects.list_projects"))


# ================================================================
# مدیریت اعضای تیم
# ================================================================
@projects_bp.route("/<int:project_id>/members/add", methods=["POST"])
def add_member(project_id):
    guard = _require_login()
    if guard:
        return guard

    data = {
        "user_id": request.form.get("user_id", type=int),
        "role_id": request.form.get("role_id", type=int),
        "responsibility": request.form.get("responsibility", "").strip(),
        "notes": request.form.get("notes", "").strip(),
    }

    if not data["user_id"] or not data["role_id"]:
        flash("کاربر و نقش الزامی هستند", "danger")
        return redirect(url_for(
            "projects.view_project", project_id=project_id
        ))

    result = ProjectMemberService.add_member(
        project_id=project_id,
        user_id=data["user_id"],
        role_id=data["role_id"],
        responsibility=data["responsibility"] or None,
        notes=data["notes"] or None,
        assigned_by=session.get("user_id"),
    )

    if result["success"]:
        flash("عضو با موفقیت اضافه شد", "success")
    else:
        for msg in result.get("errors", {}).values():
            flash(msg, "danger")

    return redirect(url_for(
        "projects.view_project", project_id=project_id
    ))


@projects_bp.route("/members/<int:member_id>/remove", methods=["POST"])
def remove_member(member_id):
    guard = _require_login()
    if guard:
        return guard

    project_id = request.form.get("project_id", type=int)
    result = ProjectMemberService.remove_member(member_id)

    if result["success"]:
        flash("عضو حذف شد", "success")
    else:
        flash("خطا در حذف عضو", "danger")

    return redirect(url_for(
        "projects.view_project", project_id=project_id
    ))


@projects_bp.route("/members/<int:member_id>/update", methods=["POST"])
def update_member(member_id):
    guard = _require_login()
    if guard:
        return guard

    project_id = request.form.get("project_id", type=int)
    data = {
        "responsibility": request.form.get("responsibility", "").strip(),
        "notes": request.form.get("notes", "").strip(),
    }

    result = ProjectMemberService.update_member(member_id, data)
    if result["success"]:
        flash("اطلاعات عضو به‌روزرسانی شد", "success")
    else:
        flash("خطا در به‌روزرسانی", "danger")

    return redirect(url_for(
        "projects.view_project", project_id=project_id
    ))


@projects_bp.route("/<int:project_id>/members.json", methods=["GET"])
def members_json(project_id):
    guard = _require_login()
    if guard:
        return jsonify({"success": False}), 401

    members = ProjectMemberService.list_members(project_id)
    return jsonify({"success": True, "members": members})


# ================================================================
# استخراج داده‌های فرم
# ================================================================
def _extract_form_data(form):
    data = {}

    # فیلدهای متنی
    text_fields = [
        "name", "code", "project_number", "description",
        "contract_number",
        "contract_number_foreign",
        "currency",
        "contract_start_date", "contract_end_date",
        "start_date", "planned_end_date", "actual_end_date",
        "status", "priority",
        "location", "province", "city", "tags", "notes",
    ]
    for f in text_fields:
        data[f] = (form.get(f) or "").strip() or None

    # فیلدهای عددی اعشاری
    numeric_fields = [
        "contract_amount", "contract_amount_foreign",
        "budget", "latitude", "longitude",
    ]
    for f in numeric_fields:
        v = form.get(f, "").strip()
        data[f] = v if v else None

    # فیلدهای عددی صحیح
    int_fields = [
        "contractor_id", "contract_type_id", "area_id",
        "duration_days",
        "progress_percent", "physical_progress", "time_progress",
        "financial_progress_rial", "financial_progress_foreign",
        "sort_order",
    ]
    for f in int_fields:
        v = form.get(f, "").strip()
        data[f] = v if v else None

    # is_active
    data["is_active"] = 1 if form.get("is_active") else 0

    # currency پیش‌فرض
    if not data.get("currency"):
        data["currency"] = "USD"

    return data