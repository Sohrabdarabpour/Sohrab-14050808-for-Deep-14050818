"""سرویس SLA برای پکیج سند.

اولویت: زیرگروه → گروه → پیش‌فرض
محاسبه با احتساب روزهای کاری و تعطیلات.
"""

from datetime import datetime

from config import Config
from database.connection import get_connection
from helpers.date_helper import now_tehran_str

from . import wp_event_service


# ============================================================
# ★ محاسبه‌ی SLA
# ============================================================
def recalculate_sla(package_id: int, actor_id: int | None = None) -> dict:
    """محاسبه‌ی مجدد SLA بر اساس گروه/زیرگروه."""
    connection = get_connection()
    try:
        row = connection.execute("""
            SELECT id, group_id, subgroup_id, date_received
            FROM document_packages WHERE id = ?
        """, (package_id,)).fetchone()
        if not row:
            return {"ok": False, "error": "سند پیدا نشد"}

        start_date = row["date_received"] or datetime.now().strftime("%Y/%m/%d")
        days, source = _resolve_sla_days(
            connection, row["group_id"], row["subgroup_id"],
        )
        due_date = _add_working_days(start_date, days)

        # محاسبه‌ی دیرکرد
        today = datetime.now().strftime("%Y/%m/%d")
        overdue_days = _working_days_between(due_date, today)
        is_overdue = 1 if overdue_days > 0 else 0

        connection.execute("""
            UPDATE document_packages
            SET sla_days = ?, sla_source = ?, sla_start_date = ?,
                sla_effective_days = ?, response_due_date = ?,
                is_overdue = ?, overdue_days = ?, updated_at = ?
            WHERE id = ?
        """, (
            days, source, start_date, days, due_date,
            is_overdue, overdue_days, now_tehran_str(), package_id,
        ))
        connection.commit()
    finally:
        connection.close()

    try:
        wp_event_service.log_event(
            package_id=package_id,
            actor_id=actor_id,
            event_type=wp_event_service.EventType.SLA_RECALCULATED,
            summary=f"SLA محاسبه شد: {days} روز کاری ({source})",
            payload={
                "sla_days": days, "sla_source": source,
                "response_due_date": due_date,
                "is_overdue": bool(is_overdue),
                "overdue_days": overdue_days,
            },
        )
    except Exception:
        pass

    return {
        "ok": True,
        "sla_days": days, "sla_source": source,
        "response_due_date": due_date,
        "is_overdue": bool(is_overdue),
        "overdue_days": overdue_days,
    }


# ============================================================
# ★ به‌روزرسانی پرچم دیرکرد
# ============================================================
def refresh_overdue_flags() -> dict:
    connection = get_connection()
    updated = []
    try:
        rows = connection.execute("""
            SELECT id, response_due_date, is_overdue, overdue_days
            FROM document_packages
            WHERE stage NOT IN ('closed', 'archived', 'cancelled')
              AND response_due_date IS NOT NULL
        """).fetchall()

        today = datetime.now().strftime("%Y/%m/%d")
        for r in rows:
            overdue_days = _working_days_between(r["response_due_date"], today)
            new_is_overdue = 1 if overdue_days > 0 else 0
            if (new_is_overdue != r["is_overdue"]
                    or overdue_days != r["overdue_days"]):
                connection.execute("""
                    UPDATE document_packages
                    SET is_overdue = ?, overdue_days = ?
                    WHERE id = ?
                """, (new_is_overdue, overdue_days, r["id"]))
                updated.append({
                    "id": r["id"],
                    "overdue_days": overdue_days,
                    "is_overdue": bool(new_is_overdue),
                })

        connection.commit()
    except Exception as exc:
        connection.rollback()
        return {"ok": False, "error": str(exc)}
    finally:
        connection.close()

    return {"ok": True, "updated": updated, "total": len(updated)}


# ============================================================
# ★ کمکی‌ها
# ============================================================
def _resolve_sla_days(connection, group_id, subgroup_id):
    """اولویت: زیرگروه → گروه → پیش‌فرض."""
    if subgroup_id:
        row = connection.execute(
            "SELECT days_review FROM document_subgroups WHERE id = ?",
            (subgroup_id,),
        ).fetchone()
        if row and row["days_review"] and row["days_review"] > 0:
            return int(row["days_review"]), "subgroup"

    if group_id:
        row = connection.execute(
            "SELECT days_review FROM document_groups WHERE id = ?",
            (group_id,),
        ).fetchone()
        if row and row["days_review"] and row["days_review"] > 0:
            return int(row["days_review"]), "group"

    return Config.DEFAULT_SLA_DAYS, "default"


def _add_working_days(start_date_str, days):
    try:
        from services.calendar.working_days import add_working_days
        result = add_working_days(start_date_str, days)
        if hasattr(result, "strftime"):
            return result.strftime("%Y/%m/%d")
        return str(result)
    except Exception:
        from datetime import timedelta
        try:
            d = datetime.strptime(start_date_str, "%Y/%m/%d")
        except ValueError:
            d = datetime.now()
        return (d + timedelta(days=days)).strftime("%Y/%m/%d")


def _working_days_between(start_str, end_str):
    try:
        from services.calendar.working_days import working_days_between
        return max(0, int(working_days_between(start_str, end_str)))
    except Exception:
        try:
            s = datetime.strptime(start_str, "%Y/%m/%d")
            e = datetime.strptime(end_str, "%Y/%m/%d")
            return max(0, (e - s).days)
        except Exception:
            return 0


def preview_sla(group_id: int | None, subgroup_id: int | None,
                start_date: str | None = None) -> dict:
    """
    پیش‌نمایش SLA بدون ذخیره. برای نمایش زنده در فرم.
    """
    connection = get_connection()
    try:
        days, source = _resolve_sla_days(connection, group_id, subgroup_id)
    finally:
        connection.close()

    if not start_date:
        start_date = datetime.now().strftime("%Y/%m/%d")

    due = _add_working_days(start_date, days)

    from helpers.date_helper import DateHelper
    try:
        due_jalali = DateHelper.format_jalali(due)
    except Exception:
        due_jalali = due

    return {
        "ok": True,
        "sla_days": days,
        "sla_source": source,
        "start_date": start_date,
        "response_due_date": due,
        "response_due_date_jalali": due_jalali,
    }