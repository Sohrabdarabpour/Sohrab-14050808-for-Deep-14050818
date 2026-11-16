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
    Stage.SENT_TO_MANAGEMENT: [Stage.RETURNED_FROM_MANAGEMENT, Stage.CANCELLED, Stage.ARCHIVED],
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
) -> dict | None:
    """تشخیص WP موجود بر اساس اولویت."""
    connection = get_connection()
    try:
        # ★ ۱. جستجو در جدول document_package_references (رفرنس‌های ثبت‌شده)
        if reference_no:
            row = connection.execute("""
                SELECT dp.id, dp.work_package_code, dp.dfc_code, dp.subject
                FROM document_package_references r
                JOIN document_packages dp ON dp.id = r.package_id
                WHERE TRIM(r.reference_no) = TRIM(?)
                  AND dp.stage NOT IN ('archived', 'cancelled')
                ORDER BY dp.id DESC
                LIMIT 1
            """, (reference_no,)).fetchone()
            if row:
                return {
                    "package_id": row["id"],
                    "work_package_code": row["work_package_code"],
                    "dfc_code": row["dfc_code"],
                    "subject": row["subject"],
                }

        # ۲. جستجوی مستقیم در sender_ref_no
        if sender_ref_no:
            row = connection.execute("""
                SELECT id, work_package_code, dfc_code, subject
                FROM document_packages
                WHERE TRIM(sender_ref_no) = TRIM(?)
                  AND stage NOT IN ('archived', 'cancelled')
                ORDER BY id DESC
                LIMIT 1
            """, (sender_ref_no,)).fetchone()
            if row:
                return {
                    "package_id": row["id"],
                    "work_package_code": row["work_package_code"],
                    "dfc_code": row["dfc_code"],
                    "subject": row["subject"],
                }

        # ۳. شماره نامه + شماره قرارداد
        if sender_ref_no and contract_number:
            row = connection.execute("""
                SELECT id, work_package_code, dfc_code, subject
                FROM document_packages
                WHERE TRIM(sender_ref_no) = TRIM(?) AND TRIM(contract_number) = TRIM(?)
                  AND stage NOT IN ('archived', 'cancelled')
                ORDER BY id DESC
                LIMIT 1
            """, (sender_ref_no, contract_number)).fetchone()
            if row:
                return {
                    "package_id": row["id"],
                    "work_package_code": row["work_package_code"],
                    "dfc_code": row["dfc_code"],
                    "subject": row["subject"],
                }

        # ۴. شماره قرارداد + پیمانکار
        if contract_number and contractor_id:
            row = connection.execute("""
                SELECT id, work_package_code, dfc_code, subject
                FROM document_packages
                WHERE TRIM(contract_number) = TRIM(?) AND contractor_id = ?
                  AND stage NOT IN ('archived', 'cancelled')
                ORDER BY id DESC
                LIMIT 1
            """, (contract_number, contractor_id)).fetchone()
            if row:
                return {
                    "package_id": row["id"],
                    "work_package_code": row["work_package_code"],
                    "dfc_code": row["dfc_code"],
                    "subject": row["subject"],
                }

        # ۵. شماره قرارداد + پروژه
        if contract_number and project_id:
            row = connection.execute("""
                SELECT id, work_package_code, dfc_code, subject
                FROM document_packages
                WHERE TRIM(contract_number) = TRIM(?) AND project_id = ?
                  AND stage NOT IN ('archived', 'cancelled')
                ORDER BY id DESC
                LIMIT 1
            """, (contract_number, project_id)).fetchone()
            if row:
                return {
                    "package_id": row["id"],
                    "work_package_code": row["work_package_code"],
                    "dfc_code": row["dfc_code"],
                    "subject": row["subject"],
                }

        # ۶. شماره اتوماسیون
        if automation_number:
            row = connection.execute("""
                SELECT id, work_package_code, dfc_code, subject
                FROM document_packages
                WHERE TRIM(automation_number) = TRIM(?)
                  AND stage NOT IN ('archived', 'cancelled')
                ORDER BY id DESC
                LIMIT 1
            """, (automation_number,)).fetchone()
            if row:
                return {
                    "package_id": row["id"],
                    "work_package_code": row["work_package_code"],
                    "dfc_code": row["dfc_code"],
                    "subject": row["subject"],
                }

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
    date_letter: str | None = None,
    date_received: str | None = None,
    sender_ref_date: str | None = None,
    date_sent_to_management: str | None = None,
    date_returned_from_management: str | None = None,
    management_date_on_letter: str | None = None,
    sender_ref_no: str | None = None,
    contract_number: str | None = None,
    reference_no: str | None = None,
    references: list[str] | None = None,
    automation_number: str | None = None,
    sender_name: str | None = None,
    sender_type: str = "other",
    source_type: str = "other",
    description: str | None = None,
    management_instruction: str | None = None,
    contractor_id: int | None = None,
    project_id: int | None = None,
    group_id: int | None = None,
    subgroup_id: int | None = None,
    priority: str = "normal",
    confidentiality: str = "internal",
    supervisor_ids: list[int] | None = None,
    direct_expert_ids: list[int] | None = None,
    response_to_id: int | None = None,
    force_new_wp: bool = False,
) -> dict:
    """ثبت سند جدید با تخصیص DFC و WP."""
    if not subject or not subject.strip():
        return {"ok": False, "error": "موضوع سند الزامی است"}
    if not registered_by:
        return {"ok": False, "error": "کاربر ثبت‌کننده مشخص نیست"}

    import json
    year = jdatetime.date.today().year
    now = now_tehran_str()

    # ★ آماده‌سازی لیست رفرنس‌ها
    all_refs = []
    if reference_no and reference_no.strip():
        all_refs.append(reference_no.strip())
    if references:
        all_refs.extend([r.strip() for r in references if r and r.strip()])
    all_refs = list(dict.fromkeys(all_refs))

    primary_reference = all_refs[0] if all_refs else None

    print(f"\n=== REGISTER_PACKAGE DEBUG ===")
    print(f"  all_refs: {all_refs}")
    print(f"  primary_reference: {primary_reference}")

    connection = get_connection()
    try:
        # ★ تشخیص WP موجود
        existing_wp_info = None
        if not force_new_wp:
            # اولویت اول: جستجو با رفرنس‌های چندگانه
            if all_refs:
                wps_found = find_wps_by_references(all_refs)
                if wps_found:
                    top_wp = wps_found[0]
                    existing_wp_info = {
                        "package_id": None,
                        "work_package_code": top_wp["work_package_code"],
                        "dfc_code": top_wp["sample_dfc"],
                        "subject": top_wp["sample_subject"],
                    }

            # اگر پیدا نشد، منطق قدیمی
            if not existing_wp_info:
                existing_wp_info = find_work_package(
                    reference_no=primary_reference,
                    sender_ref_no=sender_ref_no,
                    contract_number=contract_number,
                    contractor_id=contractor_id,
                    project_id=project_id,
                    automation_number=automation_number,
                )

        print(f"  existing_wp_info: {existing_wp_info}")

        # ★ تخصیص DFC
        dfc_value = _allocate_counter(connection, "dfc", year)
        dfc_code = f"DFC-{year}-{dfc_value:04d}"

        # ★ تخصیص یا استفاده از WP
        if existing_wp_info:
            wp_code = existing_wp_info["work_package_code"]
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

        # parent_package_id
        parent_id = None
        if response_to_id:
            parent_row = connection.execute(
                "SELECT parent_package_id, id FROM document_packages WHERE id = ?",
                (response_to_id,),
            ).fetchone()
            if parent_row:
                parent_id = parent_row["parent_package_id"] or parent_row["id"]

        supervisor_ids_json = json.dumps(supervisor_ids or [], ensure_ascii=False)
        direct_expert_ids_json = json.dumps(direct_expert_ids or [], ensure_ascii=False)

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
            sender_ref_no, contract_number, primary_reference, automation_number,
            sender_name, sender_type, source_type,
            contractor_id, project_id,
            date_sent_to_management, date_returned_from_management,
            management_date_on_letter, management_instruction,
            group_id, subgroup_id, priority, confidentiality,
            supervisor_ids_json, direct_expert_ids_json,
            Stage.REGISTERED, response_to_id, parent_id, wp_subject,
            registered_by, now,
        ))
        package_id = cursor.lastrowid

        print(f"  package_id: {package_id}")

        # ★ ثبت رفرنس‌های چندگانه
        for ref in all_refs:
            try:
                connection.execute("""
                    INSERT INTO document_package_references
                    (package_id, reference_no, created_by)
                    VALUES (?, ?, ?)
                """, (package_id, ref, registered_by))
                print(f"  ✅ ref inserted: {ref}")
            except Exception as ref_exc:
                print(f"  ❌ ref insert error: {ref_exc}")

        # ★ ثبت در جدول لینک‌ها
        try:
            connection.execute("""
                INSERT INTO document_package_wp_links
                (package_id, work_package_code, is_primary, linked_by)
                VALUES (?, ?, 1, ?)
            """, (package_id, wp_code, registered_by))
        except Exception as link_exc:
            print(f"⚠️ wp_links insert error: {link_exc}")

        connection.commit()
        print(f"  ✅ COMMITTED")
    except Exception as exc:
        connection.rollback()
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": f"خطا در ثبت سند: {exc}"}
    finally:
        connection.close()

    # ★ رویداد
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
                "existing_wp": bool(existing_wp_info),
                "references_count": len(all_refs),
                "references": all_refs,
            },
        )
    except Exception:
        pass

    return {
        "ok": True,
        "package_id": package_id,
        "document_id": package_id,
        "dfc_code": dfc_code,
        "work_package_code": wp_code,
        "package_year": year,
        "dfc_sequence": dfc_value,
        "existing_wp": bool(existing_wp_info),
        "references_count": len(all_refs),
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

        if new_stage == Stage.CLOSED:
            set_parts += ["closed_by = ?", "closed_at = ?"]
            values += [actor_id, now]
        elif new_stage == Stage.ARCHIVED:
            set_parts += ["archived_by = ?", "archived_at = ?"]
            values += [actor_id, now]
            if reason:
                set_parts.append("archive_reason = ?")
                values.append(reason)

        if extra_fields:
            allowed_extra = {
                "management_action", "management_instruction",
                "management_date_on_letter", "date_sent_to_management",
                "date_returned_from_management", "group_id", "subgroup_id",
                "priority", "confidentiality", "supervisor_ids",
                "direct_expert_ids", "date_sent_response",
                "response_letter_number", "response_letter_date",
                "final_response", "final_result", "final_result_notes",
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


# ============================================================
# ★ اتصال سند به چند WP
# ============================================================
def link_package_to_wps(
    package_id: int,
    wp_codes: list[str],
    linked_by: int,
    primary_wp: str | None = None,
) -> dict:
    connection = get_connection()
    try:
        connection.execute(
            "DELETE FROM document_package_wp_links WHERE package_id = ?",
            (package_id,),
        )

        if not wp_codes:
            connection.commit()
            return {"ok": True, "linked": 0}

        primary = primary_wp or wp_codes[0]

        for wp in wp_codes:
            try:
                connection.execute("""
                    INSERT INTO document_package_wp_links
                    (package_id, work_package_code, is_primary, linked_by)
                    VALUES (?, ?, ?, ?)
                """, (package_id, wp, 1 if wp == primary else 0, linked_by))
            except Exception:
                pass

        connection.execute("""
            UPDATE document_packages
            SET work_package_code = ?, updated_at = ?
            WHERE id = ?
        """, (primary, now_tehran_str(), package_id))

        connection.commit()
        return {"ok": True, "linked": len(wp_codes)}
    except Exception as exc:
        connection.rollback()
        return {"ok": False, "error": str(exc)}
    finally:
        connection.close()


def get_package_wps(package_id: int) -> list[dict]:
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT l.*,
                   p.dfc_code, p.subject AS sample_subject
            FROM document_package_wp_links l
            LEFT JOIN document_packages p ON p.work_package_code = l.work_package_code
            WHERE l.package_id = ?
            ORDER BY l.is_primary DESC, l.id ASC
        """, (package_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


# ============================================================
# ★ پیشنهاد WPها (منطق ترکیبی)
# ============================================================
def suggest_wps_for_reference(
    *,
    reference_no: str | None = None,
    sender_ref_no: str | None = None,
    contract_number: str | None = None,
    contractor_id: int | None = None,
    project_id: int | None = None,
    automation_number: str | None = None,
    all_references: list[str] | None = None,   # ★ جدید
    limit: int = 20,
) -> list[dict]:
    """
    پیشنهاد WPهای مرتبط.

    ★ اگر all_references داده شده باشد → همه‌ی آن‌ها جستجو می‌شوند
    ★ در غیر این صورت → reference_no و sender_ref_no
    """
    connection = get_connection()
    try:
        # جمع‌آوری رفرنس‌ها
        refs_to_search = []
        if all_references:
            refs_to_search.extend(all_references)
        if reference_no and reference_no.strip():
            refs_to_search.append(reference_no.strip())
        if sender_ref_no and sender_ref_no.strip():
            refs_to_search.append(sender_ref_no.strip())

        # حذف تکراری‌ها و خالی‌ها
        refs_to_search = list(dict.fromkeys(
            r.strip() for r in refs_to_search if r and r.strip()
        ))

        if not refs_to_search:
            return []

        placeholders = ",".join("?" * len(refs_to_search))

        # ═══════════════════════════════════════════════════
        # حالت ۱: هم رفرنس و هم قرارداد
        # ═══════════════════════════════════════════════════
        if contract_number and contract_number.strip():
            # مرحله ۱: sender_ref_no + contract_number
            sql = f"""
                SELECT work_package_code,
                       MAX(dfc_code) AS sample_dfc,
                       MAX(subject) AS sample_subject,
                       COUNT(*) AS doc_count,
                       MAX(id) AS latest_id,
                       'sender_ref+contract' AS match_source,
                       GROUP_CONCAT(DISTINCT sender_ref_no) AS matching_references_str
                FROM document_packages
                WHERE TRIM(sender_ref_no) IN ({placeholders})
                  AND TRIM(contract_number) = TRIM(?)
                  AND stage NOT IN ('archived', 'cancelled')
                GROUP BY work_package_code
                ORDER BY latest_id DESC
                LIMIT ?
            """
            params = refs_to_search + [contract_number.strip(), limit]
            rows = connection.execute(sql, params).fetchall()
            if rows:
                return _format_suggestion_rows(rows)

            # مرحله ۲: document_package_references + contract_number
            sql = f"""
                SELECT dp.work_package_code,
                       MAX(dp.dfc_code) AS sample_dfc,
                       MAX(dp.subject) AS sample_subject,
                       COUNT(DISTINCT dp.id) AS doc_count,
                       MAX(dp.id) AS latest_id,
                       'reference+contract' AS match_source,
                       GROUP_CONCAT(DISTINCT r.reference_no) AS matching_references_str
                FROM document_package_references r
                JOIN document_packages dp ON dp.id = r.package_id
                WHERE TRIM(r.reference_no) IN ({placeholders})
                  AND TRIM(dp.contract_number) = TRIM(?)
                  AND dp.stage NOT IN ('archived', 'cancelled')
                GROUP BY dp.work_package_code
                ORDER BY latest_id DESC
                LIMIT ?
            """
            rows = connection.execute(sql, params).fetchall()
            if rows:
                return _format_suggestion_rows(rows)

        # ═══════════════════════════════════════════════════
        # حالت ۲: فقط رفرنس
        # ═══════════════════════════════════════════════════

        # مرحله ۱: sender_ref_no
        sql = f"""
            SELECT work_package_code,
                   MAX(dfc_code) AS sample_dfc,
                   MAX(subject) AS sample_subject,
                   COUNT(*) AS doc_count,
                   MAX(id) AS latest_id,
                   'sender_ref' AS match_source,
                   GROUP_CONCAT(DISTINCT sender_ref_no) AS matching_references_str
            FROM document_packages
            WHERE TRIM(sender_ref_no) IN ({placeholders})
              AND stage NOT IN ('archived', 'cancelled')
            GROUP BY work_package_code
            ORDER BY latest_id DESC
            LIMIT ?
        """
        rows = connection.execute(sql, refs_to_search + [limit]).fetchall()
        if rows:
            return _format_suggestion_rows(rows)

        # مرحله ۲: document_package_references
        sql = f"""
            SELECT dp.work_package_code,
                   MAX(dp.dfc_code) AS sample_dfc,
                   MAX(dp.subject) AS sample_subject,
                   COUNT(DISTINCT dp.id) AS doc_count,
                   MAX(dp.id) AS latest_id,
                   'reference' AS match_source,
                   GROUP_CONCAT(DISTINCT r.reference_no) AS matching_references_str
            FROM document_package_references r
            JOIN document_packages dp ON dp.id = r.package_id
            WHERE TRIM(r.reference_no) IN ({placeholders})
              AND dp.stage NOT IN ('archived', 'cancelled')
            GROUP BY dp.work_package_code
            ORDER BY latest_id DESC
            LIMIT ?
        """
        rows = connection.execute(sql, refs_to_search + [limit]).fetchall()
        return _format_suggestion_rows(rows)

    finally:
        connection.close()


def _format_suggestion_rows(rows):
    """تبدیل ردیف‌های SQL به dict با matching_references."""
    result = []
    for r in rows:
        item = dict(r)
        if item.get("matching_references_str"):
            item["matching_references"] = item["matching_references_str"].split(",")
        else:
            item["matching_references"] = []
        item.pop("matching_references_str", None)
        result.append(item)
    return result
def _format_suggestion_rows(rows):
    """تبدیل ردیف‌های SQL به dict با matching_references."""
    result = []
    for r in rows:
        item = dict(r)
        if item.get("matching_references_str"):
            item["matching_references"] = item["matching_references_str"].split(",")
        else:
            item["matching_references"] = []
        # حذف فیلد موقت
        item.pop("matching_references_str", None)
        result.append(item)
    return result



def find_wps_by_references(refs: list[str]) -> list[dict]:
    """جستجوی WPهایی که دقیقاً یکی از این رفرنس‌ها در جدول
    document_package_references ثبت شده باشد."""
    if not refs:
        return []

    refs = [r.strip() for r in refs if r and r.strip()]
    if not refs:
        return []

    connection = get_connection()
    try:
        placeholders = ",".join("?" * len(refs))

        sql = f"""
            SELECT dp.work_package_code,
                   MAX(dp.dfc_code) AS sample_dfc,
                   MAX(dp.subject) AS sample_subject,
                   COUNT(DISTINCT dp.id) AS doc_count,
                   MAX(dp.id) AS latest_id
            FROM document_package_references r
            JOIN document_packages dp ON dp.id = r.package_id
            WHERE TRIM(r.reference_no) IN ({placeholders})
              AND dp.stage NOT IN ('archived', 'cancelled')
            GROUP BY dp.work_package_code
            ORDER BY latest_id DESC
            LIMIT 20
        """
        rows = connection.execute(sql, refs).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


# ============================================================
# ★ تشخیص پیمانکار و پروژه از شماره قرارداد
# ============================================================
# ============================================================
# ★ تشخیص پیمانکار و پروژه از شماره قرارداد
# ============================================================
def find_contractor_and_project_by_contract_number(
    contract_number: str,
) -> dict | None:
    """جستجو در جدول projects بر اساس شماره قرارداد (داخلی یا خارجی)."""
    if not contract_number or not contract_number.strip():
        return None

    clean_contract = contract_number.strip()
    connection = get_connection()
    try:
        # جستجو در هر دو ستون contract_number و contract_number_foreign
        row = connection.execute("""
            SELECT p.id AS project_id, p.name AS project_name,
                   c.id AS contractor_id, c.name AS contractor_name
            FROM projects p
            LEFT JOIN contractors c ON c.id = p.contractor_id
            WHERE (TRIM(p.contract_number) = TRIM(?) OR TRIM(p.contract_number_foreign) = TRIM(?))
              AND p.is_active = 1
            ORDER BY p.id DESC
            LIMIT 1
        """, (clean_contract, clean_contract)).fetchone()

        if row:
            return {
                "project_id": row["project_id"],
                "project_name": row["project_name"],
                "contractor_id": row["contractor_id"],
                "contractor_name": row["contractor_name"],
            }
        return None
    finally:
        connection.close()
        
# ============================================================
# ★ رفرنس‌های چندگانه
# ============================================================
def add_package_references(
    package_id: int,
    refs: list[str],
    created_by: int,
) -> dict:
    """ثبت چند رفرنس برای یک سند (اضافه کردن به قبلی‌ها)."""
    if not refs:
        return {"ok": True, "added": 0}

    connection = get_connection()
    try:
        added = 0
        for ref in refs:
            ref = ref.strip()
            if not ref:
                continue
            try:
                connection.execute("""
                    INSERT INTO document_package_references
                    (package_id, reference_no, created_by)
                    VALUES (?, ?, ?)
                """, (package_id, ref, created_by))
                added += 1
            except Exception:
                pass

        connection.commit()
        return {"ok": True, "added": added}
    except Exception as exc:
        connection.rollback()
        return {"ok": False, "error": str(exc)}
    finally:
        connection.close()


def get_package_references(package_id: int) -> list[dict]:
    """دریافت همه‌ی رفرنس‌های یک سند."""
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT r.*,
                   u.full_name AS created_by_name
            FROM document_package_references r
            LEFT JOIN users u ON u.id = r.created_by
            WHERE r.package_id = ?
            ORDER BY r.id ASC
        """, (package_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()