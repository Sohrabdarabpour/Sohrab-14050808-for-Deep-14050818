from flask import render_template,request
from security.decorators import role_required
from routes.reports import reports_bp
from services.departments.department_report_service import DepartmentReportService
@reports_bp.route("/department")
@role_required("admin","manager","supervisor")
def department_report():
    requested_year=request.args.get(
        "year",
        "all"
    )
    data=DepartmentReportService.get_report_data(
        requested_year=requested_year
    )
    return render_template(
        "reports/department.html",
        departments=data["departments"],
        total=data["total"],
        available_years=data["available_years"],
        selected_year=data["selected_year"]
    )