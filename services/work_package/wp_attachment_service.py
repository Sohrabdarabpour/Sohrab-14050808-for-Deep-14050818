"""سرویس پیوست‌های پکیج سند.

مسیر ذخیره: instance/uploads/packages/<dfc_code>/<uuid>.<ext>
"""

import hashlib
import mimetypes
import os
import uuid

from config import Config
from database.connection import get_connection


# ============================================================
# ★ تنظیمات
# ============================================================
# اگر ALLOWED_UPLOAD_EXTENSIONS در Config نبود، از این استفاده می‌شود
_DEFAULT_ALLOWED = {
    "pdf", "doc", "docx", "docm", "xls", "xlsx", "xlsm",
    "ppt", "pptx", "pptm", "txt", "csv", "rtf", "odt", "ods",
    "jpg", "jpeg", "jfif", "png", "gif", "bmp", "webp", "svg",
    "heic", "heif", "tiff", "tif",
    "mp4", "mov", "avi", "mkv", "webm", "mpg", "mpeg",
    "mp3", "wav", "ogg", "m4a", "aac",
    "zip", "rar", "7z", "tar", "gz",
    "dwg", "dxf", "step", "stp", "iges", "igs", "rvt", "ifc",
    "mpp", "vsd", "vsdx",
    "msg", "eml",
    "djvu",
}

_DEFAULT_PREVIEWABLE = {
    "pdf", "txt", "csv", "json", "xml",
    "jpg", "jpeg", "jfif", "png", "gif", "bmp", "webp", "svg",
    "tiff", "tif",
    "mp4", "webm", "mov", "m4a",
    "mp3", "wav", "ogg",
}


def _allowed_exts():
    return getattr(Config, "ALLOWED_UPLOAD_EXTENSIONS", _DEFAULT_ALLOWED)


def _previewable_exts():
    return getattr(Config, "PREVIEWABLE_EXTENSIONS", _DEFAULT_PREVIEWABLE)


# ============================================================
# ★ مسیرهای امن
# ============================================================
def _package_dir(dfc_code: str) -> str:
    """مسیر پوشه‌ی سند؛ ساخته می‌شود اگر نبود."""
    root = getattr(
        Config, "WORK_PACKAGE_UPLOAD_ROOT",
        os.path.join(Config.BASE_DIR, "instance", "uploads", "packages")
    )
    path = os.path.join(root, dfc_code)
    os.makedirs(path, exist_ok=True)
    return path


def _safe_ext(filename: str) -> str:
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def is_allowed(filename: str) -> bool:
    ext = _safe_ext(filename)
    return bool(ext) and ext in _allowed_exts()


def is_previewable(filename: str, mime: str | None = None) -> bool:
    ext = _safe_ext(filename)
    if ext in _previewable_exts():
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
    package_id: int,
    file_storage,
    *,
    kind: str = "other",
    description: str | None = None,
    uploaded_by: int | None = None,
    parent_attachment_id: int | None = None,
) -> dict:
    """
    ذخیره‌ی فایل به‌صورت استریمی.

    Args:
        package_id: شناسه پکیج سند
        file_storage: شیء werkzeug FileStorage
        kind: scan | letter | evidence | response | other
        description: توضیح
        uploaded_by: شناسه آپلودکننده
        parent_attachment_id: پیوست والد (برای نسخه‌ها)

    Returns:
        dict با اطلاعات فایل

    Raises:
        ValueError: پسوند نامجاز یا حجم بیش از حد
    """
    # خواندن DFC_CODE از دیتابیس
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT dfc_code FROM document_packages WHERE id = ?",
            (package_id,),
        ).fetchone()
        if not row:
            raise ValueError("سند پیدا نشد")
        dfc_code = row["dfc_code"]
    finally:
        connection.close()

    original_name = (file_storage.filename or "").strip()
    if not original_name:
        raise ValueError("نام فایل خالی است")
    if not is_allowed(original_name):
        raise ValueError(
            f"پسوند فایل مجاز نیست: {_safe_ext(original_name) or 'بدون پسوند'}"
        )

    ext = _safe_ext(original_name)
    stored_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    folder = _package_dir(dfc_code)
    filepath = os.path.join(folder, stored_name)

    # نوشتن استریمی + SHA-256
    hasher = hashlib.sha256()
    total_size = 0
    chunk_size = 1024 * 1024
    max_size = getattr(Config, "MAX_UPLOAD_SIZE_BYTES", None)

    try:
        with open(filepath, "wb") as out:
            while True:
                chunk = file_storage.stream.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
                out.write(chunk)
                total_size += len(chunk)

                if max_size is not None and total_size > max_size:
                    out.close()
                    os.remove(filepath)
                    raise ValueError(
                        f"حجم فایل بیش از حد مجاز ({max_size} بایت) است"
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

    # ثبت در دیتابیس
    connection = get_connection()
    try:
        cursor = connection.execute("""
            INSERT INTO document_package_attachments
            (package_id, parent_attachment_id, original_name, stored_name,
             mime, size, sha256, kind, description, previewable, uploaded_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            package_id, parent_attachment_id, original_name, stored_name,
            mime, total_size, hasher.hexdigest(), kind, description,
            previewable, uploaded_by,
        ))
        connection.commit()
        attachment_id = cursor.lastrowid
    finally:
        connection.close()

    return {
        "id": attachment_id,
        "package_id": package_id,
        "dfc_code": dfc_code,
        "original_name": original_name,
        "stored_name": stored_name,
        "mime": mime,
        "size": total_size,
        "sha256": hasher.hexdigest(),
        "previewable": bool(previewable),
        "path": filepath,
    }


# ============================================================
# ★ خواندن / حذف
# ============================================================
def get_attachment(attachment_id: int) -> dict | None:
    connection = get_connection()
    try:
        row = connection.execute("""
            SELECT a.*, p.dfc_code
            FROM document_package_attachments a
            JOIN document_packages p ON p.id = a.package_id
            WHERE a.id = ?
        """, (attachment_id,)).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def list_attachments(package_id: int) -> list[dict]:
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT a.*, u.full_name AS uploaded_by_name
            FROM document_package_attachments a
            LEFT JOIN users u ON u.id = a.uploaded_by
            WHERE a.package_id = ?
            ORDER BY a.created_at DESC, a.id DESC
        """, (package_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


def absolute_path(attachment: dict) -> str:
    folder = _package_dir(attachment["dfc_code"])
    return os.path.join(folder, attachment["stored_name"])


def delete_attachment(attachment_id: int) -> dict | None:
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
            "DELETE FROM document_package_attachments WHERE id = ?",
            (attachment_id,),
        )
        connection.commit()
    finally:
        connection.close()

    return attachment


def human_size(size: int) -> str:
    if size is None:
        return "-"
    size = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"