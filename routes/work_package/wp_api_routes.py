"""APIهای JSON پکیج سند."""

from flask import jsonify, request, session

from database.connection import get_connection
from helpers.date_helper import DateHelper
from services.work_package import (
    wp_assignment_service, wp_deficiency_service,
    wp_service, wp_sla_service,
)

from . import work_package_bp


def _uid():
    return session.get("user_id")


def _to_int(val):
    """تبدیل ایمن به int."""
    if val is None or val == "" or val == 0 or val == "0":
        return None
    try:
        v = int(val)
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


# ============================================================
# ★ جستجوی سریع پکیج‌ها
# ============================================================
@work_package_bp.route("/search", methods=["POST"])
def search_packages():
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    query = (data.get("q") or "").strip()
    if len(query) < 2:
        return jsonify({"ok": True, "results": []})

    connection = get_connection()
    try:
        like = f"%{query}%"
        rows = connection.execute("""
            SELECT id, dfc_code, work_package_code, subject,
                   sender_ref_no, contract_number, stage, registered_at
            FROM document_packages
            WHERE (dfc_code LIKE ? OR sender_ref_no LIKE ?
                   OR subject LIKE ? OR contract_number LIKE ?
                   OR work_package_code LIKE ?)
            ORDER BY id DESC
            LIMIT 20
        """, (like, like, like, like, like)).fetchall()
        return jsonify({"ok": True, "results": [dict(r) for r in rows]})
    finally:
        connection.close()


# ============================================================
# ★ جستجوی کاربران
# ============================================================
@work_package_bp.route("/search-users", methods=["POST"])
def search_users_api():
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    query = (data.get("q") or "").strip()
    role_filter = data.get("role_filter")

    connection = get_connection()
    try:
        where = ["is_active = 1"]
        params = []
        if query:
            where.append("(full_name LIKE ? OR username LIKE ?)")
            like = f"%{query}%"
            params += [like, like]
        if role_filter:
            where.append("role = ?")
            params.append(role_filter)

        where_sql = " AND ".join(where)
        rows = connection.execute(f"""
            SELECT id, full_name, username, role, avatar
            FROM users
            WHERE {where_sql}
            ORDER BY full_name
            LIMIT 20
        """, params).fetchall()

        return jsonify({"ok": True, "users": [dict(r) for r in rows]})
    finally:
        connection.close()


# ============================================================
# ★ تشخیص پیمانکار و پروژه از شماره قرارداد
# ============================================================
@work_package_bp.route("/lookup-contract", methods=["POST"])
def lookup_contract_api():
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    contract_number = (data.get("contract_number") or "").strip()

    if not contract_number or len(contract_number) < 2:
        return jsonify({"ok": True, "found": False})

    info = wp_service.find_contractor_and_project_by_contract_number(contract_number)

    if info:
        return jsonify({"ok": True, "found": True, "info": info})
    return jsonify({"ok": True, "found": False})


# ============================================================
# ★ پیشنهاد WPها (منطق ترکیبی: قرارداد + رفرنس)
# ============================================================
@work_package_bp.route("/suggest-wps", methods=["POST"])
def suggest_wps_api():
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}

    # ★ خواندن همه‌ی رفرنس‌ها
    references = data.get("references") or []
    if isinstance(references, str):
        references = [references]
    references = [r.strip() for r in references if r and r.strip()]

    # اولین رفرنس (اگر رفرنس‌های چندگانه داده شده)
    reference_no = references[0] if references else None

    # ★ لاگ دیباگ
    print(f"\n=== SUGGEST_WPS API ===")
    print(f"  references: {references}")
    print(f"  reference_no: {reference_no}")
    print(f"  contract_number: {data.get('contract_number')}")

    # ★ اگر هیچ رفرنسی نداریم، هیچ WPی پیشنهاد نده
    if not references:
        # اما اگر شماره قرارداد بود، فقط برای راهنمایی نشان بده
        contract_number = (data.get("contract_number") or "").strip() or None
        if not contract_number:
            print(f"  → no refs and no contract → return empty")
            return jsonify({"ok": True, "suggestions": []})

    suggestions = wp_service.suggest_wps_for_reference(
        reference_no=reference_no,
        sender_ref_no=(data.get("sender_ref_no") or "").strip() or None,
        contract_number=(data.get("contract_number") or "").strip() or None,
        contractor_id=_to_int(data.get("contractor_id")),
        project_id=_to_int(data.get("project_id")),
        automation_number=(data.get("automation_number") or "").strip() or None,
    )

    print(f"  → suggestions: {len(suggestions)}")

    return jsonify({"ok": True, "suggestions": suggestions})


