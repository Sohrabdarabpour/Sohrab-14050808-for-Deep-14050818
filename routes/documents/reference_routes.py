"""روت‌های نامه‌ها و رفرنس‌ها."""

from flask import abort, jsonify, request, session

from services.documents import reference_service
from .documents_routes import documents_bp


def _uid():
    return session.get("user_id")


@documents_bp.route("/<int:document_id>/references.json", methods=["GET"])
def list_references_json(document_id):
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    items = reference_service.list_references(document_id)
    return jsonify({"ok": True, "references": items})


@documents_bp.route("/<int:document_id>/references", methods=["POST"])
def create_reference(document_id):
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    
    data = request.get_json(silent=True) or {}
    
    result = reference_service.create_reference(
        document_id=document_id,
        ref_type=data.get("ref_type"),
        created_by=_uid(),
        direction=data.get("direction"),
        is_official=data.get("is_official"),
        ref_no=data.get("ref_no"),
        ref_date=data.get("ref_date"),
        party_type=data.get("party_type"),
        person_name=data.get("person_name"),
        subject=data.get("subject"),
        summary=data.get("summary"),
        outcome=data.get("outcome"),
        response_to_id=data.get("response_to_id"),
    )
    
    if not result["ok"]:
        return jsonify(result), 400
    return jsonify(result)