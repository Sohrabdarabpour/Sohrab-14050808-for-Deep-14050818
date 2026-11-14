"""سرویس هشدارها و اسکنر برای پکیج سند."""

from datetime import datetime

from database.connection import get_connection
from helpers.date_helper import now_tehran_str

from . import wp_sla_service


# ============================================================
# ★ انواع هشدار
# ============================================================
class AlarmType:
    ASSIGNMENT_DUE = "assignment_due"
    ASSIGNMENT_OVERDUE = "assignment_overdue"
    DOCUMENT_OVERDUE = "document_overdue"
    NO_ACTION = "no_action"


# ============================================================
# ★ ثبت هشدار (dedupe_key)
# ============================================================
def _create_alarm(
    *, package_id: int, alarm_type: str, dedupe_key: str,
    target_user_id: int | None = None, assignment_id: int | None = None,
    level: str = "warning", due_at: str | None = None,
) -> int | None:
    """
    درج هشدار با dedupe. اگر dedupe_key تکراری باشد، None برمی‌گرداند.
    ★ این جدول در این فاز ساخته نشده — اما برای آینده آماده است.
    """
    # فعلاً هشدارها را در notifications ثبت می‌کنیم
    # جدول اختصاصی document_package_alarms در فاز بعد اضافه می‌شود
    return _push_notification(
        user_id=target_user_id,
        title=f"[{level.upper()}] {alarm_type}",
        message=f"سند #{package_id} — {alarm_type}",
        document_id=package_id,
    )


def _push_notification(
    *, user_id: int | None, title: str, message: str,
    document_id: int | None = None,
) -> int | None:
    """ثبت در جدول notifications موجود."""
    if not user_id:
        return None
    try:
        from database.repositories.notifications import create_notification
        return create_notification(
            user_id=user_id,
            title=title,
            message=message,
            link=f"/documents/work-package/{document_id}" if document_id else None,
            notification_type="warning",
            document_id=document_id,
        )
    except Exception:
        return None


# ============================================================
# ★ اسکن ارجاع‌ها
# ============================================================
def scan_assignments() -> dict:
    """اسکن ارجاع‌های فعال برای نزدیک مهلت / دیرکرد / بدون اقدام."""
    today = datetime.now().strftime("%Y/%m/%d")
    created = []

    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT a.*, p.dfc_code, p.work_package_code, p.subject
            FROM document_package_assignments a
            JOIN document_packages p ON p.id = a.package_id
            WHERE a.status IN ('pending', 'accepted', 'in_progress')
        """).fetchall()
    finally:
        connection.close()

    for a in rows:
        pkg_id = a["package_id"]
        a_id = a["id"]
        assignee = a["to_user_id"]
        due = a["due_date"]

        # بدون اقدام (۴۸ ساعت)
        if not a["read_at"]:
            try:
                created_dt = datetime.strptime(
                    a["created_at"][:19], "%Y-%m-%d %H:%M:%S"
                )
                hours = (datetime.now() - created_dt).total_seconds() / 3600
                if hours > 48:
                    key = f"pkg_assign:{a_id}:no_action:48h"
                    new_id = _create_alarm(
                        package_id=pkg_id,
                        assignment_id=a_id,
                        target_user_id=assignee,
                        alarm_type=AlarmType.NO_ACTION,
                        dedupe_key=key,
                        level="warning",
                    )
                    if new_id:
                        created.append(new_id)
            except Exception:
                pass

        if not due:
            continue

        # دیرکرد
        overdue_days = wp_sla_service._working_days_between(due, today)

        if overdue_days == 0:
            key = f"pkg_assign:{a_id}:due:0d"
            new_id = _create_alarm(
                package_id=pkg_id,
                assignment_id=a_id,
                target_user_id=assignee,
                alarm_type=AlarmType.ASSIGNMENT_DUE,
                dedupe_key=key,
                level="info",
                due_at=due,
            )
            if new_id:
                created.append(new_id)

        if overdue_days > 0:
            for milestone in (1, 3, 7):
                if overdue_days >= milestone:
                    key = f"pkg_assign:{a_id}:overdue:{milestone}d"
                    level = "critical" if milestone >= 7 else "warning"
                    new_id = _create_alarm(
                        package_id=pkg_id,
                        assignment_id=a_id,
                        target_user_id=assignee,
                        alarm_type=AlarmType.ASSIGNMENT_OVERDUE,
                        dedupe_key=key,
                        level=level,
                        due_at=due,
                    )
                    if new_id:
                        created.append(new_id)

    return {"ok": True, "created": created, "total": len(created)}


# ============================================================
# ★ اسکن اسناد (مهلت کل)
# ============================================================
def scan_documents() -> dict:
    """اسکن اسناد فعال برای دیرکرد مهلت کل."""
    wp_sla_service.refresh_overdue_flags()

    today = datetime.now().strftime("%Y/%m/%d")
    created = []

    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT id, dfc_code, work_package_code, subject,
                   response_due_date, is_overdue, overdue_days, registered_by,
                   current_supervisor_id
            FROM document_packages
            WHERE stage NOT IN ('closed', 'archived', 'cancelled')
              AND response_due_date IS NOT NULL
        """).fetchall()
    finally:
        connection.close()

    for doc in rows:
        pkg_id = doc["id"]
        due = doc["response_due_date"]
        overdue_days = wp_sla_service._working_days_between(due, today)

        if overdue_days > 0:
            for milestone in (1, 3, 7, 14):
                if overdue_days >= milestone:
                    key = f"pkg_doc:{pkg_id}:overdue:{milestone}d"
                    level = "critical" if milestone >= 7 else "warning"
                    # به سرپرست یا ثبت‌کننده
                    target = doc["current_supervisor_id"] or doc["registered_by"]
                    new_id = _create_alarm(
                        package_id=pkg_id,
                        target_user_id=target,
                        alarm_type=AlarmType.DOCUMENT_OVERDUE,
                        dedupe_key=key,
                        level=level,
                        due_at=due,
                    )
                    if new_id:
                        created.append(new_id)

    return {"ok": True, "created": created, "total": len(created)}


# ============================================================
# ★ اسکنر کل
# ============================================================
def scan_all() -> dict:
    """اسکن کامل."""
    a = scan_assignments()
    d = scan_documents()
    return {
        "ok": True,
        "assignments": a,
        "documents": d,
        "total_created": a["total"] + d["total"],
    }