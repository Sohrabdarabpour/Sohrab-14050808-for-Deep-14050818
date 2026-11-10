"""سرویس محاسبه‌ی مهلت پاسخ (SLA).

قواعد:
- اولویت: زیرگروه → گروه → پیش‌فرض (SSPE_DEFAULT_SLA_DAYS)
- محاسبه با روزهای کاری (پنجشنبه/جمعه + تعطیلات)
- ذخیره روی سند: sla_days / sla_source / sla_start_date /
  sla_effective_days / response_due_date / is_overdue / overdue_days
- هر محاسبه، رویداد sla_recalculated ثبت می‌کند
- تابع refresh_overdue_flags برای اسکنر
"""

from datetime import datetime

from config import Config
from database.connection import get_connection
from helpers.date_helper import now_tehran_str

from . import event_service


# ============================================================
# ★ محاسبه‌ی مهلت مؤثر
# ============================================================
def _resolve_sla_days(group_id, subgroup_id):
    """
    تعیین روزهای مهلت با اولویت زیرگروه → گروه → پیش‌فرض.

    Returns:
        (days: int, source: str)
    """
    connection = get_connection()
    try:
        # ۱. زیرگروه
        if subgroup_id:
            row = connection.execute(
                "SELECT days_review FROM document_subgroups WHERE id = ?",
                (subgroup_id,),
            ).fetchone()
            if row and row["days_review"] and row["days_review"] > 0:
                return int(row["days_review"]), "subgroup"

        # ۲. گروه
        if group_id:
            row = connection.execute(
                "SELECT days_review FROM document_groups WHERE id = ?",
                (group_id,),
            ).fetchone()
            if row and row["days_review"] and row["days_review"] > 0:
                return int(row["days_review"]), "group"

        # ۳. پیش‌فرض
        return Config.DEFAULT_SLA_DAYS, "default"
    finally:
        connection.close()


def _add_working_days(start_date_str, days):
    """افزودن N روز کاری به تاریخ میلادی. همیشه رشته برمی‌گرداند."""
    try:
        from services.calendar.working_days import add_working_days
        result = add_working_days(start_date_str, days)
        if hasattr(result, "strftime"):
            return result.strftime("%Y/%m/%d")
        return str(result)
    except (ImportError, Exception):
        from datetime import timedelta
        try:
            d = datetime.strptime(start_date_str, "%Y/%m/%d")
        except ValueError:
            d = datetime.now()
        d = d + timedelta(days=days)
        return d.strftime("%Y/%m/%d")


def _working_days_between(start_str, end_str):
    """تعداد روز کاری بین دو تاریخ (اگر end قبل از start باشد → 0)."""
    try:
        from services.calendar.working_days import working_days_between
        result = working_days_between(start_str, end_str)
        return max(0, int(result))
    except (ImportError, Exception):
        try:
            s = datetime.strptime(start_str, "%Y/%m/%d")
            e = datetime.strptime(end_str, "%Y/%m/%d")
            diff = (e - s).days
            return max(0, diff)
        except (ValueError, TypeError):
            return 0


# ============================================================
# ★ محاسبه و ذخیره‌ی SLA
# ============================================================
def recalculate_sla(document_id: int, actor_id: int | None = None) -> dict:
    """
    محاسبه‌ی مجدد SLA سند و ذخیره روی آن.

    Returns:
        dict با کلیدهای ok, error, sla_days, sla_source, response_due_date
    """
    connection = get_connection()
    try:
        doc = connection.execute("""
            SELECT id, group_id, subgroup_id, date_received,
                   sla_effective_days, sla_start_date, response_due_date
            FROM documents WHERE id = ?
        """, (document_id,)).fetchone()

        if not doc:
            return {"ok": False, "error": "سند پیدا نشد"}

        start_date = doc["date_received"] or doc["sla_start_date"]
        if not start_date:
            # اگر تاریخ دریافت ندارد، از امروز شروع کن
            start_date = datetime.now().strftime("%Y/%m/%d")

        days, source = _resolve_sla_days(
            doc["group_id"], doc["subgroup_id"]
        )
        due_date = _add_working_days(start_date, days)

        # محاسبه‌ی دیرکرد
        today = datetime.now().strftime("%Y/%m/%d")
        overdue_days = _working_days_between(due_date, today)
        is_overdue = 1 if overdue_days > 0 else 0

        connection.execute("""
            UPDATE documents
            SET sla_days = ?,
                sla_source = ?,
                sla_start_date = ?,
                sla_effective_days = ?,
                response_due_date = ?,
                is_overdue = ?,
                overdue_days = ?
            WHERE id = ?
        """, (
            days, source, start_date, days, due_date,
            is_overdue, overdue_days, document_id,
        ))
        connection.commit()

        # ★ رویداد
        try:
            event_service.log_event(
                document_id=document_id,
                actor_id=actor_id,
                event_type=event_service.EventType.SLA_RECALCULATED,
                summary=(
                    f"مهلت پاسخ: {days} روز کاری "
                    f"(منبع: {source}) — سررسید {due_date}"
                ),
                payload={
                    "sla_days": days,
                    "sla_source": source,
                    "sla_start_date": start_date,
                    "response_due_date": due_date,
                    "is_overdue": bool(is_overdue),
                    "overdue_days": overdue_days,
                },
            )
        except Exception:
            pass

        return {
            "ok": True,
            "sla_days": days,
            "sla_source": source,
            "sla_start_date": start_date,
            "response_due_date": due_date,
            "is_overdue": bool(is_overdue),
            "overdue_days": overdue_days,
        }
    except Exception as exc:
        connection.rollback()
        return {"ok": False, "error": f"خطا: {exc}"}
    finally:
        connection.close()


# ============================================================
# ★ به‌روزرسانی پرچم دیرکرد همه‌ی اسناد فعال
# ============================================================
def refresh_overdue_flags() -> dict:
    """
    اسکن همه‌ی اسناد فعال و به‌روزرسانی is_overdue / overdue_days.

    Returns:
        dict با تعداد اسناد به‌روزشده و لیست آن‌ها
    """
    connection = get_connection()
    updated = []
    try:
        rows = connection.execute("""
            SELECT id, response_due_date, sla_effective_days,
                   is_overdue, overdue_days
            FROM documents
            WHERE stage NOT IN ('closed', 'archived', 'cancelled')
              AND response_due_date IS NOT NULL
        """).fetchall()

        today = datetime.now().strftime("%Y/%m/%d")

        for row in rows:
            due = row["response_due_date"]
            overdue_days = _working_days_between(due, today)
            new_is_overdue = 1 if overdue_days > 0 else 0

            if (new_is_overdue != row["is_overdue"]
                    or overdue_days != row["overdue_days"]):
                connection.execute("""
                    UPDATE documents
                    SET is_overdue = ?, overdue_days = ?
                    WHERE id = ?
                """, (new_is_overdue, overdue_days, row["id"]))
                updated.append({
                    "id": row["id"],
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
# ★ آیا سند دیرکرد دارد؟ (برای هشدارها)
# ============================================================
def is_document_overdue(document_id: int) -> bool:
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT is_overdue FROM documents WHERE id = ?",
            (document_id,),
        ).fetchone()
        return bool(row and row["is_overdue"])
    finally:
        connection.close()