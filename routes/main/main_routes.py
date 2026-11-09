from flask import Blueprint, redirect, url_for, render_template
from security.decorators import login_required

main_bp = Blueprint(
    "main",
    __name__
)


@main_bp.route("/")
@login_required
def index():
    return redirect(
        url_for("dashboard.dashboard")
    )


# ★★★ صفحه عدم دسترسی (برای redirect از decorators) ★★★
@main_bp.route("/access-denied")
@login_required
def access_denied():
    return render_template("access_denied.html"), 403