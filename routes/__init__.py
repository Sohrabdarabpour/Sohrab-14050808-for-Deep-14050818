# Sohrab/routes/__init__.py
"""
routes package — همه Blueprintها
"""

# ============================================================
# ★ Blueprintهای اصلی
# ============================================================
from .auth import auth_bp
from .main import main_bp
from .dashboard import dashboard_bp
from .panel import panel_bp
from .excel import excel_bp
from .documents import documents_bp
from .departments import departments_bp

# ============================================================
# ★ Blueprintهای جانبی
# ============================================================
from .reports import reports_bp
from .profile import profile_bp
from .document_group import document_group_bp
from .ai import assistant_bp

# ============================================================
# ★ ماژول‌های جدید
# ============================================================
from .contractors import contractor_bp
from .contract_types import contract_types_bp
from .project_roles import project_roles_bp
from .projects import projects_bp

# ============================================================
# ★ Workflow
# ============================================================
from .workflow import workflow_bp, notification_bp

# ============================================================
# ★ جستجوی پیشرفته
# ============================================================
from .search import search_bp

# ============================================================
# ★ تقویم کاری و مهلت پاسخ
# ============================================================
from .calendar import calendar_bp


__all__ = [
    # ---- اصلی ----
    "auth_bp",
    "main_bp",
    "dashboard_bp",
    "panel_bp",
    "excel_bp",
    "documents_bp",
    "departments_bp",

    # ---- جانبی ----
    "reports_bp",
    "profile_bp",
    "document_group_bp",
    "assistant_bp",

    # ---- ماژول‌ها ----
    "contractor_bp",
    "contract_types_bp",
    "project_roles_bp",
    "projects_bp",

    # ---- Workflow ----
    "workflow_bp",
    "notification_bp",

    # ---- جستجو ----
    "search_bp",

    # ---- تقویم ----
    "calendar_bp",
]