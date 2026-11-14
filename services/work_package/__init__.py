"""سرویس‌های پکیج سند (Work Package) — نسخه‌ی مستقل.

این سرویس‌ها کاملاً از سرویس‌های قبلی (services/documents) جدا هستند
و روی جدول‌های document_package_* کار می‌کنند.
"""

from . import wp_event_service
from . import wp_service
from . import wp_sla_service
from . import wp_assignment_service
from . import wp_attachment_service
from . import wp_deficiency_service
from . import wp_alarm_service

__all__ = [
    "wp_event_service",
    "wp_service",
    "wp_sla_service",
    "wp_assignment_service",
    "wp_attachment_service",
    "wp_deficiency_service",
    "wp_alarm_service",
]