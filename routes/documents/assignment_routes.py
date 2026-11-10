"""روت‌های ارجاع سند (JSON API).

مسیرها:
- POST /documents/<id>/route — ارجاع به یک یا چند نفر
- POST /documents/assignments/<id>/accept — پذیرش
- POST /documents/assignments/<id>/start — شروع
- POST /documents/assignments/<id>/complete — اتمام
- POST /documents/assignments/<id>/return — بازگشت
- POST /documents/assignments/<id>/cancel — لغو
- GET  /documents/<id>/assignments.json — لیست درخت
"""

from flask import abort, jsonify, request, session

from services.documents import assignment_service

from .documents_routes import documents_bp


def _uid():
    return session.get("user_id")


def _role():
    return session.get("role", "expert")


def _json_error(message, code=400, error="bad_request"):
    return jsonify({"ok": False, "error": error, "message": message}), code


# ============================================================
# ★ ارجاع
# ============================================================
@documents_bp.route(
    "/<int:document_id>/route", methods=["POST"]
)
def route_document(document_id):
    if not _uid():
        return _json_error("لطفاً وارد شوید", 401, "unauthorized")

    data = request.get_json(silent=True) or {}

    # گیرندگان: آرایه‌ی to_user_ids یا to_user_id تکی
    to_ids = data.get("to_user_ids") or []
    if not to_ids and data.get("to_user_id"):
        to_ids = [data["to_user_id"]]
    to_ids = [int(x) for x in to_ids if x]

    if not to_ids:
        return _json_error("حداقل یک گیرنده لازم است", 400, "no_recipients")

    instruction = (data.get("instruction") or "").strip() or None
    due_days = data.get("due_days")
    if due_days is not None:
        try:
            due_days = int(due_days)
        except (TypeError, ValueError):
            due_days = None
    priority = data.get("priority", "normal")

    result = assignment_service.route_document(
        document_id=document_id,
        from_user_id=_uid(),
        to_user_ids=to_ids,
        instruction=instruction,
        due_days=due_days,
        priority=priority,
    )

    if not result["ok"] and result.get("error"):
        return _json_error(result["error"], 400, "route_failed")

    return jsonify(result)


# ============================================================
# ★ اقدامات گیرنده (کمکی)
# ============================================================
def _do_action(assignment_id, action_fn, **kwargs):
    if not _uid():
        return _json_error("لطفاً وارد شوید", 401, "unauthorized")
    result = action_fn(assignment_id, _uid(), **kwargs)
    if not result["ok"]:
        return _json_error(result.get("error", "خطا"), 400, "action_failed")
    return jsonify(result)


@documents_bp.route(
    "/assignments/<int:assignment_id>/read", methods=["POST"]
)
def assignment_read(assignment_id):
    return _do_action(assignment_id, assignment_service.mark_read)


@documents_bp.route(
    "/assignments/<int:assignment_id>/accept", methods=["POST"]
)
def assignment_accept(assignment_id):
    return _do_action(assignment_id, assignment_service.accept)


@documents_bp.route(
    "/assignments/<int:assignment_id>/start", methods=["POST"]
)
def assignment_start(assignment_id):
    return _do_action(assignment_id, assignment_service.start)


@documents_bp.route(
    "/assignments/<int:assignment_id>/complete", methods=["POST"]
)
def assignment_complete(assignment_id):
    data = request.get_json(silent=True) or {}
    note = (data.get("note") or "").strip() or None
    return _do_action(assignment_id, assignment_service.complete, note=note)


@documents_bp.route(
    "/assignments/<int:assignment_id>/return", methods=["POST"]
)
def assignment_return(assignment_id):
    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "").strip()
    if not reason:
        return _json_error("دلیل بازگشت الزامی است", 400, "no_reason")
    return _do_action(assignment_id, assignment_service.return_to_sender, reason=reason)


@documents_bp.route(
    "/assignments/<int:assignment_id>/cancel", methods=["POST"]
)
def assignment_cancel(assignment_id):
    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "").strip() or None
    return _do_action(assignment_id, assignment_service.cancel, reason=reason)


# ============================================================
# ★ لیست درخت ارجاع‌های یک سند
# ============================================================
@documents_bp.route(
    "/<int:document_id>/assignments.json", methods=["GET"]
)
def list_document_assignments(document_id):
    if not _uid():
        return _json_error("لطفاً وارد شوید", 401, "unauthorized")
    items = assignment_service.get_document_assignments(document_id)
    return jsonify({"ok": True, "assignments": items})