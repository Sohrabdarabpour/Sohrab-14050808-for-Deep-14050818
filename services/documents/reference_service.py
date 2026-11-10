"""سرویس نامه‌ها و رفرنس‌ها (document_references).

قابلیت‌ها:
- ثبت نامه وارده/صادره/داخلی
- ثبت تماس تلفنی، جلسه، ایمیل، شفاهی
- زنجیره‌ی نامه و پاسخ (response_to_id)
- اتصال به پیوست‌ها
"""

from datetime import datetime

from database.connection import get_connection
from services.documents import event_service


# ============================================================
# ★ انواع رفرنس
# ============================================================
class RefType:
    INCOMING_LETTER = "incoming_letter"
    OUTGOING_LETTER = "outgoing_letter"
    VERBAL_REQUEST = "verbal_request"
    PHONE_CALL = "phone_call"
    MEETING = "meeting"
    EMAIL = "email"
    TRANSMITTAL = "transmittal"
    COMPLETION_REQUEST = "completion_request"
    COMPLETION_RESPONSE = "completion_response"
    REMINDER = "reminder"
    OTHER = "other"


#: تنظیمات پیش‌فرض برای هر نوع رفرنس
REF_TYPE_META = {
    RefType.INCOMING_LETTER: {
        "direction": "in", "is_official": 1, "channel": "letter",
        "label": "نامه وارده"
    },
    RefType.OUTGOING_LETTER: {
        "direction": "out", "is_official": 1, "channel": "letter",
        "label": "نامه صادره"
    },
    RefType.VERBAL_REQUEST: {
        "direction": "in", "is_official": 0, "channel": "verbal",
        "label": "درخواست شفاهی"
    },
    RefType.PHONE_CALL: {
        "direction": "in", "is_official": 0, "channel": "phone",
        "label": "تماس تلفنی"
    },
    RefType.MEETING: {
        "direction": "internal", "is_official": 0, "channel": "meeting",
        "label": "جلسه"
    },
    RefType.EMAIL: {
        "direction": "in", "is_official": 0, "channel": "email",
        "label": "ایمیل"
    },
    RefType.TRANSMITTAL: {
        "direction": "out", "is_official": 1, "channel": "letter",
        "label": "ترانسمیتال"
    },
    RefType.COMPLETION_REQUEST: {
        "direction": "out", "is_official": 1, "channel": "letter",
        "label": "درخواست تکمیل مدارک"
    },
    RefType.COMPLETION_RESPONSE: {
        "direction": "in", "is_official": 1, "channel": "letter",
        "label": "پاسخ تکمیل مدارک"
    },
    RefType.REMINDER: {
        "direction": "out", "is_official": 0, "channel": "letter",
        "label": "یادآوری"
    },
    RefType.OTHER: {
        "direction": "in", "is_official": 0, "channel": "other",
        "label": "سایر"
    },
}


# ============================================================
# ★ ثبت رفرنس
# ============================================================
def create_reference(
    document_id: int,
    ref_type: str,
    created_by: int,
    *,
    direction: str | None = None,
    is_official: int | None = None,
    channel: str | None = None,
    ref_no: str | None = None,
    ref_date: str | None = None,
    party_type: str | None = None,
    contractor_id: int | None = None,
    department_id: int | None = None,
    person_name: str | None = None,
    subject: str | None = None,
    summary: str | None = None,
    outcome: str | None = None,
    response_to_id: int | None = None,
    assignment_id: int | None = None,
) -> dict:
    """ثبت یک رفرنس جدید (نامه، تماس، جلسه و...) برای یک سند."""
    if not document_id:
        return {"ok": False, "error": "شناسه سند الزامی است"}
    if not ref_type:
        return {"ok": False, "error": "نوع رفرنس الزامی است"}

    meta = REF_TYPE_META.get(ref_type, REF_TYPE_META[RefType.OTHER])

    direction = direction or meta["direction"]
    is_official = meta["is_official"] if is_official is None else is_official
    channel = channel or meta["channel"]

    connection = get_connection()
    try:
        cursor = connection.execute("""
            INSERT INTO document_references (
                document_id, assignment_id,
                ref_type, direction, is_official, channel,
                ref_no, ref_date,
                party_type, contractor_id, department_id, person_name,
                subject, summary, outcome,
                response_to_id, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            document_id, assignment_id,
            ref_type, direction, is_official, channel,
            ref_no, ref_date,
            party_type, contractor_id, department_id, person_name,
            subject, summary, outcome,
            response_to_id, created_by,
        ))
        connection.commit()
        ref_id = cursor.lastrowid
    except Exception as exc:
        connection.rollback()
        return {"ok": False, "error": f"خطا در ثبت: {exc}"}
    finally:
        connection.close()

    # ★ ثبت رویداد
    try:
        label = meta["label"]
        event_service.log_event(
            document_id=document_id,
            actor_id=created_by,
            event_type=event_service.EventType.REFERENCE_ADDED,
            summary=f"{label} ثبت شد" + (f": {subject}" if subject else ""),
            payload={
                "ref_id": ref_id,
                "ref_type": ref_type,
                "subject": subject,
                "ref_no": ref_no,
            },
        )
    except Exception:
        pass

    return {"ok": True, "reference_id": ref_id}


# ============================================================
# ★ لیست رفرنس‌های یک سند
# ============================================================
def list_references(document_id: int) -> list[dict]:
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT r.*,
                   c.name AS contractor_name,
                   d.title AS department_title,
                   u.full_name AS created_by_name,
                   resp.ref_type AS response_to_type,
                   resp.ref_no AS response_to_no
            FROM document_references r
            LEFT JOIN contractors c ON c.id = r.contractor_id
            LEFT JOIN departments d ON d.id = r.department_id
            LEFT JOIN users u ON u.id = r.created_by
            LEFT JOIN document_references resp ON resp.id = r.response_to_id
            WHERE r.document_id = ?
            ORDER BY r.created_at DESC, r.id DESC
        """, (document_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()