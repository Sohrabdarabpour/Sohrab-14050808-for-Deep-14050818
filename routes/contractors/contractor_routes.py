import os
from datetime import datetime
from flask import (
    render_template, request, redirect, url_for,
    flash, session, send_file
)
from werkzeug.utils import secure_filename

from . import contractor_bp
from services.contractors import ContractorService
from forms.contractors import ContractorForm


# ================================================================
# ★ تنظیمات آپلود
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
# لیست پیمانکاران (کارتی — بدون نمودار)
# ================================================================
@contractor_bp.route("/", methods=["GET"])
def list_contractors():
    guard = _require_login()
    if guard:
        return guard

    query = request.args.get("q", "").strip()
    only_active = request.args.get("active") == "1"

    if query:
        contractors = ContractorService.search(
            query, only_active=only_active
        )
    else:
        contractors = ContractorService.list_contractors(
            only_active=only_active
        )

    stats = ContractorService.get_statistics()

    return render_template(
        "contractors/list.html",
        contractors=contractors,
        total=len(contractors),
        stats=stats,
        query=query,
        only_active=only_active,
    )


# ================================================================
# مشاهده جزئیات
# ================================================================
@contractor_bp.route("/view/<int:contractor_id>", methods=["GET"])
def view_contractor(contractor_id):
    guard = _require_login()
    if guard:
        return guard

    contractor = ContractorService.get(contractor_id)
    if not contractor:
        flash("پیمانکار یافت نشد", "danger")
        return redirect(url_for("contractors.list_contractors"))

    return render_template(
        "contractors/view.html",
        contractor=contractor,
    )


# ================================================================
# افزودن
# ================================================================
@contractor_bp.route("/add", methods=["GET", "POST"])
def add_contractor():
    guard = _require_login()
    if guard:
        return guard

    if request.method == "POST":
        data = _extract_form_data(request.form)
        result = ContractorService.create(data)

        if result["success"]:
            flash("پیمانکار با موفقیت ایجاد شد", "success")
            return redirect(url_for("contractors.list_contractors"))

        for field, msg in result.get("errors", {}).items():
            flash(f"{field}: {msg}", "danger")

        return render_template(
            "contractors/form.html",
            mode="add",
            contractor=data,
            form=ContractorForm,
        )

    return render_template(
        "contractors/form.html",
        mode="add",
        contractor=ContractorForm.empty_data(),
        form=ContractorForm,
    )


# ================================================================
# ویرایش
# ================================================================
@contractor_bp.route(
    "/edit/<int:contractor_id>", methods=["GET", "POST"]
)
def edit_contractor(contractor_id):
    guard = _require_login()
    if guard:
        return guard

    contractor = ContractorService.get(contractor_id)
    if not contractor:
        flash("پیمانکار یافت نشد", "danger")
        return redirect(url_for("contractors.list_contractors"))

    if request.method == "POST":
        data = _extract_form_data(request.form)
        result = ContractorService.update(contractor_id, data)

        if result["success"]:
            flash("پیمانکار با موفقیت به‌روزرسانی شد", "success")
            return redirect(url_for(
                "contractors.view_contractor",
                contractor_id=contractor_id
            ))

        for field, msg in result.get("errors", {}).items():
            flash(f"{field}: {msg}", "danger")

        return render_template(
            "contractors/form.html",
            mode="edit",
            contractor=data,
            contractor_id=contractor_id,
            form=ContractorForm,
        )

    return render_template(
        "contractors/form.html",
        mode="edit",
        contractor=ContractorForm.from_model(contractor),
        contractor_id=contractor_id,
        form=ContractorForm,
    )


# ================================================================
# حذف
# ================================================================
@contractor_bp.route(
    "/delete/<int:contractor_id>", methods=["POST"]
)
def delete_contractor(contractor_id):
    guard = _require_login()
    if guard:
        return guard

    result = ContractorService.delete(contractor_id)
    if result["success"]:
        flash("پیمانکار حذف شد", "success")
    else:
        flash("خطا در حذف پیمانکار", "danger")

    return redirect(url_for("contractors.list_contractors"))


# ================================================================
# ★ تغییر وضعیت
# ================================================================
@contractor_bp.route(
    "/toggle/<int:contractor_id>", methods=["POST"]
)
def toggle_contractor(contractor_id):
    guard = _require_login()
    if guard:
        return guard

    result = ContractorService.toggle_active(contractor_id)
    if result["success"]:
        status = "فعال" if result["is_active"] else "غیرفعال"
        flash(f"وضعیت پیمانکار به «{status}» تغییر یافت", "success")
    else:
        flash("خطا در تغییر وضعیت", "danger")

    return redirect(url_for("contractors.list_contractors"))


# ================================================================
# ★ Export اکسل
# ================================================================
@contractor_bp.route("/export", methods=["GET"])
def export_excel():
    guard = _require_login()
    if guard:
        return guard

    result = ContractorService.export_excel()
    if not result["success"]:
        flash("خطا در خروجی اکسل", "danger")
        return redirect(url_for("contractors.list_contractors"))

    file_path = result["path"]
    if not os.path.exists(file_path):
        flash("فایل خروجی یافت نشد", "danger")
        return redirect(url_for("contractors.list_contractors"))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    download_name = f"contractors_{timestamp}.xlsx"

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
# ★ دانلود قالب
# ================================================================
@contractor_bp.route("/template", methods=["GET"])
def download_template():
    guard = _require_login()
    if guard:
        return guard

    result = ContractorService.download_template()
    if not result["success"]:
        flash("خطا در ساخت قالب", "danger")
        return redirect(url_for("contractors.list_contractors"))

    return send_file(
        result["path"],
        as_attachment=True,
        download_name="contractors_template.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
    )


# ================================================================
# ★ Import اکسل
# ================================================================
@contractor_bp.route("/import", methods=["POST"])
def import_excel():
    guard = _require_login()
    if guard:
        return guard

    if "file" not in request.files:
        flash("فایلی انتخاب نشده", "danger")
        return redirect(url_for("contractors.list_contractors"))

    file = request.files["file"]
    if not file or file.filename == "":
        flash("فایلی انتخاب نشده", "danger")
        return redirect(url_for("contractors.list_contractors"))

    if not _allowed_file(file.filename):
        flash("فقط فایل‌های xlsx و xls مجاز هستند", "danger")
        return redirect(url_for("contractors.list_contractors"))

    # ---- ذخیره موقت ----
    upload_dir = os.path.join(
        "static", "uploads", "contractors", "temp"
    )
    os.makedirs(upload_dir, exist_ok=True)

    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_name = f"{timestamp}_{filename}"
    file_path = os.path.join(upload_dir, saved_name)
    file.save(file_path)

    # ---- Import ----
    update_existing = request.form.get("update_existing") == "1"
    result = ContractorService.import_excel(
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

    return redirect(url_for("contractors.list_contractors"))


# ================================================================
# ★ استخراج داده‌های فرم
# ================================================================
def _extract_form_data(form):
    data = {}
    for f in ContractorForm.get_fields():
        name = f["name"]
        if f.get("type") == "checkbox":
            data[name] = 1 if form.get(name) else 0
        else:
            value = form.get(name, "").strip()
            data[name] = value if value else None
    data["name"] = (form.get("name") or "").strip()
    return data