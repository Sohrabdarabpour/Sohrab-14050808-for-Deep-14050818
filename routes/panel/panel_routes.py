import os
import tempfile

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify, send_file
)

from forms.users.forms import UserForm, UserRoleForm
from services.users.user_service import UserService
from services.users.user_excel_service import UserExcelService
from services.departments.department_service import DepartmentService
from security.decorators import login_required, role_required
from helpers.date_helper import DateHelper

panel_bp = Blueprint("panel", __name__, url_prefix="/panel")


def set_department_choices(form):
    departments = DepartmentService.get_all()
    form.department_id.choices = [(0, "بدون دپارتمان")] + [
        (d["id"], d["title"]) for d in departments
    ]
    return departments


@panel_bp.route("/")
@login_required
def panel():
    return redirect(url_for("panel.users"))


# ============================================================
# لیست کاربران
# ============================================================
@panel_bp.route("/users")
@role_required("admin", "manager")
def users():
    users_list = UserService.get_all()
    users_list = [dict(u) for u in users_list]

    for u in users_list:
        u["last_login_jalali"] = DateHelper.format_jalali_datetime(
            u.get("last_login")
        )
        u["last_seen_jalali"] = DateHelper.format_jalali_datetime(
            u.get("last_seen")
        )

        # ★ اضافه کردن وضعیت آنلاین به هر کاربر
        try:
            u["is_online"] = UserService.is_online(u["id"])
        except Exception:
            u["is_online"] = False

    # مرتب‌سازی: آنلاین‌ها اول
    users_list.sort(
        key=lambda u: 0 if u.get("is_online") else 1
    )

    return render_template(
        "panel/users.html",
        users=users_list
    )
# ============================================================
# وضعیت آنلاین کاربران
# ============================================================
@panel_bp.route("/users/online-status")
@role_required("admin", "manager")
def users_online_status():
    all_users = UserService.get_all()
    result = {}

    for u in all_users:
        try:
            result[str(u["id"])] = UserService.is_online(u["id"])
        except Exception:
            result[str(u["id"])] = False

    return jsonify(result)


# ============================================================
# افزودن کاربر
# ============================================================
@panel_bp.route("/users/add", methods=["GET", "POST"])
@role_required("admin", "manager")
def add_user():
    form = UserForm()
    departments = set_department_choices(form)

    if form.validate_on_submit():
        if not form.password.data:
            flash("رمز عبور الزامی است", "danger")
            return render_template(
                "panel/add_user.html",
                form=form,
                departments=departments
            )

        department_id = form.department_id.data or None

        success = UserService.create(
            username=form.username.data,
            password=form.password.data,
            full_name=form.full_name.data,
            role=form.role.data,
            department_id=department_id,
            gender=form.gender.data,
            is_active=1 if form.is_active.data else 0,
            # ★ avatar پاس داده نمی‌شود → سرویس بر اساس جنسیت تعیین می‌کند
        )

        if success:
            flash("کاربر با موفقیت ایجاد شد", "success")
            return redirect(url_for("panel.users"))

        flash("نام کاربری تکراری است", "danger")

    return render_template(
        "panel/add_user.html",
        form=form,
        departments=departments
    )
# ============================================================
# ویرایش کاربر
# ============================================================
@panel_bp.route("/users/edit/<int:user_id>", methods=["GET", "POST"])
@role_required("admin")
def edit_user(user_id):
    user = UserService.get_by_id(user_id)

    if not user:
        flash("کاربر پیدا نشد", "danger")
        return redirect(url_for("panel.users"))

    # ★ تبدیل به dict برای دسترسی راحت‌تر (user.get(...))
    if not isinstance(user, dict):
        user = dict(user)

    form = UserForm()
    departments = set_department_choices(form)

    if request.method == "GET":
        form.username.data = user["username"]
        form.full_name.data = user["full_name"]
        form.role.data = user["role"]
        form.department_id.data = user["department_id"] or 0

        # ★ مقادیر جدید
        form.gender.data = user.get("gender") or "male"
        form.is_active.data = bool(user.get("is_active", 1))

    if form.validate_on_submit():
        department_id = form.department_id.data or None

        success = UserService.update(
            user_id=user_id,
            username=form.username.data,
            full_name=form.full_name.data,
            role=form.role.data,
            password=form.password.data,
            department_id=department_id,
            gender=form.gender.data,
            is_active=1 if form.is_active.data else 0,
            # ★ avatar پاس داده نمی‌شود → منطق هوشمند سرویس تصمیم می‌گیرد
        )

        if success:
            flash("اطلاعات کاربر اصلاح شد", "success")
            return redirect(url_for("panel.users"))

        flash("ویرایش انجام نشد", "danger")

    return render_template(
        "panel/edit_user.html",
        form=form,
        user=user,
        departments=departments
    )
