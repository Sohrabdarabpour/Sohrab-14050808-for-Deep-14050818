from flask import render_template,request
from security.decorators import role_required
from routes.reports import reports_bp
from services.reports.status_report_service import StatusReportService
@reports_bp.route("/status")
@role_required("admin","manager")
def status_report():
    requested_year=request.args.get("year","all")
    data=StatusReportService.get_report_data(
        requested_year=requested_year
    )
    return render_template(
        "reports/status.html",
        statuses=data["statuses"],
        total=data["total"],
        available_years=data["available_years"],
        selected_year=data["selected_year"]
    )