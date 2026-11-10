"""سرویس هشدار — تولید و مدیریت هشدارهای زمان‌بندی‌شده.

ویژگی‌ها:
- dedupe_key یکتا → جلوگیری از اسپم
- هشدارهای ارجاع (نزدیک مهلت / دیرکرد / بدون اقدام)
- هشدارهای تکمیل مدارک
- هشدارهای مهلت کل سند
- اتصال به notifications موجود برای زنگ و badge
"""

from datetime import datetime, timedelta

from database.connection import get_connection
from helpers.date_helper import now_tehran_str

from . import sla_service


# ============================================================
# ★ انواع هشدار
# ============================================================
class AlarmType:
    ASSIGNMENT_DUE = "assignment_due"
    ASSIGNMENT_OVERDUE = "assignment_overdue"
    ASSIGNMENT_NO_ACTION = "assignment_no_action"
    COMPLETION_DUE = "completion_due"
    COMPLETION_OVERDUE = "completion_overdue"
    DOCUMENT_DEADLINE = "document_deadline"
    DOCUMENT_OVERDUE = "document_overdue"


# ============================================================
# ★ ثبت هشدار با dedupe
# ============================================================
def _create_alarm(
    *,
    document_id: int,
    alarm_type: str,
    dedupe_key: str,
    target_user_id: int | None = None,
    assignment_id: int | None = None,
    level: str = "warning",
    due_at: str | None = None,
    payload: dict | None = None,
) -> int | None:
    """
    درج هشدار با dedupe. اگر dedupe_key تکراری باشد، None برمی‌گرداند.
    """
    import json

    connection = get_connection()
    try:
        # بررسی dedupe
        existing = connection.execute(
            "SELECT id FROM document_alarms WHERE dedupe_key = ?",
            (dedupe_key,),
        ).fetchone()
        if existing:
            return None

        payload_json = None
        if payload:
            try:
                payload_json = json.dumps(payload, ensure_ascii=False, default=str)
            except Exception:
                payload_json = None

        cursor = connection.execute("""
            INSERT INTO document_alarms
            (document_id, assignment_id, target_user_id,
             alarm_type, level, due_at, status, dedupe_key, payload)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """, (
            document_id, assignment_id, target_user_id,
            alarm_type, level, due_at, dedupe_key, payload_json,
        ))
        connection.commit()
        return cursor.lastrowid
    except Exception:
        connection.rollback()
        return None
    finally:
        connection.close()


