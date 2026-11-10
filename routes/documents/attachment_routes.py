"""روت‌های پیوست سند: آپلود، پیش‌نمایش، دانلود، لیست، حذف.

سازگار با ساختار موجود: از همان documents_bp که در documents_routes.py
تعریف شده استفاده می‌کند.
"""

import os
from urllib.parse import quote

from flask import (
    abort, current_app, jsonify, make_response,
    render_template_string, request, send_file, session,
)

from config import Config
from database.connection import get_connection
from services.documents import event_service, storage_service

from .documents_routes import documents_bp


# ============================================================
# ★ کمکی‌های دسترسی
# ============================================================
def _current_user_id():
    return session.get("user_id")


def _current_role():
    return session.get("role", "expert")


def _get_document(document_id):
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def _can_access_document(doc, user_id, role):
    """دسترسی: ادمین/مدیر/سرپرست/کنترل‌مستندات، ثبت‌کننده، یا مسئول ارجاع فعال."""
    if not doc or not user_id:
        return False
    if role in ("admin", "manager", "supervisor", "doc_controller"):
        return True
    if doc.get("registered_by") == user_id:
        return True
    # مالکیت قدیمی (user_id روی سند)
    if doc.get("user_id") == user_id:
        return True
    connection = get_connection()
    try:
        row = connection.execute("""
            SELECT 1 FROM document_assignments
            WHERE document_id = ? AND to_user_id = ?
              AND status IN ('pending','accepted','in_progress')
            LIMIT 1
        """, (doc["id"], user_id)).fetchone()
        return bool(row)
    finally:
        connection.close()


def _require_access_to_document(document_id):
    if not _current_user_id():
        abort(401)
    doc = _get_document(document_id)
    if not doc:
        abort(404)
    if not _can_access_document(doc, _current_user_id(), _current_role()):
        abort(403)
    return doc


def _require_access_to_attachment(attachment_id):
    if not _current_user_id():
        abort(401)
    attachment = storage_service.get_attachment(attachment_id)
    if not attachment:
        abort(404)
    doc = _get_document(attachment["document_id"])
    if not _can_access_document(doc, _current_user_id(), _current_role()):
        abort(403)
    return attachment, doc


# ============================================================
# ★ آپلود
# ============================================================
@documents_bp.route(
    "/<int:document_id>/attachments/upload", methods=["POST"]
)
def upload_attachment(document_id):
    """آپلود استریمی فایل به یک سند."""
    _require_access_to_document(document_id)

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
    reference_id = request.form.get("reference_id", type=int)

    try:
        info = storage_service.save_stream(
            document_id=document_id,
            file_storage=file,
            kind=kind,
            reference_id=reference_id,
            uploaded_by=_current_user_id(),
        )
    except ValueError as exc:
        current_app.logger.warning(
            f"upload rejected: filename={file.filename!r} error={exc}"
        )
        return jsonify({
            "ok": False, "error": "validation",
            "message": str(exc),
        }), 400
    except Exception:
        current_app.logger.exception("upload_attachment failed")
        return jsonify({
            "ok": False, "error": "internal",
            "message": "خطا در ذخیره‌ی فایل",
        }), 500

    # ★★★ ثبت رویداد
    try:
        event_service.log_event(
            document_id=document_id,
            actor_id=_current_user_id(),
            event_type=event_service.EventType.ATTACHMENT_ADDED,
            summary=f"فایل پیوست شد: {info['original_name']}",
            payload={
                "attachment_id": info["id"],
                "size": info["size"],
                "mime": info["mime"],
            },
        )
    except Exception:
        current_app.logger.exception("event log failed for attachment")

    return jsonify({
        "ok": True,
        "attachment": {
            "id": info["id"],
            "name": info["original_name"],
            "size": info["size"],
            "size_human": storage_service.human_size(info["size"]),
            "previewable": info["previewable"],
            "mime": info["mime"],
        },
    })


# ============================================================
# ★ لیست پیوست‌ها (JSON)
# ============================================================
@documents_bp.route(
    "/<int:document_id>/attachments.json", methods=["GET"]
)
def list_attachments_json(document_id):
    _require_access_to_document(document_id)
    attachments = storage_service.list_attachments(document_id)
    result = []
    for a in attachments:
        result.append({
            "id": a["id"],
            "name": a["original_name"],
            "size": a["size"],
            "size_human": storage_service.human_size(a["size"]),
            "mime": a["mime"],
            "kind": a["kind"],
            "previewable": bool(a["previewable"]),
            "uploaded_by": a["uploaded_by"],
            "created_at": a["created_at"],
        })
    return jsonify({"ok": True, "attachments": result})