# ============================================================
# ★ پیشنهاد WPها از چند رفرنس (قدیمی — برای سازگاری)
# ============================================================
@work_package_bp.route("/suggest-wps-by-refs", methods=["POST"])
def suggest_wps_by_refs_api():
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    refs = data.get("references") or []
    if isinstance(refs, str):
        refs = [refs]
    refs = [r.strip() for r in refs if r and r.strip()]

    if not refs:
        return jsonify({"ok": True, "suggestions": []})

    suggestions = wp_service.find_wps_by_references(refs)
    return jsonify({"ok": True, "suggestions": suggestions})


# ============================================================
# ★ پیش‌نمایش SLA
# ============================================================
@work_package_bp.route("/preview-sla", methods=["POST"])
def preview_sla_api():
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    group_id = _to_int(data.get("group_id"))
    subgroup_id = _to_int(data.get("subgroup_id"))
    start_date = data.get("start_date")

    if start_date:
        start_date = DateHelper.convert_to_gregorian(start_date)

    result = wp_sla_service.preview_sla(
        group_id=group_id,
        subgroup_id=subgroup_id,
        start_date=start_date,
    )
    return jsonify(result)


# ============================================================
# ★ تغییر مرحله
# ============================================================
@work_package_bp.route("/<int:package_id>/change-stage", methods=["POST"])
def change_stage_api(package_id):
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    new_stage = (data.get("stage") or "").strip()
    reason = (data.get("reason") or "").strip() or None
    extra_fields = data.get("extra_fields") or {}

    if not new_stage:
        return jsonify({"ok": False, "error": "مرحله لازم است"}), 400

    date_fields = (
        "date_sent_to_management",
        "date_returned_from_management",
        "management_date_on_letter",
        "date_sent_response",
        "response_letter_date",
    )
    for field in date_fields:
        if extra_fields.get(field):
            extra_fields[field] = DateHelper.convert_to_gregorian(
                extra_fields[field]
            )

    result = wp_service.change_stage(
        package_id, new_stage, actor_id=_uid(),
        reason=reason, extra_fields=extra_fields or None,
    )
    if not result["ok"]:
        return jsonify(result), 400
    return jsonify(result)


# ============================================================
# ★ بازگشت از مدیریت
# ============================================================
@work_package_bp.route("/<int:package_id>/return-from-management", methods=["POST"])
def return_from_management_api(package_id):
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    import json

    date_returned = DateHelper.convert_to_gregorian(
        data.get("date_returned_from_management", "")
    )
    management_date = DateHelper.convert_to_gregorian(
        data.get("management_date_on_letter", "")
    )
    instruction = (data.get("management_instruction") or "").strip() or None
    action = (data.get("management_action") or "").strip() or None

    if action == "archive":
        result = wp_service.change_stage(
            package_id, "archived", actor_id=_uid(),
            reason="بایگانی به دستور مدیریت",
            extra_fields={
                "date_returned_from_management": date_returned,
                "management_date_on_letter": management_date,
                "management_instruction": instruction,
                "management_action": action,
            },
        )
        return jsonify(result)

    supervisor_ids = data.get("supervisor_ids") or []
    direct_expert_ids = data.get("direct_expert_ids") or []

    extra = {
        "date_returned_from_management": date_returned,
        "management_date_on_letter": management_date,
        "management_instruction": instruction,
        "management_action": action,
        "group_id": _to_int(data.get("group_id")),
        "subgroup_id": _to_int(data.get("subgroup_id")),
        "priority": data.get("priority", "normal"),
        "confidentiality": data.get("confidentiality", "internal"),
    }

    if supervisor_ids:
        extra["supervisor_ids"] = json.dumps(
            [int(x) for x in supervisor_ids], ensure_ascii=False
        )
    if direct_expert_ids:
        extra["direct_expert_ids"] = json.dumps(
            [int(x) for x in direct_expert_ids], ensure_ascii=False
        )

    result = wp_service.change_stage(
        package_id, "returned_from_management",
        actor_id=_uid(),
        extra_fields=extra,
    )
    if not result["ok"]:
        return jsonify(result), 400

    try:
        wp_sla_service.recalculate_sla(package_id, actor_id=_uid())
    except Exception:
        pass

    if supervisor_ids:
        try:
            wp_assignment_service.route_package(
                package_id=package_id,
                from_user_id=_uid(),
                to_user_ids=[int(x) for x in supervisor_ids],
                assignee_role="supervisor",
                action="route",
                instruction=instruction,
            )
            wp_service.change_stage(package_id, "routed", actor_id=_uid())
        except Exception:
            pass

    return jsonify(result)