# ============================================================
# تغییر نقش کاربر
# ============================================================
@panel_bp.route("/users/<int:user_id>/role", methods=["GET", "POST"])
@role_required("admin")
def change_user_role(user_id):
    user = UserService.get_by_id(user_id)

    if not user:
        flash("کاربر پیدا نشد", "danger")
        return redirect(url_for("panel.users"))

    form = UserRoleForm()

    if request.method == "GET":
        form.role.data = user["role"]

    if form.validate_on_submit():
        if UserService.update_role(user_id, form.role.data):
            flash("نقش کاربر تغییر کرد", "success")
            return redirect(url_for("panel.users"))

        flash("تغییر نقش انجام نشد", "danger")

    return render_template(
        "panel/change_user_role.html",
        form=form,
        user=user
    )


# ============================================================
# حذف کاربر
# ============================================================
@panel_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@role_required("admin")
def delete_user(user_id):
    if user_id == 1:
        flash("کاربر اصلی سیستم قابل حذف نیست", "danger")
        return redirect(url_for("panel.users"))

    if UserService.delete(user_id):
        flash("کاربر حذف شد", "success")
    else:
        flash("حذف انجام نشد", "danger")

    return redirect(url_for("panel.users"))


# ============================================================
# جزئیات کاربر
# ============================================================
@panel_bp.route("/users/<int:user_id>")
@role_required("admin", "manager")
def user_detail(user_id):
    user = UserService.get_by_id(user_id)

    if not user:
        flash("کاربر یافت نشد", "danger")
        return redirect(url_for("panel.users"))

    user = dict(user)

    activity = UserService.get_last_login_and_seen(user_id)

    last_login = activity["last_login"] if activity else None
    last_seen = activity["last_seen"] if activity else None

    is_online = UserService.is_online(user_id)

    last_login_jalali = DateHelper.format_jalali_datetime(last_login)
    last_seen_jalali = DateHelper.format_jalali_datetime(last_seen)

    created_at_jalali = DateHelper.format_jalali_datetime(
        user.get("created_at")
    )
    updated_at_jalali = DateHelper.format_jalali_datetime(
        user.get("updated_at")
    )

    return render_template(
        "panel/user_detail.html",
        user=user,
        last_login=last_login_jalali,
        last_seen=last_seen_jalali,
        is_online=is_online,
        created_at_jalali=created_at_jalali,
        updated_at_jalali=updated_at_jalali
    )


# ============================================================
# خروجی اکسل کاربران
# ============================================================
@panel_bp.route("/users/export/excel")
@role_required("admin", "manager")
def users_export_excel():
    output = UserExcelService.export_users()
    filename = UserExcelService.build_export_filename()

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
# دانلود قالب خالی ورود کاربران
# ============================================================
@panel_bp.route("/users/import/template")
@role_required("admin")
def users_import_template():
    output = UserExcelService.export_import_template()

    return send_file(
        output,
        mimetype=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
        as_attachment=True,
        download_name="users_import_template.xlsx"
    )


# ============================================================
# ★★★ ورود کاربران از فایل اکسل ★★★
# ============================================================
@panel_bp.route("/users/import", methods=["POST"])
@role_required("admin")
def users_import_excel():
    """
    آپلود فایل اکسل و ورود داده‌ها به دیتابیس.
    
    منطق:
    - ردیف‌هایی که «شناسه» دارند → بروزرسانی می‌شوند
    - ردیف‌های بدون «شناسه» → کاربر جدید ایجاد می‌کنند
    """
    # ★ بررسی وجود فایل در request
    if "file" not in request.files:
        flash("فایلی انتخاب نشده است", "danger")
        return redirect(url_for("panel.users"))

    file = request.files["file"]

    # ★ بررسی خالی نبودن نام فایل
    if not file.filename:
        flash("فایلی انتخاب نشده است", "danger")
        return redirect(url_for("panel.users"))

    # ★ بررسی فرمت فایل
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        flash("فرمت فایل باید Excel باشد (.xlsx یا .xls)", "danger")
        return redirect(url_for("panel.users"))

    temp_path = None
    try:
        # ★ ذخیره موقت فایل
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".xlsx"
        ) as tmp:
            file.save(tmp.name)
            temp_path = tmp.name

        # ★ پردازش Import
        result = UserExcelService.import_users(temp_path)

        # ★ نمایش نتیجه
        if result.get("success"):
            flash(result.get("message", "ورود با موفقیت انجام شد"), "success")
        else:
            flash(
                result.get("message", "ورود با خطا مواجه شد"),
                "warning"
            )
            # ★ حداکثر ۵ خطا نمایش داده شود
            for err in result.get("errors", [])[:5]:
                flash(err, "danger")

    except Exception as e:
        flash(f"خطا در پردازش فایل: {e}", "danger")

    finally:
        # ★ پاک کردن فایل موقت
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

    return redirect(url_for("panel.users"))