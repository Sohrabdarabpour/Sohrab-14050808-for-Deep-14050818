"""سرویس اصلی پکیج سند — تخصیص DFC/WP، ثبت، تغییر مرحله، خواندن."""

from datetime import datetime

import jdatetime

from database.connection import get_connection
from helpers.date_helper import now_tehran_str

from . import wp_event_service


# ============================================================
# ★ مراحل چرخه عمر
# ============================================================
class Stage:
    REGISTERED = "registered"
    SENT_TO_MANAGEMENT = "sent_to_management"
    RETURNED_FROM_MANAGEMENT = "returned_from_management"
    ROUTED = "routed"
    IN_PROGRESS = "in_progress"
    AWAITING_CONTRACTOR = "awaiting_contractor"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    CLOSED = "closed"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"


STAGE_TRANSITIONS = {
    Stage.REGISTERED: [Stage.SENT_TO_MANAGEMENT, Stage.CANCELLED],
    Stage.SENT_TO_MANAGEMENT: [Stage.RETURNED_FROM_MANAGEMENT, Stage.CANCELLED],
    Stage.RETURNED_FROM_MANAGEMENT: [Stage.ROUTED, Stage.CANCELLED],
    Stage.ROUTED: [Stage.IN_PROGRESS, Stage.CANCELLED],
    Stage.IN_PROGRESS: [
        Stage.AWAITING_CONTRACTOR, Stage.UNDER_REVIEW, Stage.CANCELLED,
    ],
    Stage.AWAITING_CONTRACTOR: [Stage.IN_PROGRESS, Stage.CANCELLED],
    Stage.UNDER_REVIEW: [Stage.APPROVED, Stage.IN_PROGRESS],
    Stage.APPROVED: [Stage.CLOSED, Stage.IN_PROGRESS],
    Stage.CLOSED: [Stage.ARCHIVED],
    Stage.ARCHIVED: [],
    Stage.CANCELLED: [],
}


# ============================================================
# ★ تخصیص شمارنده‌ی اتمیک
# ============================================================
def _allocate_counter(connection, kind: str, year: int) -> int:
    """تخصیص مقدار بعدی برای (kind, year). اتمیک."""
    connection.execute("BEGIN IMMEDIATE")
    try:
        row = connection.execute(
            "SELECT last_value FROM document_package_counters "
            "WHERE kind = ? AND year = ?",
            (kind, year),
        ).fetchone()

        next_value = (row["last_value"] if row else 0) + 1

        connection.execute("""
            INSERT INTO document_package_counters (kind, year, last_value)
            VALUES (?, ?, ?)
            ON CONFLICT(kind, year) DO UPDATE SET last_value = excluded.last_value
        """, (kind, year, next_value))

        connection.commit()
        return next_value
    except Exception:
        connection.rollback()
        raise


