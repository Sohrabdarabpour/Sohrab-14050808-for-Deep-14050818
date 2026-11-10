"""سرویس ذخیره‌سازی فایل‌های پکیج سند.

ویژگی‌ها:
- آپلود استریمی (تکه‌تکه) — بدون بارگذاری کامل در RAM
- محاسبه‌ی SHA-256 هنگام نوشتن
- نام‌گذاری UUID برای جلوگیری از تصادم و path traversal
- ذخیره در instance/uploads/<document_id>/
- تشخیص نوع فایل و previewable
- حذف امن فایل
"""

import hashlib
import mimetypes
import os
import uuid

from config import Config
from database.connection import get_connection


# ============================================================
# ★ مسیرهای امن
# ============================================================
def _document_dir(document_id: int) -> str:
    """مسیر پوشه‌ی سند؛ ساخته می‌شود اگر نبود."""
    path = os.path.join(Config.DOCUMENT_UPLOAD_ROOT, str(document_id))
    os.makedirs(path, exist_ok=True)
    return path


def _safe_ext(filename: str) -> str:
    """پسوند ایمن (بدون dot، lowercase)."""
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def is_allowed(filename: str) -> bool:
    ext = _safe_ext(filename)
    return bool(ext) and ext in Config.ALLOWED_UPLOAD_EXTENSIONS


def is_previewable(filename: str, mime: str | None = None) -> bool:
    ext = _safe_ext(filename)
    if ext in Config.PREVIEWABLE_EXTENSIONS:
        return True
    if mime:
        if mime.startswith(("image/", "video/", "audio/")):
            return True
        if mime in ("application/pdf", "text/plain", "text/csv"):
            return True
    return False


def _guess_mime(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


# ============================================================
# ★ آپلود استریمی
# ============================================================
def save_stream(
    document_id: int,
    file_storage,
    kind: str = "other",
    reference_id: int | None = None,
    uploaded_by: int | None = None,
) -> dict:
    """
    ذخیره‌ی فایل به‌صورت استریمی.

    Args:
        document_id: شناسه سند
        file_storage: شیء werkzeug FileStorage (request.files['file'])
        kind: نوع پیوست (letter | scan | evidence | other)
        reference_id: اگر مربوط به یک رفرنس است
        uploaded_by: شناسه کاربر آپلودکننده

    Returns:
        dict با اطلاعات فایل ذخیره‌شده

    Raises:
        ValueError: اگر پسوند مجاز نباشد یا حجم بیش از حد مجاز باشد
    """
    original_name = (file_storage.filename or "").strip()
    if not original_name:
        raise ValueError("نام فایل خالی است")

    if not is_allowed(original_name):
        raise ValueError(
            f"پسوند فایل مجاز نیست: {_safe_ext(original_name) or 'بدون پسوند'}"
        )

    ext = _safe_ext(original_name)
    stored_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    folder = _document_dir(document_id)
    filepath = os.path.join(folder, stored_name)

    # ---- نوشتن استریمی + محاسبه‌ی SHA-256 ----
    hasher = hashlib.sha256()
    total_size = 0
    chunk_size = 1024 * 1024  # 1MB

    try:
        with open(filepath, "wb") as out:
            while True:
                chunk = file_storage.stream.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
                out.write(chunk)
                total_size += len(chunk)

                if (Config.MAX_UPLOAD_SIZE_BYTES is not None
                        and total_size > Config.MAX_UPLOAD_SIZE_BYTES):
                    out.close()
                    os.remove(filepath)
                    raise ValueError(
                        f"حجم فایل بیشتر از حد مجاز "
                        f"({Config.MAX_UPLOAD_SIZE_BYTES} بایت) است"
                    )
    except Exception:
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass
        raise

    mime = _guess_mime(original_name)
    previewable = 1 if is_previewable(original_name, mime) else 0

    # ---- ثبت در دیتابیس ----
    connection = get_connection()
    try:
        cursor = connection.execute("""
            INSERT INTO document_attachments
            (document_id, reference_id, original_name, stored_name,
             mime, size, sha256, kind, previewable, uploaded_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            document_id, reference_id, original_name, stored_name,
            mime, total_size, hasher.hexdigest(), kind, previewable,
            uploaded_by,
        ))
        connection.commit()
        attachment_id = cursor.lastrowid
    finally:
        connection.close()

    return {
        "id": attachment_id,
        "document_id": document_id,
        "original_name": original_name,
        "stored_name": stored_name,
        "mime": mime,
        "size": total_size,
        "sha256": hasher.hexdigest(),
        "previewable": bool(previewable),
        "path": filepath,
    }


# ============================================================
# ★ خواندن / حذف / لیست
# ============================================================
def get_attachment(attachment_id: int) -> dict | None:
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM document_attachments WHERE id = ?",
            (attachment_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def list_attachments(document_id: int) -> list[dict]:
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT * FROM document_attachments
            WHERE document_id = ?
            ORDER BY created_at DESC, id DESC
        """, (document_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


def absolute_path(attachment: dict) -> str:
    folder = os.path.join(
        Config.DOCUMENT_UPLOAD_ROOT, str(attachment["document_id"])
    )
    return os.path.join(folder, attachment["stored_name"])


def delete_attachment(attachment_id: int) -> dict | None:
    """حذف پیوست — برمی‌گرداند اطلاعات فایل حذف‌شده یا None."""
    attachment = get_attachment(attachment_id)
    if not attachment:
        return None

    filepath = absolute_path(attachment)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except OSError:
        pass

    connection = get_connection()
    try:
        connection.execute(
            "DELETE FROM document_attachments WHERE id = ?",
            (attachment_id,),
        )
        connection.commit()
    finally:
        connection.close()

    return attachment


def human_size(size: int) -> str:
    """نمایش خوانا از حجم."""
    if size is None:
        return "-"
    size = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"