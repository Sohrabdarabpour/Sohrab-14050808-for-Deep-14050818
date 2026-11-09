"""مهلت پاسخ سند بر اساس گروه/زیرگروه و تقویم کاری.

اولویت تعیین مهلت:

1. ``document_subgroups.days_review`` (اگر بزرگ‌تر از صفر باشد)
2. ``document_groups.days_review``
3. ``Config.DEFAULT_SLA_DAYS``

مهلت = تاریخ شروع + N **روز کاری** (تعطیلات رسمی و آخر هفته کسر می‌شود).
این ماژول فقط منطق است؛ خواندن/نوشتن در ``database/repositories`` انجام می‌شود.
"""

from datetime import date

from config import Config
from database.repositories import document_groups as groups_repo
from database.repositories import documents as documents_repo
from services.calendar import working_days

SOURCE_LABELS = {
    "subgroup": "زیرگروه سند",
    "group": "گروه سند",
    "default": "پیش‌فرض سامانه",
}


def _positive_int(value):
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return number if number > 0 else 0


def resolve_days(group_id=None, subgroup_id=None):
    """مهلت مؤثر (روز کاری) و منبع آن: (days, source)."""
    group_days, subgroup_days = groups_repo.get_days_review(group_id, subgroup_id)

    if _positive_int(subgroup_days):
        return _positive_int(subgroup_days), "subgroup"
    if _positive_int(group_days):
        return _positive_int(group_days), "group"

    return _positive_int(Config.DEFAULT_SLA_DAYS) or 7, "default"


def compute_due(start_date, days):
    """تاریخ سررسید (میلادی YYYY/MM/DD) با کسر تعطیلات."""
    due = working_days.add_working_days(start_date, days)
    return working_days.format_gregorian(due)


def preview(group_id=None, subgroup_id=None, start_date=None):
    """پیش‌نمایش کامل برای فرم/تقویم."""
    start = working_days.parse_date(start_date) or date.today()
    days, source = resolve_days(group_id, subgroup_id)
    due = working_days.add_working_days(start, days)

    return {
        "start": working_days.format_gregorian(start),
        "start_jalali": working_days.format_jalali(start),
        "days": days,
        "source": source,
        "source_label": SOURCE_LABELS.get(source, source),
        "due": working_days.format_gregorian(due),
        "due_jalali": working_days.format_jalali(due),
        "working_days_between": working_days.count_working_days(start, due),
        "calendar_days": (due - start).days if due else 0,
    }


def apply_to_document(document_id, start_date=None):
    """محاسبه و ذخیرهٔ مهلت پاسخ روی یک سند."""
    row = documents_repo.get_sla_inputs(document_id)
    if not row:
        return None

    result = preview(
        row["group_id"],
        row["subgroup_id"],
        start_date or row["date_received"],
    )

    documents_repo.update_sla(
        document_id,
        result["days"],
        result["source"],
        result["due"],
    )
    return result


def list_groups():
    """گروه‌های فعال برای انتخاب در فرم (همراه مهلت)."""
    return groups_repo.list_groups_with_sla()


def list_subgroups(group_id=None):
    """زیرگروه‌های فعال؛ در صورت تعیین گروه، فقط زیرگروه‌های همان گروه."""
    return groups_repo.list_subgroups_with_sla(group_id)