# ============================================================
# ★ تشخیص WP موجود
# ============================================================
def find_work_package(
    *,
    reference_no: str | None = None,
    sender_ref_no: str | None = None,
    contract_number: str | None = None,
    contractor_id: int | None = None,
    project_id: int | None = None,
    automation_number: str | None = None,
) -> str | None:
    """
    تلاش برای یافتن WP موجود بر اساس اولویت.
    Returns: work_package_code یا None
    """
    connection = get_connection()
    try:
        # ۱. رفرنس دقیق
        ref_values = [r for r in (reference_no, sender_ref_no) if r]
        for ref in ref_values:
            row = connection.execute("""
                SELECT work_package_code FROM document_packages
                WHERE (reference_no = ? OR sender_ref_no = ? OR dfc_code = ?)
                  AND stage NOT IN ('archived', 'cancelled')
                ORDER BY id DESC LIMIT 1
            """, (ref, ref, ref)).fetchone()
            if row:
                return row["work_package_code"]

        # ۲. شماره قرارداد + پیمانکار
        if contract_number and contractor_id:
            row = connection.execute("""
                SELECT work_package_code FROM document_packages
                WHERE contract_number = ? AND contractor_id = ?
                  AND stage NOT IN ('archived', 'cancelled')
                ORDER BY id DESC LIMIT 1
            """, (contract_number, contractor_id)).fetchone()
            if row:
                return row["work_package_code"]

        # ۳. شماره قرارداد + پروژه
        if contract_number and project_id:
            row = connection.execute("""
                SELECT work_package_code FROM document_packages
                WHERE contract_number = ? AND project_id = ?
                  AND stage NOT IN ('archived', 'cancelled')
                ORDER BY id DESC LIMIT 1
            """, (contract_number, project_id)).fetchone()
            if row:
                return row["work_package_code"]

        # ۴. شماره اتوماسیون
        if automation_number:
            row = connection.execute("""
                SELECT work_package_code FROM document_packages
                WHERE automation_number = ?
                  AND stage NOT IN ('archived', 'cancelled')
                ORDER BY id DESC LIMIT 1
            """, (automation_number,)).fetchone()
            if row:
                return row["work_package_code"]

        return None
    finally:
        connection.close()


