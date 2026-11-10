"""سرویس پکیج سند — ثبت، شماره‌گذاری، انتقال مرحله، بستن/آرشیو.

قواعد:
- شماره‌گذاری اتمیک با BEGIN IMMEDIATE روی document_counters
- هر عملیات باید یک رویداد در document_events ثبت کند
- انتقال‌های مجاز در STAGE_TRANSITIONS تعریف شده‌اند
- ثبت سند → stage = 'registered'
- بستن سند → stage = 'closed'
- آرشیو → stage = 'archived'
"""

from datetime import datetime

import jdatetime

from config import Config
from database.connection import get_connection
from helpers.date_helper import now_tehran_str

from . import event_service


# ============================================================
# ★ مراحل چرخه‌ی عمر
# ============================================================
class Stage:
    DRAFT = "draft"
    REGISTERED = "registered"
    ROUTED = "routed"
    IN_PROGRESS = "in_progress"
    AWAITING_CONTRACTOR = "awaiting_contractor"
    UNDER_REVIEW = "under_review"
    CLOSED = "closed"
    ARCHIVED = "archived"
    REOPENED = "reopened"
    CANCELLED = "cancelled"


#: انتقال‌های مجاز
STAGE_TRANSITIONS = {
    Stage.DRAFT: [Stage.REGISTERED, Stage.CANCELLED],
    Stage.REGISTERED: [Stage.ROUTED, Stage.CANCELLED],
    Stage.ROUTED: [Stage.IN_PROGRESS, Stage.CANCELLED],
    Stage.IN_PROGRESS: [
        Stage.AWAITING_CONTRACTOR, Stage.UNDER_REVIEW, Stage.CLOSED,
    ],
    Stage.AWAITING_CONTRACTOR: [Stage.IN_PROGRESS, Stage.CANCELLED],
    Stage.UNDER_REVIEW: [Stage.CLOSED, Stage.IN_PROGRESS],
    Stage.CLOSED: [Stage.ARCHIVED, Stage.REOPENED],
    Stage.REOPENED: [Stage.IN_PROGRESS, Stage.CLOSED],
    Stage.ARCHIVED: [],
    Stage.CANCELLED: [],
}


# ============================================================
# ★ شماره‌گذاری اتمیک (اصلاح‌شده)
# ============================================================
def allocate_package_code(connection):
    """
    تخصیص شماره‌ی پکیج به شکل DFC-YYYY-NNNN.

    ★ این تابع خودش تراکنش را شروع و commit می‌کند.

    Returns:
        (code: str, year: int, value: int)
    """
    year = jdatetime.date.today().year

    # ★ شروع تراکنش و commit داخل همین تابع
    connection.execute("BEGIN IMMEDIATE")
    try:
        row = connection.execute(
            "SELECT last_value FROM document_counters WHERE year = ?",
            (year,),
        ).fetchone()

        next_value = (row["last_value"] if row else 0) + 1

        connection.execute("""
            INSERT INTO document_counters(year, last_value) VALUES (?, ?)
            ON CONFLICT(year) DO UPDATE SET last_value = excluded.last_value
        """, (year, next_value))

        connection.commit()
        code = f"DFC-{year}-{next_value:04d}"
        return code, year, next_value
    except Exception:
        connection.rollback()
        raise


# ============================================================
# ★ ثبت سند جدید
# ============================================================
def register_document(
    *,
    subject: str,
    registered_by: int,
    date_received: str | None = None,
    group_id: int | None = None,
    subgroup_id: int | None = None,
    source_type: str = "other",
    source_department_id: int | None = None,
    sender_name: str | None = None,
    sender_ref_no: str | None = None,
    sender_ref_date: str | None = None,
    contract_number: str | None = None,
    priority: str = "normal",
    confidentiality: str = "internal",
    contractor_id: int | None = None,
    project_id: int | None = None,
    area_id: int | None = None,
    department_id: int | None = None,
    user_id: int | None = None,
    description: str | None = None,
) -> dict:
    """ثبت یک سند جدید در دیتابیس."""
    if not subject or not subject.strip():
        return {"ok": False, "error": "موضوع سند الزامی است"}

    if not registered_by:
        return {"ok": False, "error": "کاربر ثبت‌کننده مشخص نیست"}

    date_received_clean = _normalize_date(date_received) or _today_gregorian()
    now = now_tehran_str()

    connection = get_connection()
    try:
        code, year, value = allocate_package_code(connection)

        cursor = connection.execute("""
            INSERT INTO documents (
                subject, date_received,
                group_id, subgroup_id,
                source_type, source_department_id,
                sender_name, sender_ref_no, sender_ref_date,
                contract_number,
                priority, confidentiality,
                contractor_id, project_id,
                area_id, department_id, user_id,
                package_code, package_year,
                stage, registered_by, registered_at,
                direction
            ) VALUES (
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?,
                ?,
                ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                ?
            )
        """, (
            subject.strip(), date_received_clean,
            group_id, subgroup_id,
            source_type, source_department_id,
            sender_name, sender_ref_no, sender_ref_date,
            contract_number,
            priority, confidentiality,
            contractor_id, project_id,
            area_id, department_id, user_id,
            code, year,
            Stage.REGISTERED, registered_by, now,
            "incoming",
        ))
        document_id = cursor.lastrowid
        connection.commit()
    except Exception as exc:
        connection.rollback()
        return {"ok": False, "error": f"خطا در ثبت سند: {exc}"}
    finally:
        connection.close()

    # رویداد
    try:
        event_service.log_event(
            document_id=document_id,
            actor_id=registered_by,
            event_type=event_service.EventType.REGISTERED,
            summary=f"سند با کد {code} ثبت شد",
            payload={
                "package_code": code,
                "package_year": year,
                "package_value": value,
                "subject": subject,
                "contract_number": contract_number,
            },
        )
    except Exception:
        pass

    # SLA
    try:
        from .sla_service import recalculate_sla
        recalculate_sla(document_id, actor_id=registered_by)
    except ImportError:
        pass
    except Exception:
        pass

    return {
        "ok": True,
        "document_id": document_id,
        "package_code": code,
        "package_year": year,
        "package_value": value,
    }


