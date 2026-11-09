from flask import render_template, request, jsonify
from . import reports_bp
from services.departments.department_expert_documents_service import (
    DepartmentExpertDocumentsService
)


# ============================================================
# ★ روت اصلی — فقط متادیتا (سریع، بدون لیست اسناد)
# ============================================================
@reports_bp.route(
    "/department/<int:department_id>/expert/<int:expert_id>",
    methods=["GET"]
)
def department_expert_documents(department_id, expert_id):
    year = request.args.get("year", "all")
    area_id = request.args.get("area_id")

    try:
        area_id = (
            int(area_id)
            if area_id not in (None, "", "all")
            else None
        )
    except (ValueError, TypeError):
        area_id = None

    # ★ فقط متادیتا — بدون لیست اسناد
    data = DepartmentExpertDocumentsService.get_documents_meta(
        department_id=department_id,
        expert_id=expert_id,
        requested_year=year,
        area_id=area_id
    )

    if not data:
        return "کارشناس یا دپارتمان مورد نظر پیدا نشد", 404

    return render_template(
        "reports/department_expert_documents.html",
        **data
    )


# ============================================================
# ★ روت JSON — برای AJAX (لیست اسناد با فیلتر وضعیت + صفحه‌بندی)
# ============================================================
@reports_bp.route(
    "/department/<int:department_id>/expert/<int:expert_id>/documents.json",
    methods=["GET"]
)
def department_expert_documents_json(department_id, expert_id):
    year = request.args.get("year", "all")
    search = request.args.get("search", "")
    page = request.args.get("page", 1, type=int)
    status_code = request.args.get("status") or None
    area_id = request.args.get("area_id")

    try:
        area_id = (
            int(area_id)
            if area_id not in (None, "", "all")
            else None
        )
    except (ValueError, TypeError):
        area_id = None

    data = DepartmentExpertDocumentsService.get_documents_json(
        department_id=department_id,
        expert_id=expert_id,
        requested_year=year,
        search=search,
        page=page,
        area_id=area_id,
        status_code=status_code
    )

    return jsonify(data)