# ============================================================
# ★ ثبت سند جدید
# ============================================================
def register_package(
    *,
    subject: str,
    registered_by: int,
    # تاریخ‌ها (میلادی — از قبل تبدیل شده)
    date_letter: str | None = None,
    date_received: str | None = None,
    sender_ref_date: str | None = None,
    date_sent_to_management: str | None = None,
    date_returned_from_management: str | None = None,
    management_date_on_letter: str | None = None,
    # اطلاعات سند
    sender_ref_no: str | None = None,
    contract_number: str | None = None,
    reference_no: str | None = None,
    automation_number: str | None = None,
    sender_name: str | None = None,
    sender_type: str = "other",
    source_type: str = "other",
    description: str | None = None,
    management_instruction: str | None = None,
    # ارتباطات
    contractor_id: int | None = None,
    project_id: int | None = None,
    group_id: int | None = None,
    subgroup_id: int | None = None,
    priority: str = "normal",
    confidentiality: str = "internal",
    # سرپرستان و کارشناسان
    supervisor_ids: list[int] | None = None,
    direct_expert_ids: list[int] | None = None,
    # رفرنس
    response_to_id: int | None = None,
    force_new_wp: bool = False,
) -> dict:
    """
    ثبت سند جدید با تخصیص DFC و WP.

    Returns:
        dict با ok, package_id, dfc_code, work_package_code, error
    """
    if not subject or not subject.strip():
        return {"ok": False, "error": "موضوع سند الزامی است"}
    if not registered_by:
        return {"ok": False, "error": "کاربر ثبت‌کننده مشخص نیست"}

    import json
    year = jdatetime.date.today().year
    now = now_tehran_str()

    connection = get_connection()
    try:
        # ★ تشخیص WP
        existing_wp = None
        if not force_new_wp:
            existing_wp = find_work_package(
                reference_no=reference_no,
                sender_ref_no=sender_ref_no,
                contract_number=contract_number,
                contractor_id=contractor_id,
                project_id=project_id,
                automation_number=automation_number,
            )

        # ★ تخصیص DFC
        dfc_value = _allocate_counter(connection, "dfc", year)
        dfc_code = f"DFC-{year}-{dfc_value:04d}"

        # ★ تخصیص یا استفاده از WP
        if existing_wp:
            wp_code = existing_wp
            # موضوع اصلی پکیج را از اولین سند بخوان
            wp_subject_row = connection.execute(
                "SELECT work_package_subject FROM document_packages "
                "WHERE work_package_code = ? AND work_package_subject IS NOT NULL "
                "ORDER BY id ASC LIMIT 1",
                (wp_code,),
            ).fetchone()
            wp_subject = wp_subject_row["work_package_subject"] if wp_subject_row else subject.strip()
        else:
            wp_value = _allocate_counter(connection, "wp", year)
            wp_code = f"WP-{year}-{wp_value:04d}"
            wp_subject = subject.strip()

        # ★ parent_package_id
        parent_id = None
        if response_to_id:
            parent_row = connection.execute(
                "SELECT parent_package_id, id FROM document_packages WHERE id = ?",
                (response_to_id,),
            ).fetchone()
            if parent_row:
                parent_id = parent_row["parent_package_id"] or parent_row["id"]

        # ★ JSON برای supervisor_ids و direct_expert_ids
        supervisor_ids_json = json.dumps(supervisor_ids or [], ensure_ascii=False)
        direct_expert_ids_json = json.dumps(direct_expert_ids or [], ensure_ascii=False)

        # ★ stage اولیه
        initial_stage = Stage.REGISTERED

        cursor = connection.execute("""
            INSERT INTO document_packages (
                dfc_code, work_package_code, package_year, dfc_sequence,
                subject, description,
                date_letter, date_received, sender_ref_date,
                sender_ref_no, contract_number, reference_no, automation_number,
                sender_name, sender_type, source_type, direction,
                contractor_id, project_id,
                date_sent_to_management, date_returned_from_management,
                management_date_on_letter, management_instruction,
                group_id, subgroup_id, priority, confidentiality,
                supervisor_ids, direct_expert_ids,
                stage, response_to_id, parent_package_id, work_package_subject,
                registered_by, registered_at
            ) VALUES (
                ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, 'incoming',
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?, ?,
                ?, ?
            )
        """, (
            dfc_code, wp_code, year, dfc_value,
            subject.strip(), description,
            date_letter, date_received, sender_ref_date,
            sender_ref_no, contract_number, reference_no, automation_number,
            sender_name, sender_type, source_type,
            contractor_id, project_id,
            date_sent_to_management, date_returned_from_management,
            management_date_on_letter, management_instruction,
            group_id, subgroup_id, priority, confidentiality,
            supervisor_ids_json, direct_expert_ids_json,
            initial_stage, response_to_id, parent_id, wp_subject,
            registered_by, now,
        ))
        package_id = cursor.lastrowid
        connection.commit()
    except Exception as exc:
        connection.rollback()
        return {"ok": False, "error": f"خطا در ثبت سند: {exc}"}
    finally:
        connection.close()

    # ★ ثبت رویداد
    try:
        wp_event_service.log_event(
            package_id=package_id,
            actor_id=registered_by,
            event_type=wp_event_service.EventType.REGISTERED,
            summary=f"سند با کد {dfc_code} در پکیج {wp_code} ثبت شد",
            payload={
                "dfc_code": dfc_code,
                "work_package_code": wp_code,
                "subject": subject,
                "existing_wp": bool(existing_wp),
            },
        )
    except Exception:
        pass

    return {
        "ok": True,
        "package_id": package_id,
        "dfc_code": dfc_code,
        "work_package_code": wp_code,
        "package_year": year,
        "dfc_sequence": dfc_value,
        "existing_wp": bool(existing_wp),
    }


