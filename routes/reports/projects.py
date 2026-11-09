from flask import render_template
from routes.reports import reports_bp
from database.reports import get_project_report
from security.decorators import login_required
@reports_bp.route("/projects")
@login_required
def projects_report():
    projects = get_project_report()
    return render_template(
        "reports/project_report.html",
        projects=projects
    )