# ============================================================
# ★ پیش‌نمایش (inline)
# ============================================================
@documents_bp.route(
    "/attachments/<int:attachment_id>/preview", methods=["GET"]
)
def preview_attachment(attachment_id):
    attachment, _doc = _require_access_to_attachment(attachment_id)
    filepath = storage_service.absolute_path(attachment)
    if not os.path.exists(filepath):
        abort(404)
    
    mime = attachment.get("mime") or "application/octet-stream"
    
    # ★★★ استفاده از make_response برای مجبور کردن مرورگر به نمایش (inline)
    resp = make_response(send_file(
        filepath,
        mimetype=mime,
        as_attachment=False,
        download_name=attachment["original_name"],
        conditional=True,
        etag=attachment.get("sha256") or True,
        last_modified=os.path.getmtime(filepath),
    ))
    
    # ★★★ نام فایل را encode می‌کنیم تا مرورگر با فارسی/فاصله مشکل نداشته باشد
    safe_name = quote(attachment["original_name"])
    resp.headers["Content-Disposition"] = f'inline; filename="{safe_name}"; filename*=UTF-8\'\'{safe_name}'
    
    return resp


# ============================================================
# ★ دانلود (attachment)
# ============================================================
@documents_bp.route(
    "/attachments/<int:attachment_id>/download", methods=["GET"]
)
def download_attachment(attachment_id):
    attachment, _doc = _require_access_to_attachment(attachment_id)
    filepath = storage_service.absolute_path(attachment)
    if not os.path.exists(filepath):
        abort(404)
    return send_file(
        filepath,
        mimetype=attachment.get("mime") or "application/octet-stream",
        as_attachment=True,
        download_name=attachment["original_name"],
        conditional=True,
        etag=attachment.get("sha256") or True,
        last_modified=os.path.getmtime(filepath),
    )


# ============================================================
# ★ حذف
# ============================================================
@documents_bp.route(
    "/attachments/<int:attachment_id>/delete", methods=["POST"]
)
def delete_attachment(attachment_id):
    attachment, doc = _require_access_to_attachment(attachment_id)
    user_id = _current_user_id()
    
    if _current_role() not in ("admin", "manager") \
            and attachment.get("uploaded_by") != user_id \
            and doc.get("registered_by") != user_id:
        abort(403)

    deleted = storage_service.delete_attachment(attachment_id)
    if not deleted:
        return jsonify({
            "ok": False, "error": "not_found",
            "message": "پیوست پیدا نشد",
        }), 404

    try:
        event_service.log_event(
            document_id=doc["id"],
            actor_id=user_id,
            event_type=event_service.EventType.ATTACHMENT_DELETED,
            summary=f"فایل حذف شد: {deleted['original_name']}",
            payload={"attachment_id": attachment_id},
        )
    except Exception:
        current_app.logger.exception("event log failed for attachment delete")

    return jsonify({"ok": True, "message": "پیوست حذف شد"})


