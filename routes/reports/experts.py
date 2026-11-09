from flask import render_template
from routes.reports import reports_bp
from database.reports import get_expert_report
from security.decorators import login_required
@reports_bp.route("/experts")
@login_required
def experts_report():
    experts = get_expert_report()
    return render_template(
        "reports/expert_report.html",
        experts=experts
    )