# ============================================================
# ★ اسکن ارجاع‌ها
# ============================================================
def scan_assignments() -> dict:
    """
    اسکن همه‌ی ارجاع‌های فعال:
    - نزدیک مهلت (۱ روز مانده)
    - دیرکرد (۱ / ۳ / ۷ روز)
    - بدون اقدام (> 48h از ایجاد و read_at NULL)
    """
    today = datetime.now().strftime("%Y/%m/%d")
    created = []

    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT a.*,
                   d.package_code, d.subject,
                   d.response_due_date
            FROM document_assignments a
            JOIN documents d ON d.id = a.document_id
            WHERE a.status IN ('pending', 'accepted', 'in_progress')
        """).fetchall()
    finally:
        connection.close()

    for a in rows:
        doc_id = a["document_id"]
        a_id = a["id"]
        assignee = a["to_user_id"]
        due = a["due_date"]

        # بدون اقدام
        if not a["read_at"]:
            try:
                created_dt = datetime.strptime(
                    a["created_at"][:19], "%Y-%m-%d %H:%M:%S"
                )
                if (datetime.now() - created_dt) > timedelta(hours=48):
                    key = f"assign:{a_id}:no_action:48h"
                    new_id = _create_alarm(
                        document_id=doc_id,
                        assignment_id=a_id,
                        target_user_id=assignee,
                        alarm_type=AlarmType.ASSIGNMENT_NO_ACTION,
                        dedupe_key=key,
                        level="warning",
                        payload={"hours_since": 48},
                    )
                    if new_id:
                        created.append(new_id)
                        _push_notification(
                            user_id=assignee,
                            title="ارجاع بدون اقدام",
                            message=f"سند {a['package_code'] or doc_id} هنوز خوانده نشده",
                            link=f"/inbox/?tab=unread",
                            document_id=doc_id,
                        )
            except (ValueError, TypeError):
                pass

        if not due:
            continue

        overdue_days = sla_service._working_days_between(due, today)

        # نزدیک مهلت (امروز ۱ روز مانده)
        if overdue_days == 0:
            key = f"assign:{a_id}:due:0d"
            new_id = _create_alarm(
                document_id=doc_id,
                assignment_id=a_id,
                target_user_id=assignee,
                alarm_type=AlarmType.ASSIGNMENT_DUE,
                dedupe_key=key,
                level="info",
                due_at=due,
            )
            if new_id:
                created.append(new_id)
                _push_notification(
                    user_id=assignee,
                    title="نزدیک مهلت ارجاع",
                    message=f"سند {a['package_code'] or doc_id} امروز مهلت دارد",
                    link="/inbox/",
                    document_id=doc_id,
                )

        # دیرکرد
        if overdue_days > 0:
            for milestone in (1, 3, 7):
                if overdue_days >= milestone:
                    key = f"assign:{a_id}:overdue:{milestone}d"
                    level = "critical" if milestone >= 7 else "warning"
                    new_id = _create_alarm(
                        document_id=doc_id,
                        assignment_id=a_id,
                        target_user_id=assignee,
                        alarm_type=AlarmType.ASSIGNMENT_OVERDUE,
                        dedupe_key=key,
                        level=level,
                        due_at=due,
                        payload={"overdue_days": overdue_days, "milestone": milestone},
                    )
                    if new_id:
                        created.append(new_id)
                        _push_notification(
                            user_id=assignee,
                            title=f"دیرکرد {milestone} روزه",
                            message=f"سند {a['package_code'] or doc_id} از مهلت گذشته",
                            link="/inbox/?tab=overdue",
                            document_id=doc_id,
                        )

    return {"ok": True, "created": created, "total": len(created)}


# ============================================================
# ★ اسکن مهلت کل سند
# ============================================================
def scan_documents() -> dict:
    """اسکن اسناد فعال برای نزدیکی/گذشت مهلت کل."""
    # ابتدا پرچم دیرکرد همه‌ی اسناد را به‌روز کن
    sla_service.refresh_overdue_flags()

    today = datetime.now().strftime("%Y/%m/%d")
    created = []

    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT id, package_code, subject, response_due_date,
                   is_overdue, overdue_days, registered_by
            FROM documents
            WHERE stage NOT IN ('closed', 'archived', 'cancelled')
              AND response_due_date IS NOT NULL
        """).fetchall()
    finally:
        connection.close()

    for doc in rows:
        doc_id = doc["id"]
        due = doc["response_due_date"]
        overdue_days = sla_service._working_days_between(due, today)

        # ۳ روز قبل
        if overdue_days == 0:
            pass  # امروز — هشدار warning
        elif overdue_days < 0 and abs(overdue_days) <= 3:
            pass  # نزدیک — می‌توان بعداً اضافه کرد

        if overdue_days > 0:
            for milestone in (1, 3, 7, 14):
                if overdue_days >= milestone:
                    key = f"doc:{doc_id}:overdue:{milestone}d"
                    level = "critical" if milestone >= 7 else "warning"
                    new_id = _create_alarm(
                        document_id=doc_id,
                        target_user_id=doc["registered_by"],
                        alarm_type=AlarmType.DOCUMENT_OVERDUE,
                        dedupe_key=key,
                        level=level,
                        due_at=due,
                        payload={"overdue_days": overdue_days, "milestone": milestone},
                    )
                    if new_id:
                        created.append(new_id)
                        if doc["registered_by"]:
                            _push_notification(
                                user_id=doc["registered_by"],
                                title=f"سند دیرکرد {milestone} روزه",
                                message=f"سند {doc['package_code'] or doc_id} از مهلت کل گذشته",
                                link=f"/documents/view/{doc_id}",
                                document_id=doc_id,
                            )

    return {"ok": True, "created": created, "total": len(created)}


# ============================================================
# ★ اسکنر کل (همه‌ی منابع)
# ============================================================
def scan_all() -> dict:
    """اسکن کامل — هم ارجاع‌ها، هم اسناد."""
    a = scan_assignments()
    d = scan_documents()
    return {
        "ok": True,
        "assignments": a,
        "documents": d,
        "total_created": a["total"] + d["total"],
    }


# ============================================================
# ★ ارسال notification داخلی
# ============================================================
def _push_notification(
    *,
    user_id: int,
    title: str,
    message: str,
    link: str | None = None,
    document_id: int | None = None,
):
    """ساخت ردیف در notifications موجود."""
    try:
        from database.repositories.notifications import create_notification
        create_notification(
            user_id=user_id,
            title=title,
            message=message,
            link=link,
            notification_type="warning",
            document_id=document_id,
        )
    except Exception:
        pass


# ============================================================
# ★ دریافت هشدارهای یک کاربر
# ============================================================
def list_user_alarms(user_id: int, *, status: str = "pending",
                     limit: int = 100) -> list[dict]:
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT a.*, d.package_code, d.subject
            FROM document_alarms a
            JOIN documents d ON d.id = a.document_id
            WHERE a.target_user_id = ? AND a.status = ?
            ORDER BY
              CASE a.level
                WHEN 'critical' THEN 1
                WHEN 'warning' THEN 2
                ELSE 3
              END,
              a.created_at DESC
            LIMIT ?
        """, (user_id, status, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


def ack_alarm(alarm_id: int) -> bool:
    """علامت‌گذاری هشدار به‌عنوان دیده‌شده."""
    connection = get_connection()
    try:
        connection.execute("""
            UPDATE document_alarms
            SET status = 'acked', acked_at = ?
            WHERE id = ?
        """, (now_tehran_str(), alarm_id))
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        return False
    finally:
        connection.close()