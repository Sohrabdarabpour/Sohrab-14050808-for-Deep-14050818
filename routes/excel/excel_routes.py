import os
from flask import (
    Blueprint,
    render_template,
    send_file,
    request,
    redirect,
    url_for,
    flash
)
from config import Config
from services.excel.excel_service import ExcelService
from security.decorators import login_required, role_required

excel_bp = Blueprint(
    "excel",
    __name__,
    url_prefix="/excel"
)

@excel_bp.route("/")
@login_required
@role_required("admin", "manager")
def index():
    document_count = ExcelService.get_document_count()
    return render_template(
        "excel/import.html",
        document_count=document_count
    )

@excel_bp.route("/export")
@login_required
def export_excel():
    output = ExcelService.export_template()
    return send_file(
        output,
        as_attachment=True,
        download_name="SSPE_Document_Template.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )

@excel_bp.route("/import", methods=["POST"])
@login_required
def import_excel():
    file = request.files.get("file")
    mode = request.form.get("mode", "append")
    if not file or not file.filename:
        flash(
            "لطفاً ابتدا یک فایل Excel انتخاب کنید",
            "danger"
        )
        return redirect(url_for("excel.index"))
    if mode not in ("append", "replace"):
        flash(
            "حالت ورود اطلاعات نامعتبر است",
            "danger"
        )
        return redirect(url_for("excel.index"))
    filename = file.filename
    extension = os.path.splitext(filename)[1].lower()
    allowed_extensions = {".xlsx", ".xls"}
    if extension not in allowed_extensions:
        flash(
            "فرمت فایل مجاز نیست. فقط فایل Excel انتخاب کنید",
            "danger"
        )
        return redirect(url_for("excel.index"))
    os.makedirs(
        Config.UPLOAD_FOLDER,
        exist_ok=True
    )
    temporary_name = f"excel_import{extension}"
    file_path = os.path.join(
        Config.UPLOAD_FOLDER,
        temporary_name
    )
    try:
        file.save(file_path)
        result = ExcelService.import_file(
            file_path,
            mode=mode
        )
        if result["success"]:
            flash(
                result["message"],
                "success"
            )
        else:
            flash(
                result["message"],
                "warning"
            )
        return redirect(url_for("excel.index"))
    except Exception as error:
        flash(
            f"خطا در ورود فایل: {error}",
            "danger"
        )
        return redirect(url_for("excel.index"))
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass



@excel_bp.route("/export-data")
@login_required
@role_required("admin", "manager")
def export_data():
    """خروجی اکسل از داده‌های موجود"""
    import os
    from datetime import datetime

    # ---- فیلترها ----
    filters = {
        "year": request.args.get("year", "all"),
        "status_id": request.args.get("status_id", type=int),
        "area_id": request.args.get("area_id", type=int),
        "department_id": request.args.get("department_id", type=int),
        "user_id": request.args.get("user_id", type=int),
        "contractor_id": request.args.get("contractor_id", type=int),
        "project_id": request.args.get("project_id", type=int),
    }

    # ---- Export ----
    try:
        file_path = ExcelService.export_data(filters=filters)
    except Exception as e:
        flash(f"خطا در خروجی اکسل: {e}", "danger")
        return redirect(url_for("excel.index"))

    if not os.path.exists(file_path):
        flash("فایل خروجی یافت نشد", "danger")
        return redirect(url_for("excel.index"))

    # ---- نام فایل دانلودی ----
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    download_name = f"documents_{timestamp}.xlsx"

    return send_file(
        file_path,
        as_attachment=True,
        download_name=download_name,
        mimetype=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
    )
