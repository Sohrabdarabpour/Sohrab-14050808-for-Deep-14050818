"""بسته جداول — ساختار دیتابیس

هر جدول در فایل خودش قرار دارد و فقط DDL است (ساختار + ایندکس).
منطق خواندن/نوشتن در database/repositories/ است.
"""

from . import users
from . import document_statuses
from . import areas
from . import departments
from . import document_groups
from . import document_subgroups
from . import group_subgroups
from . import subgroup_departments
from . import documents
from . import contractors
from . import contract_types
from . import project_roles
from . import projects
from . import project_members
from . import workflow_steps
from . import document_notes
from . import note_events
from . import notifications
from . import assistant_logs
from . import assistant_feedback
from . import calendar_holidays
from . import calendar_holiday_events

TABLES = [
    users,
    document_statuses,
    areas,
    departments,
    document_groups,
    document_subgroups,
    group_subgroups,
    subgroup_departments,
    documents,
    contractors,
    contract_types,
    project_roles,
    projects,
    project_members,
    workflow_steps,
    document_notes,
    note_events,
    notifications,
    assistant_logs,
    assistant_feedback,
    calendar_holidays,
    calendar_holiday_events,
]

__all__ = ["TABLES", "create_all", "create_indexes"]


def create_all(cursor):
    """ساخت همه جداول به ترتیب وابستگی."""
    for module in TABLES:
        module.create(cursor)


def create_indexes(cursor):
    """ساخت ایندکس‌های هر جدول (در همان فایل جدول تعریف شده‌اند)."""
    for module in TABLES:
        for statement in module.INDEX_SQL:
            cursor.execute(statement)
