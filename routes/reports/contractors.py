from flask import render_template
from routes.reports import reports_bp
from database.reports import get_contractor_report
from security.decorators import login_required
@reports_bp.route("/contractors")
@login_required
def contractors_report():
    contractors = get_contractor_report()
    return render_template(
        "reports/contractor_report.html",
        contractors=contractors
    )