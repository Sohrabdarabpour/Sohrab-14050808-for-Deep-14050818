"""بسته جداول — ساختار دیتابیس"""

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

# ★★★ جدید — پکیج سند
from . import document_counters
from . import document_assignments
from . import document_events
from . import document_references
from . import document_completion_requests
from . import document_attachments
from . import document_alarms
from . import document_watchers


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

    # ★★★ جدید — پکیج سند (بعد از documents و users)
    document_counters,
    document_assignments,
    document_events,
    document_references,
    document_completion_requests,
    document_attachments,
    document_alarms,
    document_watchers,
]

__all__ = ["TABLES", "create_all", "create_indexes"]


def create_all(cursor):
    for module in TABLES:
        module.create(cursor)


def create_indexes(cursor):
    for module in TABLES:
        for statement in module.INDEX_SQL:
            cursor.execute(statement)