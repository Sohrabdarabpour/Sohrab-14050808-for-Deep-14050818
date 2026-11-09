from flask import render_template, request
from . import reports_bp
from services.reports.area_departments_service import AreaDepartmentsService

@reports_bp.route("/area/<int:area_id>", methods=["GET"])
def area_departments(area_id):
    year=request.args.get("year","all")
    data=AreaDepartmentsService.get_report(
        area_id=area_id,
        requested_year=year
    )
    if not data:
        return "ناحیه مورد نظر پیدا نشد",404
    return render_template("reports/area_departments.html",**data)