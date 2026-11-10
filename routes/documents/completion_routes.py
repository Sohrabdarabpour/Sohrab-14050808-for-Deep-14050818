"""روت‌های تکمیل مدارک."""

from flask import jsonify, request, session
from services.documents import completion_service
from .documents_routes import documents_bp


def _uid():
    return session.get("user_id")


@documents_bp.route("/<int:document_id>/completion.json", methods=["GET"])
def list_completion_requests(document_id):
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    items = completion_service.list_requests(document_id)
    return jsonify({"ok": True, "requests": items})


@documents_bp.route("/<int:document_id>/completion", methods=["POST"])
def create_completion_request(document_id):
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    
    items = data.get("items") or []
    if isinstance(items, str):
        # اگر رشته بود، با کاما جدا کن
        items = [i.strip() for i in items.split(",") if i.strip()]

    result = completion_service.create_completion_request(
        document_id=document_id,
        requested_by=_uid(),
        mode=data.get("mode", "written"),
        request_date=data.get("request_date"),
        due_date=data.get("due_date"),
        note=data.get("note"),
        items=items,
    )
    if not result["ok"]:
        return jsonify(result), 400
    return jsonify(result)


@documents_bp.route("/completion/items/<int:item_id>/toggle", methods=["POST"])
def toggle_completion_item(item_id):
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    
    data = request.get_json(silent=True) or {}
    received = bool(data.get("received"))
    
    result = completion_service.mark_item_received(
        item_id=item_id,
        received=received,
        actor_id=_uid(),
    )
    if not result["ok"]:
        return jsonify(result), 400
    return jsonify(result)