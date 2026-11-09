from flask import Blueprint

reports_bp = Blueprint(
    "reports",
    __name__,
    url_prefix="/reports"
)

from . import projects
from . import contractors
from . import delays
from . import status
from . import status_documents
from . import units
from . import experts
from . import department
from . import department_documents
from . import department_expert_documents
from . import area
from . import area_departments
from . import department_performance       # ★ این خط اضافه شد
from . import responsible                  # ★ مسئول رسیدگی (قبلاً import نمی‌شد)


__all__ = ["reports_bp"]