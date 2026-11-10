"""سرویس ارجاع سند — قلب کارتابل.

قواعد:
- هر ارجاع یک والد دارد (parent_id) — درخت ارجاع
- فقط ارجاع‌هایی که to_user_id = من و status فعال است در کارتابل می‌آیند
- رسید خواندن (read_at) هنگام باز کردن کارتابل ثبت می‌شود
- پذیرش/انجام/بازگشت همه رویداد می‌سازند
- مهلت ارجاع (due_date) جدا از مهلت سند (response_due_date) است
"""

from datetime import datetime, timedelta

from config import Config
from database.connection import get_connection
from helpers.date_helper import now_tehran_str

from . import event_service


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


#: انواع اقدام
class AssignmentAction:
    ROUTE = "route"
    REFER = "refer"
    RETURN = "return"
    FORWARD = "forward"
    CC = "cc"


# ============================================================
# ★ ارجاع سند
# ============================================================
def route_document(
    *,
    document_id: int,
    from_user_id: int,
    to_user_ids: list[int],
    instruction: str | None = None,
    due_days: int | None = None,
    priority: str = "normal",
    parent_id: int | None = None,
    action: str = AssignmentAction.ROUTE,
) -> dict:
    """
    ارجاع سند به یک یا چند کاربر.

    Args:
        document_id: شناسه سند
        from_user_id: چه کسی ارجاع می‌دهد
        to_user_ids: لیست شناسه‌های گیرندگان
        instruction: دستور/توضیح
        due_days: مهلت اقدام (روز کاری از امروز) — پیش‌فرض از SLA سند
        priority: low | normal | high | urgent
        parent_id: اگر این ارجاع فرزند ارجاع دیگری است
        action: نوع اقدام (route | refer | return | forward | cc)

    Returns:
        dict با کلیدهای ok, created (list), errors (list)
    """
    if not document_id:
        return {"ok": False, "error": "document_id لازم است"}
    if not from_user_id:
        return {"ok": False, "error": "from_user_id لازم است"}
    if not to_user_ids:
        return {"ok": False, "error": "حداقل یک گیرنده لازم است"}

    # حذف تکراری‌ها
    to_user_ids = list(dict.fromkeys(int(x) for x in to_user_ids if x))

    # خواندن سند
    connection = get_connection()
    try:
        doc = connection.execute(
            "SELECT * FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
        if not doc:
            return {"ok": False, "error": "سند پیدا نشد"}

        # محاسبه‌ی مهلت (اگر due_days داده نشد، از sla_days سند استفاده کن)
        if due_days is None:
            due_days = doc["sla_effective_days"] or doc["sla_days"] or Config.DEFAULT_SLA_DAYS

        due_date = _add_working_days(_today(), due_days)

        created = []
        errors = []
        now = now_tehran_str()

        for to_user_id in to_user_ids:
            # بررسی وجود کاربر
            u = connection.execute(
                "SELECT id, full_name FROM users WHERE id = ? AND is_active = 1",
                (to_user_id,),
            ).fetchone()
            if not u:
                errors.append(f"کاربر {to_user_id} پیدا نشد یا غیرفعال است")
                continue

            try:
                cursor = connection.execute("""
                    INSERT INTO document_assignments
                    (document_id, parent_id,
                     from_user_id, to_user_id,
                     action, instruction,
                     priority, due_date, due_days,
                     status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    document_id, parent_id,
                    from_user_id, to_user_id,
                    action, instruction,
                    priority, due_date, due_days,
                    AssignmentStatus.PENDING, now, now,
                ))
                assignment_id = cursor.lastrowid
                created.append({
                    "assignment_id": assignment_id,
                    "to_user_id": to_user_id,
                    "to_user_name": u["full_name"],
                    "due_date": due_date,
                    "due_days": due_days,
                })
            except Exception as exc:
                errors.append(f"خطا برای کاربر {to_user_id}: {exc}")

        connection.commit()

        # اگر ارجاع اولیه بود (parent_id=None) → مرحله را routed کن
        if parent_id is None and created:
            try:
                from . import package_service
                package_service.change_stage(
                    document_id, package_service.Stage.ROUTED,
                    actor_id=from_user_id,
                    payload_extra={"assignments_created": len(created)},
                )
            except Exception:
                pass

    except Exception as exc:
        connection.rollback()
        return {"ok": False, "error": f"خطا: {exc}"}
    finally:
        connection.close()

    # ---- ثبت رویداد برای هر ارجاع ----
    for item in created:
        try:
            event_service.log_event(
                document_id=document_id,
                actor_id=from_user_id,
                event_type=event_service.EventType.ROUTED,
                summary=f"ارجاع به {item['to_user_name']}",
                payload={
                    "to_user_id": item["to_user_id"],
                    "due_date": item["due_date"],
                    "due_days": item["due_days"],
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
    """ثبت رسید خواندن."""
    return _update_assignment(
        assignment_id, user_id,
        allowed_statuses=ACTIVE_STATUSES,
        updates={"read_at": now_tehran_str()},
        event_type="read",
        summary="ارجاع خوانده شد",
    )


def accept(assignment_id: int, user_id: int) -> dict:
    """پذیرش ارجاع."""
    return _update_assignment(
        assignment_id, user_id,
        allowed_statuses=(AssignmentStatus.PENDING,),
        updates={
            "status": AssignmentStatus.ACCEPTED,
            "accepted_at": now_tehran_str(),
        },
        event_type=event_service.EventType.ACCEPTED,
        summary="ارجاع پذیرفته شد",
    )


def start(assignment_id: int, user_id: int) -> dict:
    """شروع انجام."""
    return _update_assignment(
        assignment_id, user_id,
        allowed_statuses=(AssignmentStatus.ACCEPTED, AssignmentStatus.PENDING),
        updates={"status": AssignmentStatus.IN_PROGRESS},
        event_type=event_service.EventType.STARTED,
        summary="شروع انجام",
    )


def complete(assignment_id: int, user_id: int, note: str | None = None) -> dict:
    """اتمام ارجاع."""
    result = _update_assignment(
        assignment_id, user_id,
        allowed_statuses=ACTIVE_STATUSES,
        updates={
            "status": AssignmentStatus.DONE,
            "completed_at": now_tehran_str(),
        },
        event_type=event_service.EventType.COMPLETED,
        summary=note or "ارجاع انجام شد",
    )
    return result


def return_to_sender(
    assignment_id: int, user_id: int, reason: str
) -> dict:
    """بازگرداندن به فرستنده."""
    if not reason or not reason.strip():
        return {"ok": False, "error": "دلیل بازگشت الزامی است"}

    return _update_assignment(
        assignment_id, user_id,
        allowed_statuses=ACTIVE_STATUSES,
        updates={
            "status": AssignmentStatus.RETURNED,
            "returned_at": now_tehran_str(),
        },
        event_type=event_service.EventType.RETURNED,
        summary=f"بازگشت: {reason.strip()}",
        payload={"reason": reason.strip()},
    )


def cancel(assignment_id: int, user_id: int, reason: str | None = None) -> dict:
    """لغو ارجاع (توسط فرستنده یا ادمین)."""
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM document_assignments WHERE id = ?",
            (assignment_id,),
        ).fetchone()
        if not row:
            return {"ok": False, "error": "ارجاع پیدا نشد"}

        # فقط فرستنده یا ادمین
        role = _get_user_role(user_id)
        if row["from_user_id"] != user_id and role not in ("admin", "manager"):
            return {"ok": False, "error": "اجازه‌ی لغو ندارید"}

        now = now_tehran_str()
        connection.execute("""
            UPDATE document_assignments
            SET status = ?, cancelled_at = ?, cancel_reason = ?, updated_at = ?
            WHERE id = ?
        """, (
            AssignmentStatus.CANCELLED, now, reason, now, assignment_id,
        ))
        connection.commit()
    finally:
        connection.close()

    try:
        event_service.log_event(
            document_id=row["document_id"],
            actor_id=user_id,
            event_type=event_service.EventType.CANCELLED,
            summary=f"ارجاع لغو شد" + (f": {reason}" if reason else ""),
            payload={"assignment_id": assignment_id, "reason": reason},
            assignment_id=assignment_id,
        )
    except Exception:
        pass

    return {"ok": True}


# ============================================================
# ★ کمکی داخلی
# ============================================================
def _update_assignment(
    assignment_id: int,
    user_id: int,
    *,
    allowed_statuses: tuple,
    updates: dict,
    event_type: str,
    summary: str,
    payload: dict | None = None,
) -> dict:
    """تغییر وضعیت ارجاع با بررسی دسترسی و ثبت رویداد."""
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM document_assignments WHERE id = ?",
            (assignment_id,),
        ).fetchone()
        if not row:
            return {"ok": False, "error": "ارجاع پیدا نشد"}

        if row["to_user_id"] != user_id:
            return {"ok": False, "error": "این ارجاع به شما تعلق ندارد"}

        if row["status"] not in allowed_statuses:
            return {
                "ok": False,
                "error": f"وضعیت فعلی ({row['status']}) اجازه‌ی این اقدام را نمی‌دهد",
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
            f"UPDATE document_assignments SET {', '.join(set_parts)} WHERE id = ?",
            values,
        )
        connection.commit()
    finally:
        connection.close()

    try:
        event_service.log_event(
            document_id=row["document_id"],
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
# ★ کوئری کارتابل
# ============================================================
def get_inbox(
    user_id: int,
    *,
    tab: str = "active",
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """
    کارتابل کاربر.

    tab:
      - 'active'  → pending/accepted/in_progress
      - 'unread'  → active + read_at IS NULL
      - 'overdue' → active + due_date < today
      - 'waiting' → ارجاع‌هایی که من فرستادم و هنوز انجام نشده
      - 'done'    → انجام‌شده‌ها (۳۰ روز اخیر)
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
            where_parts.append("a.completed_at >= date('now', '-30 days')")
            params += [user_id, AssignmentStatus.DONE]

        else:
            return {"ok": False, "error": f"تب نامعتبر: {tab}"}

        where_clause = " AND ".join(where_parts)

        sql = f"""
            SELECT a.*,
                   d.package_code, d.subject, d.priority AS doc_priority,
                   d.stage AS doc_stage, d.source_type, d.sender_name,
                   d.response_due_date, d.is_overdue AS doc_overdue,
                   fu.full_name AS from_user_name,
                   tu.full_name AS to_user_name
            FROM document_assignments a
            JOIN documents d ON d.id = a.document_id
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

        # شمارش کل
        count_sql = f"""
            SELECT COUNT(*) AS c FROM document_assignments a
            WHERE {where_clause}
        """
        total = connection.execute(
            count_sql, params[:-2]
        ).fetchone()["c"]

        return {"ok": True, "items": items, "total": total}
    finally:
        connection.close()


def get_document_assignments(document_id: int) -> list[dict]:
    """درخت ارجاع‌های یک سند."""
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT a.*,
                   fu.full_name AS from_user_name,
                   tu.full_name AS to_user_name,
                   tu.avatar AS to_user_avatar,
                   dep.title AS to_department_title
            FROM document_assignments a
            LEFT JOIN users fu ON fu.id = a.from_user_id
            LEFT JOIN users tu ON tu.id = a.to_user_id
            LEFT JOIN departments dep ON dep.id = a.to_department_id
            WHERE a.document_id = ?
            ORDER BY a.created_at ASC, a.id ASC
        """, (document_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


def get_assignment(assignment_id: int) -> dict | None:
    connection = get_connection()
    try:
        row = connection.execute("""
            SELECT a.*,
                   d.package_code, d.subject,
                   fu.full_name AS from_user_name,
                   tu.full_name AS to_user_name
            FROM document_assignments a
            JOIN documents d ON d.id = a.document_id
            LEFT JOIN users fu ON fu.id = a.from_user_id
            LEFT JOIN users tu ON tu.id = a.to_user_id
            WHERE a.id = ?
        """, (assignment_id,)).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


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
    """افزودن N روز کاری به تاریخ میلادی (با احتساب آخر هفته و تعطیلات)."""
    try:
        from services.calendar.working_days import add_working_days
        result = add_working_days(start_date_str, days)
        # ★ ممکن است date یا str برگرداند — همیشه رشته کن
        if hasattr(result, "strftime"):
            return result.strftime("%Y/%m/%d")
        return str(result)
    except (ImportError, Exception):
        try:
            d = datetime.strptime(start_date_str, "%Y/%m/%d")
        except ValueError:
            d = datetime.now()
        d = d + timedelta(days=days)
        return d.strftime("%Y/%m/%d")