"""سرویس‌های دپارتمان‌ها — بسته‌بندی خودکار بر اساس موجودیت."""
from .department_service import DepartmentService
from .department_documents_service import DepartmentDocumentsService
from .department_expert_documents_service import DepartmentExpertDocumentsService
from .department_performance_service import DepartmentPerformanceService
from .department_report_service import DepartmentReportService
__all__ = [
    "DepartmentService",
    "DepartmentDocumentsService",
    "DepartmentExpertDocumentsService",
    "DepartmentPerformanceService",
    "DepartmentReportService",
]
