"""روت‌های کارتابل — نمایش ترکیبی ارجاع‌های پکیج جدید و اسناد قدیمی."""

from flask import (
    jsonify, redirect, render_template, request, session, url_for,
)

from . import inbox_bp


def _uid():
    return session.get("user_id")


def _get_inbox_merged(user_id, tab="active", limit=100):
    """دریافت کارتابل ترکیبی از پکیج جدید + اسناد قدیمی."""
    from services.work_package import wp_assignment_service
    try:
        return wp_assignment_service.get_inbox_merged(
            user_id, tab=tab, limit=limit
        )
    except Exception:
        return {"ok": True, "items": [], "total": 0,
                "package_count": 0, "legacy_count": 0}


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

    data = _get_inbox_merged(_uid(), tab=tab)
    counts = _get_counts(_uid())

    return render_template(
        "inbox/inbox.html",
        user_id=_uid(),
        current_tab=tab,
        items=data.get("items", []),
        total=data.get("total", 0),
        package_count=data.get("package_count", 0),
        legacy_count=data.get("legacy_count", 0),
        counts=counts,
        login_required=False,
    )


# ============================================================
# ★ API — شمارنده‌ها
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
    data = _get_inbox_merged(_uid(), tab=tab)
    return jsonify(data)


# ============================================================
# ★ کمکی
# ============================================================
def _get_counts(user_id):
    """شمارنده هر تب — ترکیبی از پکیج و legacy."""
    result = {}
    for tab in ("active", "unread", "overdue", "waiting", "done"):
        try:
            d = _get_inbox_merged(user_id, tab=tab, limit=1)
            result[tab] = d.get("total", 0)
        except Exception:
            result[tab] = 0
    return result