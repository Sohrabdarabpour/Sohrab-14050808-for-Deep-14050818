"""routes/documents — بسته‌بندی خودکار بر اساس موجودیت.

ترتیب import مهم است:
1. documents_routes → documents_bp را می‌سازد
2. attachment_routes → روت‌های پیوست را روی همان documents_bp ثبت می‌کند
"""

"""routes/documents — بسته‌بندی خودکار بر اساس موجودیت."""
"""routes/documents — بسته‌بندی خودکار بر اساس موجودیت."""

from .documents_routes import documents_bp

from . import attachment_routes       # noqa: F401
from . import assignment_routes      # noqa: F401
from . import assignment_test_routes # noqa: F401
from . import package_routes         # noqa: F401  ★ جدید
from . import reference_routes  # noqa: F401
from . import completion_routes  # noqa: F401


__all__ = ["documents_bp"]