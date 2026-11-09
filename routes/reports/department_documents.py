from flask import render_template,request
from security.decorators import role_required
from routes.reports import reports_bp
from services.departments.department_documents_service import DepartmentDocumentsService

@reports_bp.route("/department/<int:department_id>")
@role_required("admin","manager","supervisor")
def department_documents(department_id):
    requested_year=request.args.get("year","all")
    search=request.args.get("search","").strip()
    page=request.args.get("page",1)

    area_id=request.args.get("area_id")

    try:
        area_id=int(area_id) if area_id not in (None,"","all") else None
    except (ValueError,TypeError):
        area_id=None

    data=DepartmentDocumentsService.get_documents(
        department_id=department_id,
        requested_year=requested_year,
        search=search,
        page=page,
        area_id=area_id
    )

    if not data:
        return render_template(
            "reports/department_documents.html",
            department=None,
            experts=[],
            documents=[],
            total=0,
            page=1,
            page_size=30,
            total_pages=1,
            available_years=[],
            selected_year="all",
            search="",
            area_id=area_id
        ),404

    return render_template(
        "reports/department_documents.html",
        department=data["department"],
        experts=data["experts"],
        documents=data["documents"],
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
        total_pages=data["total_pages"],
        available_years=data["available_years"],
        selected_year=data["selected_year"],
        search=data["search"],
        area_id=data["area_id"]
    )