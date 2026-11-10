"""روت‌های پکیج سند — صفحه‌ی کامل /documents/package/<id>."""

from flask import (
    abort, jsonify, redirect, render_template,
    request, session, url_for, flash,
)

from database.connection import get_connection
from services.documents import (
    assignment_service, event_service, package_service,
    sla_service, storage_service,
)
from helpers.date_helper import DateHelper

from .documents_routes import documents_bp
from forms.documents.package_form import PackageForm


PRIVILEGED_ROLES = ("admin", "manager", "supervisor", "doc_controller")


# ============================================================
# ★ صفحه‌ی اصلی پکیج
# ============================================================
@documents_bp.route("/package/<int:document_id>", methods=["GET"])
def package_view(document_id):
    """صفحه‌ی کامل پکیج سند با تب‌ها."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    role = session.get("role", "expert")
    is_privileged = role in PRIVILEGED_ROLES

    doc = package_service.get_package(document_id)
    if not doc:
        abort(404)

    # ★ دسترسی
    has_access = (
        is_privileged
        or doc.get("registered_by") == user_id
        or doc.get("user_id") == user_id
    )
    if not has_access:
        connection = get_connection()
        try:
            r = connection.execute("""
                SELECT 1 FROM document_assignments
                WHERE document_id = ? AND to_user_id = ?
                LIMIT 1
            """, (document_id, user_id)).fetchone()
            if r:
                has_access = True
        finally:
            connection.close()

    if not has_access:
        abort(403)

    # ★ داده‌های تب‌ها
    events = event_service.list_events(document_id, limit=100)
    assignments = assignment_service.get_document_assignments(document_id)
    attachments = storage_service.list_attachments(document_id)

    # ★ تاریخ‌ها را به شمسی تبدیل کن
    for field in ("date_letter", "date_received", "date_referral",
                  "response_due_date", "sla_start_date",
                  "created_at", "updated_at",
                  "closed_at", "archived_at"):
        if doc.get(field):
            try:
                doc[field] = DateHelper.format_jalali(doc[field])
            except Exception:
                pass

    for a in assignments:
        for field in ("due_date", "created_at", "completed_at", "read_at"):
            if a.get(field):
                try:
                    a[field] = DateHelper.format_jalali(a[field])
                except Exception:
                    pass

    for e in events:
        if e.get("created_at"):
            try:
                e["created_at"] = DateHelper.format_jalali_datetime(e["created_at"])
            except Exception:
                pass

    for att in attachments:
        att["size_human"] = storage_service.human_size(att["size"])

    # ★ کاربران برای فرم ارجاع
    connection = get_connection()
    try:
        users = [dict(r) for r in connection.execute(
            "SELECT id, full_name, role FROM users "
            "WHERE is_active = 1 ORDER BY full_name"
        ).fetchall()]
    finally:
        connection.close()

    from services.documents.package_service import STAGE_TRANSITIONS
    current_stage = doc.get("stage") or "draft"
    allowed_stages = STAGE_TRANSITIONS.get(current_stage, [])

    return render_template(
        "documents/package.html",
        doc=doc,
        events=events,
        assignments=assignments,
        attachments=attachments,
        users=users,
        is_privileged=is_privileged,
        current_stage=current_stage,
        allowed_stages=allowed_stages,
    )


# ============================================================
# ★ API: انتقال مرحله
# ============================================================
@documents_bp.route(
    "/package/<int:document_id>/change-stage", methods=["POST"]
)
def package_change_stage(document_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    new_stage = (data.get("stage") or "").strip()
    reason = (data.get("reason") or "").strip() or None

    if not new_stage:
        return jsonify({"ok": False, "error": "مرحله لازم است"}), 400

    result = package_service.change_stage(
        document_id, new_stage, actor_id=user_id, reason=reason,
    )
    if not result["ok"]:
        return jsonify(result), 400
    return jsonify(result)


# ============================================================
# ★ فرم ثبت سند جدید (اصلاح‌شده)
# ============================================================
@documents_bp.route("/package/new", methods=["GET", "POST"])
def package_new():
    """صفحه و فرم ثبت پکیج سند جدید."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    form = PackageForm()
    
    connection = get_connection()
    try:
        form.group_id.choices = [(0, "— بدون گروه —")] + [
            (r["id"], r["title"]) for r in connection.execute(
                "SELECT id, title FROM document_groups WHERE is_active=1 ORDER BY sort_order"
            ).fetchall()
        ]
        form.subgroup_id.choices = [(0, "— بدون زیرگروه —")]
        form.contractor_id.choices = [(0, "— بدون پیمانکار —")] + [
            (r["id"], r["name"]) for r in connection.execute(
                "SELECT id, name FROM contractors WHERE is_active=1 ORDER BY name"
            ).fetchall()
        ]
        form.project_id.choices = [(0, "— بدون پروژه —")] + [
            (r["id"], r["name"]) for r in connection.execute(
                "SELECT id, name FROM projects WHERE is_active=1 ORDER BY name"
            ).fetchall()
        ]
    finally:
        connection.close()

    if form.validate_on_submit():
        from services.documents.package_service import register_document
        
        date_received_gregorian = None
        if form.date_received.data:
            date_received_gregorian = DateHelper.convert_to_gregorian(form.date_received.data)

        result = register_document(
            subject=form.subject.data,
            registered_by=user_id,
            date_received=date_received_gregorian,
            group_id=form.group_id.data if form.group_id.data != 0 else None,
            subgroup_id=form.subgroup_id.data if form.subgroup_id.data != 0 else None,
            source_type=form.source_type.data,
            sender_name=form.sender_name.data,
            sender_ref_no=form.sender_ref_no.data,
            contract_number=form.contract_number.data,
            priority=form.priority.data,
            contractor_id=form.contractor_id.data if form.contractor_id.data != 0 else None,
            project_id=form.project_id.data if form.project_id.data != 0 else None,
        )
        
        if result["ok"]:
            # ★ لاگ دیباگ
            print(f"✅ سند ثبت شد: id={result['document_id']}, code={result['package_code']}")
            print(f"   redirecting to /documents/package/{result['document_id']}")
            
            flash(f"سند با کد {result['package_code']} با موفقیت ثبت شد.", "success")
            # ★ ریدایرکت مستقیم (بدون url_for) برای اطمینان
            return redirect(f"/documents/package/{result['document_id']}")
        else:
            print(f"❌ خطا در ثبت: {result.get('error')}")
            flash(result.get("error", "خطا در ثبت سند"), "danger")

    elif form.errors:
        print("=" * 60)
        print("❌ فرم اعتبارسنجی نشد:")
        for field, errors in form.errors.items():
            print(f"   {field}: {errors}")
        print("=" * 60)

    return render_template("documents/package_new.html", form=form)


