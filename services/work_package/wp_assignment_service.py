"""سرویس ارجاع پکیج سند.

- ارجاع به یک یا چند نفر (سرپرست/کارشناس)
- متولی اصلی (is_primary=1)
- رسید خواندن، پذیرش، انجام، بازگشت
- کارتابل شخصی
"""

from datetime import datetime, timedelta

from config import Config
from database.connection import get_connection
from helpers.date_helper import now_tehran_str

from . import wp_event_service


# ============================================================
# ★ وضعیت‌های ارجاع
# ============================================================
class AssignmentStatus:
    PENDING = "pending"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    RETURNED = "returned"
    CANCELLED = "cancelled"


ACTIVE_STATUSES = (
    AssignmentStatus.PENDING,
    AssignmentStatus.ACCEPTED,
    AssignmentStatus.IN_PROGRESS,
)


class AssigneeRole:
    SUPERVISOR = "supervisor"
    EXPERT = "expert"
    COLLABORATOR = "collaborator"
    MANAGER = "manager"


class Action:
    ROUTE = "route"
    REFER = "refer"
    RETURN = "return"
    FORWARD = "forward"
    CC = "cc"


# ============================================================
# ★ ارجاع
# ============================================================
def route_package(
    *,
    package_id: int,
    from_user_id: int,
    to_user_ids: list[int],
    assignee_role: str = AssigneeRole.EXPERT,
    action: str = Action.ROUTE,
    instruction: str | None = None,
    due_days: int | None = None,
    priority: str = "normal",
    parent_id: int | None = None,
    primary_user_id: int | None = None,
) -> dict:
    """
    ارجاع سند به یک یا چند کاربر.

    Args:
        primary_user_id: اگر مشخص باشد، این کاربر متولی اصلی (is_primary=1) می‌شود.
                         اگر None باشد، اولین گیرنده متولی اصلی می‌شود.
    """
    if not package_id:
        return {"ok": False, "error": "شناسه سند الزامی است"}
    if not from_user_id:
        return {"ok": False, "error": "ارجاع‌دهنده الزامی است"}
    if not to_user_ids:
        return {"ok": False, "error": "حداقل یک گیرنده لازم است"}

    # حذف تکراری‌ها
    to_user_ids = list(dict.fromkeys(int(x) for x in to_user_ids if x))

    connection = get_connection()
    try:
        # خواندن سند
        doc = connection.execute(
            "SELECT * FROM document_packages WHERE id = ?", (package_id,)
        ).fetchone()
        if not doc:
            return {"ok": False, "error": "سند پیدا نشد"}

        # محاسبه مهلت
        if due_days is None:
            due_days = doc["sla_effective_days"] or doc["sla_days"] or Config.DEFAULT_SLA_DAYS

        due_date = _add_working_days(_today(), due_days)
        now = now_tehran_str()

        created = []
        errors = []

        # تعیین متولی اصلی
        if primary_user_id:
            primary_id = int(primary_user_id)
        else:
            primary_id = to_user_ids[0] if to_user_ids else None

        for i, to_user_id in enumerate(to_user_ids):
            # بررسی وجود کاربر
            u = connection.execute(
                "SELECT id, full_name FROM users WHERE id = ? AND is_active = 1",
                (to_user_id,),
            ).fetchone()
            if not u:
                errors.append(f"کاربر {to_user_id} پیدا نشد")
                continue

            is_primary = 1 if to_user_id == primary_id else 0

            try:
                cursor = connection.execute("""
                    INSERT INTO document_package_assignments
                    (package_id, parent_id, from_user_id, to_user_id,
                     assignee_role, action, instruction, is_primary,
                     priority, due_date, due_days, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    package_id, parent_id, from_user_id, to_user_id,
                    assignee_role, action, instruction, is_primary,
                    priority, due_date, due_days,
                    AssignmentStatus.PENDING, now, now,
                ))
                assignment_id = cursor.lastrowid
                created.append({
                    "assignment_id": assignment_id,
                    "to_user_id": to_user_id,
                    "to_user_name": u["full_name"],
                    "is_primary": bool(is_primary),
                    "due_date": due_date,
                    "due_days": due_days,
                })
            except Exception as exc:
                errors.append(f"خطا برای {to_user_id}: {exc}")

        # ★ به‌روزرسانی فیلدهای اصلی سند
        # current_expert_id = متولی اصلی (اگر نقش کارشناس است)
        if created and assignee_role == AssigneeRole.EXPERT:
            connection.execute("""
                UPDATE document_packages
                SET current_expert_id = ?, updated_at = ?
                WHERE id = ?
            """, (primary_id, now, package_id))
        elif created and assignee_role == AssigneeRole.SUPERVISOR:
            connection.execute("""
                UPDATE document_packages
                SET current_supervisor_id = ?, updated_at = ?
                WHERE id = ?
            """, (primary_id, now, package_id))

        connection.commit()
    except Exception as exc:
        connection.rollback()
        return {"ok": False, "error": f"خطا: {exc}"}
    finally:
        connection.close()

    # ★ ثبت رویداد
    for item in created:
        try:
            event_type = (
                wp_event_service.EventType.ROUTED_TO_SUPERVISOR
                if assignee_role == AssigneeRole.SUPERVISOR
                else wp_event_service.EventType.ROUTED_TO_EXPERT
            )
            wp_event_service.log_event(
                package_id=package_id,
                actor_id=from_user_id,
                event_type=event_type,
                summary=f"ارجاع به {item['to_user_name']}"
                        + (" (متولی اصلی)" if item["is_primary"] else ""),
                payload={
                    "to_user_id": item["to_user_id"],
                    "is_primary": item["is_primary"],
                    "due_date": item["due_date"],
                    "due_days": item["due_days"],
                    "role": assignee_role,
                    "action": action,
                },
                assignment_id=item["assignment_id"],
            )
        except Exception:
            pass

    return {
        "ok": bool(created),
        "created": created,
        "errors": errors,
    }


# ============================================================
# ★ اقدامات گیرنده
# ============================================================
def mark_read(assignment_id: int, user_id: int) -> dict:
    return _update_assignment(
        assignment_id, user_id,
        allowed_statuses=ACTIVE_STATUSES,
        updates={"read_at": now_tehran_str()},
        event_type="assignment_read",
        summary="ارجاع خوانده شد",
    )


def accept(assignment_id: int, user_id: int) -> dict:
    return _update_assignment(
        assignment_id, user_id,
        allowed_statuses=(AssignmentStatus.PENDING,),
        updates={
            "status": AssignmentStatus.ACCEPTED,
            "accepted_at": now_tehran_str(),
        },
        event_type=wp_event_service.EventType.EXPERT_ACCEPTED,
        summary="ارجاع پذیرفته شد",
    )


def start(assignment_id: int, user_id: int) -> dict:
    return _update_assignment(
        assignment_id, user_id,
        allowed_statuses=(AssignmentStatus.PENDING, AssignmentStatus.ACCEPTED),
        updates={"status": AssignmentStatus.IN_PROGRESS},
        event_type="assignment_started",
        summary="شروع انجام",
    )


def complete(assignment_id: int, user_id: int, note: str | None = None) -> dict:
    return _update_assignment(
        assignment_id, user_id,
        allowed_statuses=ACTIVE_STATUSES,
        updates={
            "status": AssignmentStatus.DONE,
            "completed_at": now_tehran_str(),
        },
        event_type="assignment_completed",
        summary=note or "ارجاع انجام شد",
    )


def return_to_sender(assignment_id: int, user_id: int, reason: str) -> dict:
    if not reason or not reason.strip():
        return {"ok": False, "error": "دلیل بازگشت الزامی است"}

    return _update_assignment(
        assignment_id, user_id,
        allowed_statuses=ACTIVE_STATUSES,
        updates={
            "status": AssignmentStatus.RETURNED,
            "returned_at": now_tehran_str(),
        },
        event_type="assignment_returned",
        summary=f"بازگشت: {reason.strip()}",
        payload={"reason": reason.strip()},
    )


def cancel(assignment_id: int, user_id: int, reason: str | None = None) -> dict:
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM document_package_assignments WHERE id = ?",
            (assignment_id,),
        ).fetchone()
        if not row:
            return {"ok": False, "error": "ارجاع پیدا نشد"}

        # فقط ارجاع‌دهنده یا ادمین
        role = _get_user_role(user_id)
        if row["from_user_id"] != user_id and role not in ("admin", "manager"):
            return {"ok": False, "error": "اجازه لغو ندارید"}

        now = now_tehran_str()
        connection.execute("""
            UPDATE document_package_assignments
            SET status = ?, cancelled_at = ?, cancel_reason = ?, updated_at = ?
            WHERE id = ?
        """, (
            AssignmentStatus.CANCELLED, now, reason, now, assignment_id,
        ))
        connection.commit()
    finally:
        connection.close()

    try:
        wp_event_service.log_event(
            package_id=row["package_id"],
            actor_id=user_id,
            event_type="assignment_cancelled",
            summary=f"ارجاع لغو شد" + (f": {reason}" if reason else ""),
            payload={"assignment_id": assignment_id, "reason": reason},
            assignment_id=assignment_id,
        )
    except Exception:
        pass

    return {"ok": True}


# ============================================================
# ★ کارتابل
# ============================================================
def get_inbox(user_id: int, tab: str = "active",
              limit: int = 100, offset: int = 0) -> dict:
    """
    کارتابل کاربر.

    tab: active | unread | overdue | waiting | done
    """
    connection = get_connection()
    try:
        where_parts = []
        params = []

        if tab == "active":
            where_parts.append("a.to_user_id = ?")
            where_parts.append("a.status IN (?, ?, ?)")
            params += [user_id, *ACTIVE_STATUSES]

        elif tab == "unread":
            where_parts.append("a.to_user_id = ?")
            where_parts.append("a.status IN (?, ?, ?)")
            where_parts.append("a.read_at IS NULL")
            params += [user_id, *ACTIVE_STATUSES]

        elif tab == "overdue":
            today = _today()
            where_parts.append("a.to_user_id = ?")
            where_parts.append("a.status IN (?, ?, ?)")
            where_parts.append("a.due_date IS NOT NULL AND a.due_date < ?")
            params += [user_id, *ACTIVE_STATUSES, today]

        elif tab == "waiting":
            where_parts.append("a.from_user_id = ?")
            where_parts.append("a.status IN (?, ?, ?)")
            params += [user_id, *ACTIVE_STATUSES]

        elif tab == "done":
            where_parts.append("a.to_user_id = ?")
            where_parts.append("a.status = ?")
            params += [user_id, AssignmentStatus.DONE]

        else:
            return {"ok": False, "error": f"تب نامعتبر: {tab}"}

        where_clause = " AND ".join(where_parts)

        sql = f"""
            SELECT a.*,
                   p.dfc_code, p.work_package_code, p.subject,
                   p.priority AS pkg_priority, p.stage AS pkg_stage,
                   p.source_type, p.sender_name, p.response_due_date,
                   p.is_overdue AS pkg_overdue,
                   fu.full_name AS from_user_name,
                   tu.full_name AS to_user_name
            FROM document_package_assignments a
            JOIN document_packages p ON p.id = a.package_id
            LEFT JOIN users fu ON fu.id = a.from_user_id
            LEFT JOIN users tu ON tu.id = a.to_user_id
            WHERE {where_clause}
            ORDER BY
              CASE a.priority
                WHEN 'urgent' THEN 1
                WHEN 'high' THEN 2
                WHEN 'normal' THEN 3
                ELSE 4
              END,
              COALESCE(a.due_date, '9999') ASC,
              a.created_at DESC
            LIMIT ? OFFSET ?
        """
        params += [limit, offset]

        rows = connection.execute(sql, params).fetchall()
        items = [dict(r) for r in rows]

        count_sql = f"SELECT COUNT(*) AS c FROM document_package_assignments a WHERE {where_clause}"
        total = connection.execute(count_sql, params[:-2]).fetchone()["c"]

        return {"ok": True, "items": items, "total": total}
    finally:
        connection.close()


def get_package_assignments(package_id: int) -> list[dict]:
    """درخت ارجاع‌های یک پکیج."""
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT a.*,
                   fu.full_name AS from_user_name,
                   tu.full_name AS to_user_name,
                   tu.avatar AS to_user_avatar,
                   dep.title AS to_department_title
            FROM document_package_assignments a
            LEFT JOIN users fu ON fu.id = a.from_user_id
            LEFT JOIN users tu ON tu.id = a.to_user_id
            LEFT JOIN departments dep ON dep.id = a.to_department_id
            WHERE a.package_id = ?
            ORDER BY a.created_at ASC, a.id ASC
        """, (package_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


def get_assignment(assignment_id: int) -> dict | None:
    connection = get_connection()
    try:
        row = connection.execute("""
            SELECT a.*,
                   p.dfc_code, p.work_package_code, p.subject,
                   fu.full_name AS from_user_name,
                   tu.full_name AS to_user_name
            FROM document_package_assignments a
            JOIN document_packages p ON p.id = a.package_id
            LEFT JOIN users fu ON fu.id = a.from_user_id
            LEFT JOIN users tu ON tu.id = a.to_user_id
            WHERE a.id = ?
        """, (assignment_id,)).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


# ============================================================
# ★ کمکی داخلی
# ============================================================
def _update_assignment(assignment_id, user_id, *,
                       allowed_statuses, updates, event_type,
                       summary, payload=None) -> dict:
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM document_package_assignments WHERE id = ?",
            (assignment_id,),
        ).fetchone()
        if not row:
            return {"ok": False, "error": "ارجاع پیدا نشد"}

        if row["to_user_id"] != user_id:
            return {"ok": False, "error": "این ارجاع به شما تعلق ندارد"}

        if row["status"] not in allowed_statuses:
            return {
                "ok": False,
                "error": f"وضعیت فعلی ({row['status']}) اجازه این اقدام را نمی‌دهد",
            }

        set_parts = []
        values = []
        for k, v in updates.items():
            set_parts.append(f"{k} = ?")
            values.append(v)
        set_parts.append("updated_at = ?")
        values.append(now_tehran_str())
        values.append(assignment_id)

        connection.execute(
            f"UPDATE document_package_assignments SET {', '.join(set_parts)} WHERE id = ?",
            values,
        )
        connection.commit()
    finally:
        connection.close()

    try:
        wp_event_service.log_event(
            package_id=row["package_id"],
            actor_id=user_id,
            event_type=event_type,
            summary=summary,
            payload=payload,
            assignment_id=assignment_id,
        )
    except Exception:
        pass

    return {"ok": True, "status": updates.get("status", row["status"])}


# ============================================================
# ★ کارتابل ترکیبی (پکیج جدید + اسناد قدیمی)
# ============================================================
def get_inbox_merged(user_id: int, tab: str = "active",
                     limit: int = 100, offset: int = 0) -> dict:
    """
    کارتابل ترکیبی: هم ارجاع‌های پکیج جدید، هم ارجاع‌های قدیمی.
    هر آیتم دارای فیلد `_type` است: 'package' یا 'legacy'.
    """
    # ★ ۱. ارجاع‌های پکیج جدید
    package_inbox = get_inbox(user_id, tab=tab, limit=limit, offset=offset)
    package_items = package_inbox.get("items", [])
    for item in package_items:
        item["_type"] = "package"
        item["_link"] = f"/work-package/{item['package_id']}"

    # ★ ۲. ارجاع‌های قدیمی (documents)
    legacy_items = []
    try:
        connection = get_connection()
        try:
            where_parts = []
            params = []

            if tab == "active":
                where_parts.append("a.to_user_id = ?")
                where_parts.append("a.status IN ('pending', 'accepted', 'in_progress')")
                params = [user_id]
            elif tab == "unread":
                where_parts.append("a.to_user_id = ?")
                where_parts.append("a.status IN ('pending', 'accepted', 'in_progress')")
                where_parts.append("a.read_at IS NULL")
                params = [user_id]
            elif tab == "overdue":
                where_parts.append("a.to_user_id = ?")
                where_parts.append("a.status IN ('pending', 'accepted', 'in_progress')")
                where_parts.append("a.due_date IS NOT NULL AND a.due_date < date('now')")
                params = [user_id]
            elif tab == "waiting":
                where_parts.append("a.from_user_id = ?")
                where_parts.append("a.status IN ('pending', 'accepted', 'in_progress')")
                params = [user_id]
            elif tab == "done":
                where_parts.append("a.to_user_id = ?")
                where_parts.append("a.status = 'done'")
                params = [user_id]
            else:
                where_parts.append("1=0")

            where_sql = " AND ".join(where_parts)

            rows = connection.execute(f"""
                SELECT a.*,
                       d.package_code, d.subject, d.priority AS doc_priority,
                       d.stage AS doc_stage, d.source_type, d.sender_name,
                       fu.full_name AS from_user_name,
                       tu.full_name AS to_user_name
                FROM document_assignments a
                LEFT JOIN documents d ON d.id = a.document_id
                LEFT JOIN users fu ON fu.id = a.from_user_id
                LEFT JOIN users tu ON tu.id = a.to_user_id
                WHERE {where_sql}
                ORDER BY a.created_at DESC
                LIMIT ?
            """, params + [limit]).fetchall()

            for r in rows:
                item = dict(r)
                item["_type"] = "legacy"
                item["package_id"] = None
                item["document_id"] = item.get("document_id")
                item["dfc_code"] = item.get("package_code")
                item["work_package_code"] = None
                item["_link"] = f"/documents/package/{item['document_id']}" if item.get("document_id") else "#"
                legacy_items.append(item)
        finally:
            connection.close()
    except Exception:
        pass

    # ★ ۳. ادغام
    all_items = package_items + legacy_items

    # ★ ۴. مرتب‌سازی بر اساس اولویت و تاریخ
    def _sort_key(item):
        priority_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
        p = item.get("priority") or item.get("doc_priority") or "normal"
        due = item.get("due_date") or "9999"
        return (priority_order.get(p, 2), due)

    all_items.sort(key=_sort_key)

    return {
        "ok": True,
        "items": all_items[:limit],
        "total": package_inbox.get("total", 0) + len(legacy_items),
        "package_count": len(package_items),
        "legacy_count": len(legacy_items),
    }


# ============================================================
# ★ کمکی‌های تاریخ
# ============================================================
def _today() -> str:
    return datetime.now().strftime("%Y/%m/%d")


def _get_user_role(user_id: int) -> str:
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT role FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return row["role"] if row else ""
    finally:
        connection.close()


def _add_working_days(start_date_str: str, days: int) -> str:
    try:
        from services.calendar.working_days import add_working_days
        result = add_working_days(start_date_str, days)
        if hasattr(result, "strftime"):
            return result.strftime("%Y/%m/%d")
        return str(result)
    except Exception:
        try:
            d = datetime.strptime(start_date_str, "%Y/%m/%d")
        except ValueError:
            d = datetime.now()
        return (d + timedelta(days=days)).strftime("%Y/%m/%d")