"""سرویس رویدادها — تایم‌لاین غیرقابل‌تغییر سند.

قاعده‌ی طلایی: هر عملیاتی که روی سند انجام می‌شود، باید یک ردیف در
document_events بنویسد. UPDATE و DELETE روی این جدول ممنوع است.
"""

import json
from datetime import datetime

from database.connection import get_connection
from helpers.date_helper import now_tehran_str


def log_event(
    document_id: int,
    actor_id: int | None,
    event_type: str,
    summary: str | None = None,
    payload: dict | None = None,
    assignment_id: int | None = None,
) -> int | None:
    """
    ثبت یک رویداد در تایم‌لاین سند.

    Args:
        document_id: شناسه سند (اجباری)
        actor_id: شناسه کاربر انجام‌دهنده (می‌تواند None باشد برای سیستم)
        event_type: نوع رویداد (از لیست ثابت زیر)
        summary: متن کوتاه برای نمایش
        payload: دیکشنری جزئیات (به JSON تبدیل می‌شود)
        assignment_id: اگر رویداد مربوط به یک ارجاع است

    Returns:
        id رویداد ثبت‌شده یا None در خطا
    """
    if not document_id or not event_type:
        return None

    payload_json = None
    if payload:
        try:
            payload_json = json.dumps(payload, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            payload_json = None

    connection = get_connection()
    try:
        cursor = connection.execute("""
            INSERT INTO document_events
            (document_id, actor_id, event_type, summary, payload, assignment_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            document_id, actor_id, event_type,
            summary, payload_json, assignment_id,
        ))
        connection.commit()
        return cursor.lastrowid
    except Exception:
        connection.rollback()
        return None
    finally:
        connection.close()


def list_events(document_id: int, limit: int = 200) -> list[dict]:
    """دریافت تایم‌لاین سند (جدیدترین اول)."""
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT e.*,
                   u.full_name AS actor_name,
                   u.avatar AS actor_avatar,
                   u.username AS actor_username
            FROM document_events e
            LEFT JOIN users u ON u.id = e.actor_id
            WHERE e.document_id = ?
            ORDER BY e.created_at DESC, e.id DESC
            LIMIT ?
        """, (document_id, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


# ============================================================
# ★ لیست ثابت انواع رویداد (برای جلوگیری از اشتباه تایپی)
# ============================================================
class EventType:
    REGISTERED = "registered"
    ROUTED = "routed"
    REFERRED = "referred"
    ACCEPTED = "accepted"
    STARTED = "started"
    RETURNED = "returned"
    COMPLETED = "completed"

    LETTER_ADDED = "letter_added"
    REFERENCE_ADDED = "reference_added"

    COMPLETION_REQUESTED = "completion_requested"
    COMPLETION_FULFILLED = "completion_fulfilled"

    ATTACHMENT_ADDED = "attachment_added"
    ATTACHMENT_DELETED = "attachment_deleted"

    STATUS_CHANGED = "status_changed"
    STAGE_CHANGED = "stage_changed"

    SLA_RECALCULATED = "sla_recalculated"
    OVERDUE_DETECTED = "overdue_detected"

    CLOSED = "closed"
    ARCHIVED = "archived"
    REOPENED = "reopened"
    CANCELLED = "cancelled"

    COMMENTED = "commented"