# ============================================================
# ★ API: زیرگروه‌ها
# ============================================================
@documents_bp.route("/api/groups/<int:group_id>/subgroups", methods=["GET"])
def api_get_subgroups(group_id):
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT sg.id, sg.title 
            FROM document_subgroups sg
            JOIN group_subgroups gs ON gs.subgroup_id = sg.id
            WHERE gs.group_id = ? AND sg.is_active = 1
            ORDER BY sg.sort_order
        """, (group_id,)).fetchall()
        return jsonify({"ok": True, "subgroups": [dict(r) for r in rows]})
    finally:
        connection.close()


# ============================================================
# ★ API: پروژه‌های یک پیمانکار
# ============================================================
@documents_bp.route("/api/contractors/<int:contractor_id>/projects", methods=["GET"])
def api_get_contractor_projects(contractor_id):
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT id, name 
            FROM projects 
            WHERE contractor_id = ? AND is_active = 1 
            ORDER BY name
        """, (contractor_id,)).fetchall()
        return jsonify({"ok": True, "projects": [dict(r) for r in rows]})
    finally:
        connection.close()


# ============================================================
# ★ API: جستجوی رفرنس برای پر کردن خودکار فرم
# ============================================================
@documents_bp.route("/package/search-reference", methods=["POST"])
def search_reference_api():
    """جستجوی رفرنس در اسناد قبلی برای پر کردن خودکار فرم."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    ref_no = (data.get("ref_no") or "").strip()
    if not ref_no:
        return jsonify({"ok": True, "found": False, "message": "شماره رفرنس وارد نشده"})

    connection = get_connection()
    try:
        # ۱. جستجو در جدول document_references
        ref_rows = connection.execute("""
            SELECT r.document_id AS doc_id, d.package_code, d.subject,
                   d.contractor_id, d.project_id, d.contract_number,
                   c.name AS contractor_name, p.name AS project_name
            FROM document_references r
            JOIN documents d ON d.id = r.document_id
            LEFT JOIN contractors c ON c.id = d.contractor_id
            LEFT JOIN projects p ON p.id = d.project_id
            WHERE r.ref_no = ?
            ORDER BY r.created_at DESC
            LIMIT 5
        """, (ref_no,)).fetchall()

        # ۲. جستجو در جدول documents (شماره نامه فرستنده یا شماره قرارداد)
        doc_rows = connection.execute("""
            SELECT d.id AS doc_id, d.package_code, d.subject,
                   d.contractor_id, d.project_id, d.contract_number,
                   c.name AS contractor_name, p.name AS project_name
            FROM documents d
            LEFT JOIN contractors c ON c.id = d.contractor_id
            LEFT JOIN projects p ON p.id = d.project_id
            WHERE d.sender_ref_no = ?
               OR d.contractor_letter_number = ?
               OR d.contract_number = ?
               OR d.automation_number = ?
            ORDER BY d.id DESC
            LIMIT 5
        """, (ref_no, ref_no, ref_no, ref_no)).fetchall()

        seen = set()
        results = []
        for row in list(ref_rows) + list(doc_rows):
            doc_id = row["doc_id"]
            if doc_id in seen:
                continue
            seen.add(doc_id)
            results.append({
                "document_id": doc_id,
                "package_code": row["package_code"],
                "subject": row["subject"],
                "contractor_id": row["contractor_id"],
                "contractor_name": row["contractor_name"],
                "project_id": row["project_id"],
                "project_name": row["project_name"],
                "contract_number": row["contract_number"],
            })

        if not results:
            return jsonify({
                "ok": True, "found": False,
                "message": "هیچ سندی با این رفرنس پیدا نشد."
            })

        return jsonify({
            "ok": True, "found": True,
            "results": results[:5],
            "first": results[0],
        })
    finally:
        connection.close()


# ============================================================
# ★ API: جستجوی دقیق شماره نامه تکراری
# ============================================================
@documents_bp.route("/package/find-by-ref", methods=["POST"])
def find_by_ref_api():
    """اگر نامه‌ای با همین شماره قبلاً ثبت شده باشد، آن را برگردان."""
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    ref_no = data.get("sender_ref_no", "").strip()

    if not ref_no:
        return jsonify({"ok": True, "matches": []})

    from services.documents import suggestion_service
    matches = suggestion_service.find_by_sender_ref_no(ref_no)
    return jsonify({"ok": True, "matches": matches})


# ============================================================
# ★ API: پیشنهاد پکیج
# ============================================================
@documents_bp.route("/package/suggest", methods=["POST"])
def suggest_packages_api():
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    from services.documents import suggestion_service

    suggestions = suggestion_service.suggest_packages(
        subject=data.get("subject"),
        contractor_id=data.get("contractor_id"),
        project_id=data.get("project_id"),
        sender_name=data.get("sender_name"),
        group_id=data.get("group_id"),
        limit=10,
    )
    return jsonify({"ok": True, "suggestions": suggestions})