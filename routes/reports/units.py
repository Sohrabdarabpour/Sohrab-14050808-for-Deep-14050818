from flask import render_template
from routes.reports import reports_bp
from database.reports import get_unit_report
from security.decorators import login_required
@reports_bp.route("/units")
@login_required
def units_report():
    units = get_unit_report()
    return render_template(
        "reports/unit_report.html",
        units=units
    )