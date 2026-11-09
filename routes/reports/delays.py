from flask import render_template
from routes.reports import reports_bp
from database.reports import get_delay_report
from security.decorators import login_required
@reports_bp.route("/delays")
@login_required
def delays_report():
    delays = get_delay_report()
    return render_template(
        "reports/delay_report.html",
        delays=delays
    )