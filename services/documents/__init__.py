"""سرویس‌های اسناد — بسته‌بندی خودکار بر اساس موجودیت.

شامل:
- DocumentService (قدیمی — خواندن/جستجوی اسناد)
- event_service (جدید — تایم‌لاین)
- storage_service (جدید — آپلود/پیش‌نمایش)
- package_service (جدید — ثبت + شماره‌گذاری + مرحله)
"""

"""سرویس‌های اسناد."""

"""سرویس‌های اسناد."""

"""سرویس‌های اسناد."""

from .document_service import DocumentService
from . import event_service
from . import storage_service
from . import package_service
from . import assignment_service
from . import sla_service
from . import alarm_service
from . import reference_service
from . import completion_service

__all__ = [
    "DocumentService",
    "event_service",
    "storage_service",
    "package_service",
    "assignment_service",
    "sla_service",
    "alarm_service",
    "reference_service",
    "completion_service",
]