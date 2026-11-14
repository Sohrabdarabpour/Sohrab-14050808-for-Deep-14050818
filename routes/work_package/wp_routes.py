"""روت‌های نمایش پکیج سند."""

from flask import (
    abort, redirect, render_template, request, session, url_for,
)

from database.connection import get_connection
from helpers.date_helper import DateHelper
from services.work_package import (
    wp_event_service, wp_service, wp_sla_service,
)

from . import work_package_bp


PRIVILEGED_ROLES = ("admin", "manager", "supervisor", "doc_controller")


def _uid():
    return session.get("user_id")


def _role():
    return session.get("role", "expert")


# ============================================================
# ★ صفحه‌ی اصلی پکیج
# ============================================================
@work_package_bp.route("/<int:package_id>", methods=["GET"])
def view(package_id):
    if not _uid():
        return redirect(url_for("auth.login"))

    package = wp_service.get_package(package_id)
    if not package:
        abort(404)

    # دسترسی
    has_access = (
        _role() in PRIVILEGED_ROLES
        or package.get("registered_by") == _uid()
    )
    if not has_access:
        conn = get_connection()
        try:
            r = conn.execute("""
                SELECT 1 FROM document_package_assignments
                WHERE package_id = ? AND to_user_id = ?
                LIMIT 1
            """, (package_id, _uid())).fetchone()
            if r:
                has_access = True
        finally:
            conn.close()

    if not has_access:
        abort(403)

    # تبدیل تاریخ‌ها به شمسی
    date_fields = (
        "date_letter", "date_received", "sender_ref_date",
        "date_sent_to_management", "date_returned_from_management",
        "management_date_on_letter", "sla_start_date",
        "response_due_date", "response_letter_date", "date_sent_response",
        "supervisor_approved_at", "management_approved_at",
        "closed_at", "archived_at", "created_at", "updated_at",
        "registered_at",
    )
    for field in date_fields:
        if package.get(field):
            try:
                package[field] = DateHelper.format_jalali(package[field])
            except Exception:
                pass

    # رویدادها
    events = wp_event_service.list_events(package_id, limit=100)
    for e in events:
        if e.get("created_at"):
            try:
                e["created_at"] = DateHelper.format_jalali_datetime(e["created_at"])
            except Exception:
                pass

    # ارجاع‌ها
    from services.work_package import wp_assignment_service
    assignments = wp_assignment_service.get_package_assignments(package_id)
    for a in assignments:
        for field in ("due_date", "created_at", "read_at",
                      "accepted_at", "completed_at"):
            if a.get(field):
                try:
                    a[field] = DateHelper.format_jalali(a[field])
                except Exception:
                    pass

    # پیوست‌ها
    from services.work_package import wp_attachment_service
    attachments = wp_attachment_service.list_attachments(package_id)
    for att in attachments:
        att["size_human"] = wp_attachment_service.human_size(att["size"])

    # نواقص
    from services.work_package import wp_deficiency_service
    deficiencies = wp_deficiency_service.list_deficiencies(package_id)
    for d in deficiencies:
        for field in ("request_date", "due_date", "fulfilled_at"):
            if d.get(field):
                try:
                    d[field] = DateHelper.format_jalali(d[field])
                except Exception:
                    pass

    # siblings
    siblings = wp_service.list_work_package_siblings(
        package["work_package_code"]
    )

    # ★ کاربران + گروه‌ها
    conn = get_connection()
    try:
        users = [dict(r) for r in conn.execute(
            "SELECT id, full_name, role FROM users WHERE is_active=1 ORDER BY full_name"
        ).fetchall()]
        all_groups = [dict(r) for r in conn.execute(
            "SELECT id, title FROM document_groups WHERE is_active=1 ORDER BY sort_order"
        ).fetchall()]
    finally:
        conn.close()

    # مراحل مجاز
    from services.work_package.wp_service import STAGE_TRANSITIONS
    current_stage = package.get("stage") or "registered"
    allowed_stages = STAGE_TRANSITIONS.get(current_stage, [])

    return render_template(
        "work_package/view.html",
        package=package,
        events=events,
        assignments=assignments,
        attachments=attachments,
        deficiencies=deficiencies,
        siblings=siblings,
        users=users,
        all_users=users,          # ★ برای مودال بازگشت
        all_groups=all_groups,    # ★ برای مودال بازگشت
        current_stage=current_stage,
        allowed_stages=allowed_stages,
    )


# ============================================================
# ★ چاپ کد DFC
# ============================================================
@work_package_bp.route("/<int:package_id>/print-label", methods=["GET"])
def print_label(package_id):
    if not _uid():
        return redirect(url_for("auth.login"))

    package = wp_service.get_package(package_id)
    if not package:
        abort(404)

    if package.get("registered_at"):
        try:
            package["registered_at"] = DateHelper.format_jalali(
                package["registered_at"]
            )
        except Exception:
            pass

    return render_template("work_package/print_label.html", package=package)


# ============================================================
# ★ لیست پکیج‌ها
# ============================================================
@work_package_bp.route("/", methods=["GET"])
def list_packages():
    if not _uid():
        return redirect(url_for("auth.login"))

    stage = request.args.get("stage") or None
    search = request.args.get("search", "").strip()
    page = max(1, request.args.get("page", 1, type=int))

    per_page = 30
    offset = (page - 1) * per_page

    conn = get_connection()
    try:
        where = ["1=1"]
        params = []
        if stage:
            where.append("p.stage = ?")
            params.append(stage)
        if search:
            where.append("""
                (p.dfc_code LIKE ? OR p.subject LIKE ?
                 OR p.contract_number LIKE ? OR p.sender_ref_no LIKE ?
                 OR p.work_package_code LIKE ?)
            """)
            like = f"%{search}%"
            params += [like, like, like, like, like]

        where_sql = " AND ".join(where)

        total = conn.execute(
            f"SELECT COUNT(*) AS c FROM document_packages p WHERE {where_sql}",
            params,
        ).fetchone()["c"]

        rows = conn.execute(f"""
            SELECT p.*,
                   c.name AS contractor_name,
                   u.full_name AS registered_by_name
            FROM document_packages p
            LEFT JOIN contractors c ON c.id = p.contractor_id
            LEFT JOIN users u ON u.id = p.registered_by
            WHERE {where_sql}
            ORDER BY p.id DESC
            LIMIT ? OFFSET ?
        """, params + [per_page, offset]).fetchall()

        packages = [dict(r) for r in rows]
    finally:
        conn.close()

    for pkg in packages:
        for field in ("date_received", "response_due_date", "registered_at"):
            if pkg.get(field):
                try:
                    pkg[field] = DateHelper.format_jalali(pkg[field])
                except Exception:
                    pass

    return render_template(
        "work_package/list.html",
        packages=packages,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
        stage=stage,
        search=search,
    )