# ============================================================
# ★ صفحه‌ی تست HTML — فقط DEBUG
# ============================================================
_TEST_PAGE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="csrf-token" content="{{ csrf_token() }}">
  <title>تست پیوست سند #{{ doc.id }}</title>
  <style>
    body { font-family: Tahoma, sans-serif; background: #f5f7fa; padding: 20px; }
    .card { background: #fff; border-radius: 8px; padding: 16px;
            margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
    h2 { margin-top: 0; color: #1b698b; }
    .row { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; flex-wrap: wrap; }
    button, input[type=submit] { padding: 8px 16px; border: none;
            background: #1b698b; color: #fff; border-radius: 4px; cursor: pointer; }
    button:hover { background: #145272; }
    .danger { background: #dc2626; }
    .danger:hover { background: #b91c1c; }
    .secondary { background: #718096; }
    .secondary:hover { background: #4a5568; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 8px; text-align: right; border-bottom: 1px solid #eee; }
    th { background: #f7fafc; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 10px;
            font-size: 12px; background: #e2e8f0; }
    #progress { display: none; margin-top: 8px; }
    #preview-area { margin-top: 16px; min-height: 100px; }
    iframe, video, img { max-width: 100%; border: 1px solid #ddd; border-radius: 6px; }
    .msg { padding: 10px; border-radius: 4px; margin: 8px 0; }
    .msg-ok { background: #c6f6d5; color: #22543d; }
    .msg-err { background: #fed7d7; color: #742a2a; }
  </style>
</head>
<body>
  <div class="card">
    <h2>سند #{{ doc.id }} — {{ doc.subject or 'بدون موضوع' }}</h2>
    <p>کد پکیج: <strong>{{ doc.package_code or '(ثبت نشده)' }}</strong></p>
    <p>مرحله: <span class="badge">{{ doc.stage or 'draft' }}</span></p>
  </div>

  <div class="card">
    <h2>آپلود فایل جدید</h2>
    <form id="upload-form">
      <div class="row">
        <input type="file" id="file-input" name="file" required>
        <select id="kind-input">
          <option value="letter">نامه</option>
          <option value="scan">اسکن</option>
          <option value="evidence">مدرک</option>
          <option value="other" selected>سایر</option>
        </select>
        <button type="submit">آپلود</button>
      </div>
      <progress id="progress" value="0" max="100" style="width:100%"></progress>
      <div id="upload-result"></div>
    </form>
  </div>

  <div class="card">
    <h2>پیوست‌های موجود</h2>
    <div id="list-area">در حال بارگذاری...</div>
  </div>

  <div class="card" id="preview-card" style="display:none">
    <h2>پیش‌نمایش</h2>
    <div id="preview-area"></div>
  </div>

<script>
const DOC_ID = {{ doc.id }};
const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]').content;

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
}

async function loadList() {
  const area = document.getElementById('list-area');
  area.textContent = 'در حال بارگذاری...';
  try {
    const res = await fetch(`/documents/${DOC_ID}/attachments.json`);
    const data = await res.json();
    if (!data.ok) throw new Error(data.message || 'خطا');
    if (data.attachments.length === 0) {
      area.textContent = 'هنوز فایلی پیوست نشده است.';
      return;
    }
    let html = '<table><thead><tr>'
      + '<th>نام</th><th>حجم</th><th>نوع</th><th>عملیات</th>'
      + '</tr></thead><tbody>';
    for (const a of data.attachments) {
      const previewBtn = a.previewable
        ? `<button onclick="preview(${a.id}, '${escapeHtml(a.mime)}')">پیش‌نمایش</button>`
        : '<span class="badge">بدون پیش‌نمایش</span>';
      html += `<tr>
        <td>${escapeHtml(a.name)}</td>
        <td>${escapeHtml(a.size_human)}</td>
        <td>${escapeHtml(a.mime)}</td>
        <td>
          ${previewBtn}
          <a href="/documents/attachments/${a.id}/download"><button class="secondary">دانلود</button></a>
          <button class="danger" onclick="del(${a.id})">حذف</button>
        </td>
      </tr>`;
    }
    html += '</tbody></table>';
    area.innerHTML = html;
  } catch (e) {
    area.innerHTML = `<div class="msg msg-err">خطا: ${escapeHtml(e.message)}</div>`;
  }
}

function preview(id, mime) {
  const card = document.getElementById('preview-card');
  const area = document.getElementById('preview-area');
  card.style.display = 'block';
  if (mime.startsWith('image/')) {
    area.innerHTML = `<img src="/documents/attachments/${id}/preview" alt="preview">`;
  } else if (mime.startsWith('video/')) {
    area.innerHTML = `<video controls src="/documents/attachments/${id}/preview"></video>`;
  } else if (mime.startsWith('audio/')) {
    area.innerHTML = `<audio controls src="/documents/attachments/${id}/preview"></audio>`;
  } else if (mime === 'application/pdf' || mime.startsWith('text/')) {
    area.innerHTML = `<iframe src="/documents/attachments/${id}/preview" style="width:100%;height:600px"></iframe>`;
  } else {
    area.innerHTML = '<div class="msg msg-err">این نوع فایل قابل پیش‌نمایش نیست. لطفاً دانلود کنید.</div>';
  }
}

async function del(id) {
  if (!confirm('پیوست حذف شود؟')) return;
  try {
    const res = await fetch(`/documents/attachments/${id}/delete`, {method:'POST'});
    const data = await res.json();
    if (!data.ok) throw new Error(data.message || 'خطا');
    loadList();
  } catch (e) {
    alert('خطا: ' + e.message);
  }
}

document.getElementById('upload-form').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const fileInput = document.getElementById('file-input');
  const kindInput = document.getElementById('kind-input');
  const progress = document.getElementById('progress');
  const result = document.getElementById('upload-result');
  if (!fileInput.files[0]) return;

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  formData.append('kind', kindInput.value);

  result.innerHTML = '';
  progress.style.display = 'block';
  progress.value = 0;

  const xhr = new XMLHttpRequest();
  xhr.open('POST', `/documents/${DOC_ID}/attachments/upload`);
  xhr.setRequestHeader('X-CSRFToken', CSRF_TOKEN);

  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable) {
      progress.value = Math.round((e.loaded / e.total) * 100);
    }
  };
  xhr.onload = () => {
    progress.style.display = 'none';
    try {
      const data = JSON.parse(xhr.responseText);
      if (xhr.status >= 200 && xhr.status < 300 && data.ok) {
        result.innerHTML = `<div class="msg msg-ok">✅ آپلود شد: ${escapeHtml(data.attachment.name)} (${escapeHtml(data.attachment.size_human)})</div>`;
        fileInput.value = '';
        loadList();
      } else {
        result.innerHTML = `<div class="msg msg-err">خطا ${xhr.status}: ${escapeHtml(data.message || 'ناشناخته')}</div>`;
      }
    } catch {
      result.innerHTML = `<div class="msg msg-err">پاسخ نامعتبر از سرور: ${escapeHtml(xhr.responseText.slice(0, 200))}</div>`;
    }
  };
  xhr.onerror = () => {
    progress.style.display = 'none';
    result.innerHTML = `<div class="msg msg-err">خطای شبکه</div>`;
  };
  xhr.send(formData);
});

loadList();
</script>
</body>
</html>
"""

@documents_bp.route("/attachments/test-page/<int:document_id>", methods=["GET"])
def attachment_test_page(document_id):
    """صفحه‌ی تست HTML — فقط در حالت DEBUG."""
    if not Config.DEBUG:
        abort(404)
    doc = _require_access_to_document(document_id)
    return render_template_string(_TEST_PAGE, doc=doc)