# ============================================================
# ★ تغییر مرحله
# ============================================================
def change_stage(
    document_id: int,
    new_stage: str,
    actor_id: int,
    *,
    reason: str | None = None,
    payload_extra: dict | None = None,
) -> dict:
    """
    تغییر مرحله‌ی سند با بررسی مجاز بودن انتقال.
    """
    if new_stage not in {v for vals in STAGE_TRANSITIONS.values() for v in vals} | set(STAGE_TRANSITIONS.keys()):
        return {"ok": False, "error": f"مرحله‌ی نامعتبر: {new_stage}"}

    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT stage FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
        if not row:
            return {"ok": False, "error": "سند پیدا نشد"}

        current_stage = row["stage"] or Stage.DRAFT
        allowed = STAGE_TRANSITIONS.get(current_stage, [])
        if new_stage not in allowed:
            return {
                "ok": False,
                "error": f"انتقال از {current_stage} به {new_stage} مجاز نیست",
            }

        now = now_tehran_str()
        extra_cols = ""
        extra_vals = []

        if new_stage == Stage.CLOSED:
            extra_cols += ", closed_by = ?, closed_at = ?"
            extra_vals += [actor_id, now]
        elif new_stage == Stage.ARCHIVED:
            extra_cols += ", archived_by = ?, archived_at = ?"
            extra_vals += [actor_id, now]
            if reason:
                extra_cols += ", archive_reason = ?"
                extra_vals.append(reason)
        elif new_stage == Stage.REOPENED:
            extra_cols += ", reopen_count = COALESCE(reopen_count, 0) + 1"
        elif new_stage == Stage.CANCELLED:
            extra_cols += ", closed_by = ?, closed_at = ?"
            extra_vals += [actor_id, now]

        connection.execute(
            f"UPDATE documents SET stage = ?{extra_cols} WHERE id = ?",
            [new_stage] + extra_vals + [document_id],
        )
        connection.commit()
    finally:
        connection.close()

    # رویداد
    try:
        payload = {
            "from_stage": current_stage,
            "to_stage": new_stage,
        }
        if reason:
            payload["reason"] = reason
        if payload_extra:
            payload.update(payload_extra)

        event_service.log_event(
            document_id=document_id,
            actor_id=actor_id,
            event_type=event_service.EventType.STAGE_CHANGED,
            summary=f"مرحله از «{current_stage}» به «{new_stage}» تغییر کرد",
            payload=payload,
        )
    except Exception:
        pass

    return {
        "ok": True,
        "from_stage": current_stage,
        "to_stage": new_stage,
    }


# ============================================================
# ★ کمکی‌های تاریخ
# ============================================================
def _today_gregorian() -> str:
    return datetime.now().strftime("%Y/%m/%d")


def _normalize_date(value: str | None) -> str | None:
    """تبدیل تاریخ شمسی یا میلادی به میلادی YYYY/MM/DD."""
    if not value:
        return None
    from helpers.date_helper import DateHelper
    return DateHelper.convert_to_gregorian(value)


# ============================================================
# ★ خواندن پکیج (برای صفحه‌ی /documents/<id>)
# ============================================================
def get_package(document_id: int) -> dict | None:
    """خواندن کامل سند با اطلاعات مرتبط."""
    connection = get_connection()
    try:
        row = connection.execute("""
            SELECT d.*,
                   s.title AS status_title, s.color AS status_color,
                   a.title AS area_title,
                   dep.title AS department_title,
                   g.title AS group_title,
                   sg.title AS subgroup_title,
                   c.name AS contractor_name,
                   p.name AS project_name_full,
                   u.full_name AS registered_by_name,
                   u.avatar AS registered_by_avatar
            FROM documents d
            LEFT JOIN document_statuses s ON s.id = d.status_id
            LEFT JOIN areas a ON a.id = d.area_id
            LEFT JOIN departments dep ON dep.id = d.department_id
            LEFT JOIN document_groups g ON g.id = d.group_id
            LEFT JOIN document_subgroups sg ON sg.id = d.subgroup_id
            LEFT JOIN contractors c ON c.id = d.contractor_id
            LEFT JOIN projects p ON p.id = d.project_id
            LEFT JOIN users u ON u.id = d.registered_by
            WHERE d.id = ?
        """, (document_id,)).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()