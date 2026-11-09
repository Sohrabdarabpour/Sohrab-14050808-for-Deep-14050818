"""
سرویس‌های گردش‌کار
"""
from .note_service import NoteService
from .notification_service import NotificationService

# ★ برای سازگاری با کدهای قدیمی
WorkflowService = NoteService

__all__ = [
    "NoteService",
    "NotificationService",
    "WorkflowService",
]