from flask import render_template, redirect, url_for, flash, request, abort
from . import departments_bp
from services.departments.department_service import DepartmentService
from services.users.user_service import UserService
from security.decorators import role_required, login_required


@departments_bp.route("/")
@role_required("admin", "manager")
def department_list():
    departments = DepartmentService.get_all()
    return render_template(
        "departments/list.html",
        departments=departments
    )


@departments_bp.route("/add", methods=["GET", "POST"])
@role_required("admin")
def add_department():
    supervisors = DepartmentService.get_supervisors()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        code = request.form.get("code", "").strip()
        sort_order = request.form.get("sort_order", 0, type=int)
        supervisor_id = request.form.get("supervisor_id", type=int)
        is_active = 1 if request.form.get("is_active") else 0

        if not title:
            flash("عنوان دپارتمان الزامی است", "danger")
            return render_template(
                "departments/form.html",
                department=None,
                supervisors=supervisors
            )

        success, message = DepartmentService.create(
            title=title,
            code=code,
            sort_order=sort_order,
            supervisor_id=supervisor_id,
            is_active=is_active
        )
        flash(message, "success" if success else "danger")

        if success:
            return redirect(url_for("departments.department_list"))

    return render_template(
        "departments/form.html",
        department=None,
        supervisors=supervisors
    )


@departments_bp.route("/edit/<int:department_id>", methods=["GET", "POST"])
@role_required("admin")
def edit_department(department_id):
    department = DepartmentService.get_by_id(department_id)

    if not department:
        flash("دپارتمان پیدا نشد", "danger")
        return redirect(url_for("departments.department_list"))

    supervisors = DepartmentService.get_supervisors()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        code = request.form.get("code", "").strip()
        sort_order = request.form.get("sort_order", 0, type=int)
        supervisor_id = request.form.get("supervisor_id", type=int)
        is_active = 1 if request.form.get("is_active") else 0

        if not title:
            flash("عنوان دپارتمان الزامی است", "danger")
            return render_template(
                "departments/form.html",
                department=department,
                supervisors=supervisors
            )

        success, message = DepartmentService.update(
            department_id=department_id,
            title=title,
            code=code,
            sort_order=sort_order,
            supervisor_id=supervisor_id,
            is_active=is_active
        )
        flash(message, "success" if success else "danger")

        if success:
            return redirect(url_for("departments.department_list"))

    return render_template(
        "departments/form.html",
        department=department,
        supervisors=supervisors
    )


@departments_bp.route("/delete/<int:department_id>", methods=["POST"])
@role_required("admin")
def delete_department(department_id):
    success, message = DepartmentService.delete(department_id)
    flash(message, "success" if success else "danger")
    return redirect(url_for("departments.department_list"))


# ============================================================
# ★ VIEW DEPARTMENT (با فیلتر سال + ماه شمسی)
# ============================================================

@departments_bp.route("/view/<int:department_id>", methods=["GET"])
@login_required
def view_department(department_id):
    # ★ ۱) گرفتن سال و ماه از URL
    year = request.args.get("year", "all")
    month = request.args.get("month", "all")

    # ★ ۲) اعتبارسنجی سال → گرفتن لیست سال‌ها
    selected_year, available_years = DepartmentService.normalize_year(
        department_id,
        year
    )

    # ★ ۳) اعتبارسنجی ماه بر اساس سال انتخاب‌شده
    selected_month, available_months = DepartmentService.normalize_month(
        department_id,
        month,
        selected_year=selected_year
    )

    # ★ ۴) تبدیل به لیست بازه‌های میلادی
    #    (پشتیبانی از حالت «همه سال‌ها + ماه مشخص»)
    date_ranges = DepartmentService.get_date_ranges(
        selected_year,
        selected_month,
        available_years=available_years
    )

    # ★ ۵) گرفتن دپارتمان
    department = DepartmentService.get_by_id(
        department_id,
        date_ranges=date_ranges
    )
    if not department:
        abort(404)

    # ★ ۶) کارشناسان
    experts = DepartmentService.get_department_experts(
        department_id,
        date_ranges=date_ranges
    )

    # ★ محاسبه is_online + شمارش فعال/غیرفعال
    experts_list = []
    active_count = 0
    inactive_count = 0

    for expert in experts:
        expert_dict = dict(expert)
        try:
            expert_dict["is_online"] = UserService.is_online(expert_dict["id"])
        except Exception:
            expert_dict["is_online"] = False

        if expert_dict.get("is_active"):
            active_count += 1
        else:
            inactive_count += 1

        experts_list.append(expert_dict)

    experts_list.sort(key=lambda e: 0 if e.get("is_online") else 1)

    return render_template(
        "departments/view.html",
        department=department,
        experts=experts_list,
        selected_year=selected_year,
        selected_month=selected_month,
        available_years=available_years,
        available_months=available_months,
        active_count=active_count,
        inactive_count=inactive_count,
    )


@departments_bp.route("/expert/<int:department_id>/<int:expert_id>/breakdown", methods=["GET"])
@login_required
def expert_breakdown(department_id, expert_id):
    """★ صفحه تفکیک کارهای کارشناس بر اساس گروه و زیرگروه سند"""
    year = request.args.get("year", "all")
    month = request.args.get("month", "all")

    selected_year, available_years = DepartmentService.normalize_year(
        department_id, year
    )
    selected_month, available_months = DepartmentService.normalize_month(
        department_id, month, selected_year=selected_year
    )

    date_ranges = DepartmentService.get_date_ranges(
        selected_year, selected_month, available_years=available_years
    )

    expert = UserService.get_by_id(expert_id)
    if not expert:
        abort(404)
    if not isinstance(expert, dict):
        expert = dict(expert)

    department = DepartmentService.get_by_id(
        department_id, date_ranges=date_ranges
    )
    if not department:
        abort(404)

    breakdown_data = DepartmentService.get_expert_breakdown(
        expert_id=expert_id,
        department_id=department_id,
        date_ranges=date_ranges
    )

    return render_template(
        "departments/expert_breakdown.html",
        department=department,
        expert=expert,
        breakdown_data=breakdown_data,
        selected_year=selected_year,
        selected_month=selected_month,
        available_years=available_years,
        available_months=available_months,
    )