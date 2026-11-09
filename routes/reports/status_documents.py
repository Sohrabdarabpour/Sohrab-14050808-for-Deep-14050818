from flask import render_template,request
from security.decorators import role_required
from routes.reports import reports_bp
from services.reports.status_documents_service import StatusDocumentsService
@reports_bp.route("/status/<status_code>")
@role_required("admin","manager","supervisor")
def status_documents(status_code):
    requested_year=request.args.get("year","all")
    search=request.args.get("search","").strip()
    page=request.args.get("page",1)
    data=StatusDocumentsService.get_documents(
        status_code=status_code,
        requested_year=requested_year,
        search=search,
        page=page
    )
    if not data:
        return render_template(
            "reports/status_documents.html",
            status=None,
            documents=[],
            total=0,
            page=1,
            page_size=30,
            total_pages=1,
            available_years=[],
            selected_year="all",
            search=""
        ),404
    return render_template(
        "reports/status_documents.html",
        status=data["status"],
        documents=data["documents"],
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
        total_pages=data["total_pages"],
        available_years=data["available_years"],
        selected_year=data["selected_year"],
        search=data["search"]
    )