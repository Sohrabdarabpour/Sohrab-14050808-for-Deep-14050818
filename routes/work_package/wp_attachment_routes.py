"""روت‌های پیوست پکیج سند."""

import os

from flask import (
    abort, current_app, jsonify, make_response,
    request, send_file, session,
)
from urllib.parse import quote

from database.connection import get_connection
from services.work_package import wp_attachment_service, wp_event_service

from . import work_package_bp


def _uid():
    return session.get("user_id")


def _role():
    return session.get("role", "expert")


def _can_access(package_id):
    """بررسی دسترسی به سند."""
    if not _uid():
        return False
    if _role() in ("admin", "manager", "supervisor", "doc_controller"):
        return True
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT registered_by FROM document_packages WHERE id = ?",
            (package_id,),
        ).fetchone()
        if row and row["registered_by"] == _uid():
            return True
        r = conn.execute("""
            SELECT 1 FROM document_package_assignments
            WHERE package_id = ? AND to_user_id = ?
            LIMIT 1
        """, (package_id, _uid())).fetchone()
        return bool(r)
    finally:
        conn.close()


# ============================================================
# ★ آپلود
# ============================================================
@work_package_bp.route(
    "/<int:package_id>/attachments/upload", methods=["POST"]
)
def upload_attachment(package_id):
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    if not _can_access(package_id):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    if "file" not in request.files:
        return jsonify({
            "ok": False, "error": "no_file",
            "message": "فایلی ارسال نشد",
        }), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({
            "ok": False, "error": "empty_filename",
            "message": "نام فایل خالی است",
        }), 400

    kind = request.form.get("kind", "other")
    description = request.form.get("description") or None

    try:
        info = wp_attachment_service.save_stream(
            package_id=package_id,
            file_storage=file,
            kind=kind,
            description=description,
            uploaded_by=_uid(),
        )
    except ValueError as exc:
        return jsonify({
            "ok": False, "error": "validation",
            "message": str(exc),
        }), 400
    except Exception:
        current_app.logger.exception("upload failed")
        return jsonify({
            "ok": False, "error": "internal",
            "message": "خطا در ذخیره فایل",
        }), 500

    try:
        wp_event_service.log_event(
            package_id=package_id,
            actor_id=_uid(),
            event_type=wp_event_service.EventType.ATTACHMENT_ADDED,
            summary=f"فایل پیوست شد: {info['original_name']}",
            payload={"attachment_id": info["id"], "size": info["size"]},
        )
    except Exception:
        pass

    return jsonify({
        "ok": True,
        "attachment": {
            "id": info["id"],
            "name": info["original_name"],
            "size": info["size"],
            "size_human": wp_attachment_service.human_size(info["size"]),
            "previewable": info["previewable"],
            "mime": info["mime"],
        },
    })


# ============================================================
# ★ لیست
# ============================================================
@work_package_bp.route(
    "/<int:package_id>/attachments.json", methods=["GET"]
)
def list_attachments_json(package_id):
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    if not _can_access(package_id):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    items = wp_attachment_service.list_attachments(package_id)
    result = []
    for a in items:
        result.append({
            "id": a["id"],
            "name": a["original_name"],
            "size": a["size"],
            "size_human": wp_attachment_service.human_size(a["size"]),
            "mime": a["mime"],
            "kind": a["kind"],
            "description": a.get("description"),
            "previewable": bool(a["previewable"]),
            "uploaded_by_name": a.get("uploaded_by_name"),
            "created_at": a["created_at"],
        })
    return jsonify({"ok": True, "attachments": result})


# ============================================================
# ★ پیش‌نمایش
# ============================================================
@work_package_bp.route(
    "/attachments/<int:attachment_id>/preview", methods=["GET"]
)
def preview_attachment(attachment_id):
    if not _uid():
        abort(401)
    attachment = wp_attachment_service.get_attachment(attachment_id)
    if not attachment:
        abort(404)
    if not _can_access(attachment["package_id"]):
        abort(403)

    filepath = wp_attachment_service.absolute_path(attachment)
    if not os.path.exists(filepath):
        abort(404)

    resp = make_response(send_file(
        filepath,
        mimetype=attachment.get("mime") or "application/octet-stream",
        as_attachment=False,
        download_name=attachment["original_name"],
        conditional=True,
        etag=attachment.get("sha256") or True,
        last_modified=os.path.getmtime(filepath),
    ))
    safe_name = quote(attachment["original_name"])
    resp.headers["Content-Disposition"] = (
        f'inline; filename="{safe_name}"; filename*=UTF-8\'\'{safe_name}'
    )
    return resp


# ============================================================
# ★ دانلود
# ============================================================
@work_package_bp.route(
    "/attachments/<int:attachment_id>/download", methods=["GET"]
)
def download_attachment(attachment_id):
    if not _uid():
        abort(401)
    attachment = wp_attachment_service.get_attachment(attachment_id)
    if not attachment:
        abort(404)
    if not _can_access(attachment["package_id"]):
        abort(403)

    filepath = wp_attachment_service.absolute_path(attachment)
    if not os.path.exists(filepath):
        abort(404)

    return send_file(
        filepath,
        mimetype=attachment.get("mime") or "application/octet-stream",
        as_attachment=True,
        download_name=attachment["original_name"],
        conditional=True,
    )


# ============================================================
# ★ حذف
# ============================================================
@work_package_bp.route(
    "/attachments/<int:attachment_id>/delete", methods=["POST"]
)
def delete_attachment(attachment_id):
    if not _uid():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    attachment = wp_attachment_service.get_attachment(attachment_id)
    if not attachment:
        return jsonify({"ok": False, "error": "not_found"}), 404
    if not _can_access(attachment["package_id"]):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    # فقط آپلودکننده یا ادمین
    if (_role() not in ("admin", "manager")
            and attachment.get("uploaded_by") != _uid()):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    deleted = wp_attachment_service.delete_attachment(attachment_id)
    if not deleted:
        return jsonify({"ok": False, "error": "delete_failed"}), 500

    try:
        wp_event_service.log_event(
            package_id=attachment["package_id"],
            actor_id=_uid(),
            event_type=wp_event_service.EventType.ATTACHMENT_DELETED,
            summary=f"فایل حذف شد: {deleted['original_name']}",
            payload={"attachment_id": attachment_id},
        )
    except Exception:
        pass

    return jsonify({"ok": True, "message": "پیوست حذف شد"})