# ============================================================
# ★ تغییر مرحله
# ============================================================
def change_stage(
    package_id: int,
    new_stage: str,
    actor_id: int,
    *,
    reason: str | None = None,
    extra_fields: dict | None = None,
) -> dict:
    """تغییر مرحله با بررسی مجاز بودن و به‌روزرسانی فیلدهای اضافی."""
    if new_stage not in set(STAGE_TRANSITIONS.keys()) | {
        v for vals in STAGE_TRANSITIONS.values() for v in vals
    }:
        return {"ok": False, "error": f"مرحله نامعتبر: {new_stage}"}

    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT stage FROM document_packages WHERE id = ?",
            (package_id,),
        ).fetchone()
        if not row:
            return {"ok": False, "error": "سند پیدا نشد"}

        current = row["stage"] or Stage.REGISTERED
        allowed = STAGE_TRANSITIONS.get(current, [])
        if new_stage not in allowed:
            return {
                "ok": False,
                "error": f"انتقال از {current} به {new_stage} مجاز نیست",
            }

        now = now_tehran_str()
        set_parts = ["stage = ?", "updated_at = ?"]
        values = [new_stage, now]

        # فیلدهای ویژه بر اساس مرحله
        if new_stage == Stage.CLOSED:
            set_parts += ["closed_by = ?", "closed_at = ?"]
            values += [actor_id, now]
        elif new_stage == Stage.ARCHIVED:
            set_parts += ["archived_by = ?", "archived_at = ?"]
            values += [actor_id, now]
            if reason:
                set_parts.append("archive_reason = ?")
                values.append(reason)

        # ★ فیلدهای اضافی
        if extra_fields:
            # فیلدهای مجاز
            allowed_extra = {
                "management_action",
                "management_instruction",
                "management_date_on_letter",
                "date_sent_to_management",
                "date_returned_from_management",
                "group_id",
                "subgroup_id",
                "priority",
                "confidentiality",
                "supervisor_ids",
                "direct_expert_ids",
                "date_sent_response",
                "response_letter_number",
                "response_letter_date",
                "final_response",
                "final_result",
                "final_result_notes",
            }
            for k, v in extra_fields.items():
                if k in allowed_extra:
                    set_parts.append(f"{k} = ?")
                    values.append(v)

        values.append(package_id)

        connection.execute(
            f"UPDATE document_packages SET {', '.join(set_parts)} WHERE id = ?",
            values,
        )
        connection.commit()
    finally:
        connection.close()

    # رویداد
    try:
        payload = {"from": current, "to": new_stage}
        if reason:
            payload["reason"] = reason
        if extra_fields:
            payload.update(extra_fields)

        wp_event_service.log_event(
            package_id=package_id,
            actor_id=actor_id,
            event_type=wp_event_service.EventType.STAGE_CHANGED,
            summary=f"مرحله از «{current}» به «{new_stage}» تغییر کرد",
            payload=payload,
        )
    except Exception:
        pass

    return {"ok": True, "from_stage": current, "to_stage": new_stage}


# ============================================================
# ★ خواندن
# ============================================================
def get_package(package_id: int) -> dict | None:
    connection = get_connection()
    try:
        row = connection.execute("""
            SELECT p.*,
                   c.name AS contractor_name,
                   pr.name AS project_name_full,
                   g.title AS group_title,
                   sg.title AS subgroup_title,
                   u.full_name AS registered_by_name,
                   sup.full_name AS current_supervisor_name,
                   exp.full_name AS current_expert_name,
                   parent.dfc_code AS parent_dfc_code,
                   resp.dfc_code AS response_to_dfc_code
            FROM document_packages p
            LEFT JOIN contractors c ON c.id = p.contractor_id
            LEFT JOIN projects pr ON pr.id = p.project_id
            LEFT JOIN document_groups g ON g.id = p.group_id
            LEFT JOIN document_subgroups sg ON sg.id = p.subgroup_id
            LEFT JOIN users u ON u.id = p.registered_by
            LEFT JOIN users sup ON sup.id = p.current_supervisor_id
            LEFT JOIN users exp ON exp.id = p.current_expert_id
            LEFT JOIN document_packages parent ON parent.id = p.parent_package_id
            LEFT JOIN document_packages resp ON resp.id = p.response_to_id
            WHERE p.id = ?
        """, (package_id,)).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def list_work_package_siblings(wp_code: str) -> list[dict]:
    """همه‌ی اسناد یک WP (رفت‌وبرگشت‌ها)."""
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT id, dfc_code, subject, sender_ref_no, contract_number,
                   stage, registered_at, response_to_id, parent_package_id
            FROM document_packages
            WHERE work_package_code = ?
            ORDER BY id ASC
        """, (wp_code,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()