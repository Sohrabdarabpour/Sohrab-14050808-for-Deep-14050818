from flask import render_template
from security.decorators import login_required
from routes.reports import reports_bp


@reports_bp.route("/responsible")
@login_required
def responsible():
    return render_template("reports/responsible.html")