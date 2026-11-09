from flask import Blueprint, render_template, request, session, jsonify
from services.dashboard.dashboard_service import DashboardService
from security.decorators import login_required

dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/dashboard"
)


@dashboard_bp.route("/")
@login_required
def dashboard():
    user_id = session.get("user_id")
    selected_year = request.args.get("year", "all")

    data = DashboardService.get_dashboard_meta(user_id, selected_year)

    return render_template(
        "dashboard/index.html",
        current_user=data["user"],
        available_years=data["available_years"],
        selected_year=data["selected_year"],
        statuses=data["statuses"],
        total=data["total"],
        deadline_alerts=data["deadline_alerts"],
        manager_approval_count=data.get("manager_approval_count", 0),
    )


@dashboard_bp.route("/documents.json")
@login_required
def dashboard_documents_json():
    user_id = session.get("user_id")
    year = request.args.get("year", "all")
    search = request.args.get("search", "")
    page = request.args.get("page", 1, type=int)
    status_code = request.args.get("status") or None
    deadline_filter = request.args.get("deadline_filter") or None

    data = DashboardService.get_documents_json(
        user_id=user_id,
        requested_year=year,
        search=search,
        page=page,
        status_code=status_code,
        deadline_filter=deadline_filter,
    )
    return jsonify(data)