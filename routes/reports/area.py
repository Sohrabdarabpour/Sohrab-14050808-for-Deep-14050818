from flask import render_template, request
from . import reports_bp
from services.reports.area_report_service import AreaReportService


@reports_bp.route("/area", methods=["GET"])
def area_report():
    year = request.args.get(
        "year",
        "all"
    )

    data = AreaReportService.get_report(
        requested_year=year
    )

    return render_template(
        "reports/area.html",
        **data
    )