"""سرویس رویدادهای پکیج سند (document_package_events).

قاعده‌ی طلایی: هر عملیاتی که روی سند انجام می‌شود، باید یک ردیف اینجا بنویسد.
UPDATE و DELETE ممنوع است.
"""

import json

from database.connection import get_connection


# ============================================================
# ★ انواع رویداد
# ============================================================
class EventType:
    REGISTERED = "registered"
    SENT_TO_MANAGEMENT = "sent_to_management"
    RETURNED_FROM_MANAGEMENT = "returned_from_management"
    ROUTED_TO_SUPERVISOR = "routed_to_supervisor"
    ROUTED_TO_EXPERT = "routed_to_expert"
    EXPERT_ACCEPTED = "expert_accepted"
    DEFICIENCY_REQUESTED = "deficiency_requested"
    DEFICIENCY_FULFILLED = "deficiency_fulfilled"
    RESPONSE_PREPARED = "response_prepared"
    RESPONSE_APPROVED_BY_SUPERVISOR = "response_approved_by_supervisor"
    RESPONSE_APPROVED_BY_MANAGEMENT = "response_approved_by_management"
    RESPONSE_SENT = "response_sent"
    FINALIZED = "finalized"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"
    ATTACHMENT_ADDED = "attachment_added"
    ATTACHMENT_DELETED = "attachment_deleted"
    SLA_RECALCULATED = "sla_recalculated"
    OVERDUE_DETECTED = "overdue_detected"
    STAGE_CHANGED = "stage_changed"


# ============================================================
# ★ ثبت رویداد
# ============================================================
def log_event(
    package_id: int,
    actor_id: int | None,
    event_type: str,
    summary: str | None = None,
    payload: dict | None = None,
    assignment_id: int | None = None,
) -> int | None:
    """ثبت یک رویداد در تایم‌لاین."""
    if not package_id or not event_type:
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
            INSERT INTO document_package_events
            (package_id, actor_id, event_type, summary, payload, assignment_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            package_id, actor_id, event_type,
            summary, payload_json, assignment_id,
        ))
        connection.commit()
        return cursor.lastrowid
    except Exception:
        connection.rollback()
        return None
    finally:
        connection.close()


# ============================================================
# ★ خواندن
# ============================================================
def list_events(package_id: int, limit: int = 200) -> list[dict]:
    """دریافت تایم‌لاین سند (جدیدترین اول)."""
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT e.*,
                   u.full_name AS actor_name,
                   u.avatar AS actor_avatar,
                   u.username AS actor_username
            FROM document_package_events e
            LEFT JOIN users u ON u.id = e.actor_id
            WHERE e.package_id = ?
            ORDER BY e.created_at DESC, e.id DESC
            LIMIT ?
        """, (package_id, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()