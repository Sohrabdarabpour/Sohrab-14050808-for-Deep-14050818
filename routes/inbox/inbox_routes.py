"""روت‌های کارتابل — صفحه‌ی /inbox و API."""

from flask import (
    abort, jsonify, render_template, request, session,
)

from services.documents import assignment_service

from . import inbox_bp


def _uid():
    return session.get("user_id")


# ============================================================
# ★ صفحه‌ی کارتابل
# ============================================================
@inbox_bp.route("/", methods=["GET"])
def index():
    if not _uid():
        return render_template(
            "inbox/inbox.html",
            user_id=None,
            current_tab="active",
            items=[],
            total=0,
            counts={},
            login_required=True,
        )

    tab = request.args.get("tab", "active")
    if tab not in ("active", "unread", "overdue", "waiting", "done"):
        tab = "active"

    data = assignment_service.get_inbox(_uid(), tab=tab)
    counts = _get_counts(_uid())

    return render_template(
        "inbox/inbox.html",
        user_id=_uid(),
        current_tab=tab,
        items=data.get("items", []),
        total=data.get("total", 0),
        counts=counts,
        login_required=False,
    )


# ============================================================
# ★ API — برای polling
# ============================================================
@inbox_bp.route("/api/counts", methods=["GET"])
def api_counts():
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    return jsonify({"ok": True, "counts": _get_counts(_uid())})


@inbox_bp.route("/api/<tab>", methods=["GET"])
def api_tab(tab):
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    if tab not in ("active", "unread", "overdue", "waiting", "done"):
        return jsonify({"ok": False, "error": "bad_tab"}), 400
    data = assignment_service.get_inbox(_uid(), tab=tab)
    return jsonify(data)


# ============================================================
# ★ کمکی
# ============================================================
def _get_counts(user_id):
    """شمارنده‌ی هر تب برای badge."""
    result = {}
    for tab in ("active", "unread", "overdue", "waiting", "done"):
        try:
            d = assignment_service.get_inbox(user_id, tab=tab)
            result[tab] = d.get("total", 0)
        except Exception:
            result[tab] = 0
    return result