# ============================================================
# ★ ارجاع
# ============================================================
@work_package_bp.route("/<int:package_id>/route", methods=["POST"])
def route_api(package_id):
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    to_ids = data.get("to_user_ids") or []
    if not to_ids:
        return jsonify({"ok": False, "error": "no_recipients"}), 400

    to_ids = [int(x) for x in to_ids if x]

    result = wp_assignment_service.route_package(
        package_id=package_id,
        from_user_id=_uid(),
        to_user_ids=to_ids,
        assignee_role=data.get("role", "expert"),
        action=data.get("action", "route"),
        instruction=data.get("instruction"),
        due_days=data.get("due_days"),
        priority=data.get("priority", "normal"),
        primary_user_id=data.get("primary_user_id"),
    )

    if not result["ok"] and result.get("error"):
        return jsonify(result), 400

    if result.get("created") and data.get("role") == "supervisor":
        try:
            wp_service.change_stage(package_id, "routed", actor_id=_uid())
        except Exception:
            pass

    return jsonify(result)


# ============================================================
# ★ اقدامات روی ارجاع
# ============================================================
def _do_action(assignment_id, fn, **kwargs):
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    result = fn(assignment_id, _uid(), **kwargs)
    if not result["ok"]:
        return jsonify(result), 400
    return jsonify(result)


@work_package_bp.route("/assignments/<int:aid>/read", methods=["POST"])
def assignment_read(aid):
    return _do_action(aid, wp_assignment_service.mark_read)


@work_package_bp.route("/assignments/<int:aid>/accept", methods=["POST"])
def assignment_accept(aid):
    return _do_action(aid, wp_assignment_service.accept)


@work_package_bp.route("/assignments/<int:aid>/start", methods=["POST"])
def assignment_start(aid):
    return _do_action(aid, wp_assignment_service.start)


@work_package_bp.route("/assignments/<int:aid>/complete", methods=["POST"])
def assignment_complete(aid):
    data = request.get_json(silent=True) or {}
    return _do_action(
        aid, wp_assignment_service.complete,
        note=data.get("note"),
    )


@work_package_bp.route("/assignments/<int:aid>/return", methods=["POST"])
def assignment_return(aid):
    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "").strip()
    if not reason:
        return jsonify({"ok": False, "error": "no_reason"}), 400
    return _do_action(
        aid, wp_assignment_service.return_to_sender,
        reason=reason,
    )


# ============================================================
# ★ نواقص
# ============================================================
@work_package_bp.route("/<int:package_id>/deficiencies", methods=["POST"])
def create_deficiency_api(package_id):
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    items = data.get("items") or []
    if isinstance(items, str):
        items = [i.strip() for i in items.split(",") if i.strip()]

    result = wp_deficiency_service.create_deficiency(
        package_id=package_id,
        requested_by=_uid(),
        mode=data.get("mode", "written"),
        reference_no=data.get("reference_no"),
        request_date=DateHelper.convert_to_gregorian(
            data.get("request_date", "")
        ),
        due_date=DateHelper.convert_to_gregorian(
            data.get("due_date", "")
        ),
        note=data.get("note"),
        items=items,
    )

    if not result["ok"]:
        return jsonify(result), 400
    return jsonify(result)


@work_package_bp.route("/deficiency/items/<int:item_id>/toggle", methods=["POST"])
def toggle_deficiency_item(item_id):
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    result = wp_deficiency_service.mark_item_received(
        item_id=item_id,
        received=bool(data.get("received")),
        actor_id=_uid(),
    )
    if not result["ok"]:
        return jsonify(result), 400
    return jsonify(result)


# ============================================================
# ★ محاسبه مجدد SLA
# ============================================================
@work_package_bp.route("/<int:package_id>/recalc-sla", methods=["POST"])
def recalc_sla_api(package_id):
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    result = wp_sla_service.recalculate_sla(package_id, actor_id=_uid())
    if not result["ok"]:
        return jsonify(result), 400
    return jsonify(result)


# ============================================================
# ★ اتصال سند به چند WP
# ============================================================
@work_package_bp.route("/<int:package_id>/link-wps", methods=["POST"])
def link_wps_api(package_id):
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    wp_codes = data.get("wp_codes") or []
    primary_wp = data.get("primary_wp")
    wp_codes = [w.strip() for w in wp_codes if w and w.strip()]

    result = wp_service.link_package_to_wps(
        package_id=package_id,
        wp_codes=wp_codes,
        linked_by=_uid(),
        primary_wp=primary_wp,
    )

    if not result["ok"]:
        return jsonify(result), 400

    try:
        from services.work_package import wp_event_service
        wp_event_service.log_event(
            package_id=package_id,
            actor_id=_uid(),
            event_type="wp_links_updated",
            summary=f"اتصال‌ها به‌روز شد: {len(wp_codes)} پکیج کاری",
            payload={"wp_codes": wp_codes, "primary": primary_wp},
        )
    except Exception:
        pass

    return jsonify(result)


# ============================================================
# ★ دریافت WPهای یک سند
# ============================================================
@work_package_bp.route("/<int:package_id>/wps.json", methods=["GET"])
def get_wps_api(package_id):
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    wps = wp_service.get_package_wps(package_id)
    return jsonify({"ok": True, "wps": wps})