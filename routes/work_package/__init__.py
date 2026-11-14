"""Blueprint پکیج سند (Work Package).

مسیرها: /work-package/...
"""

from flask import Blueprint

work_package_bp = Blueprint(
    "work_package",
    __name__,
    url_prefix="/work-package",
)

from . import wp_routes         # noqa: E402,F401
from . import wp_step_routes    # noqa: E402,F401
from . import wp_api_routes     # noqa: E402,F401
from . import wp_attachment_routes  # noqa: E402,F401

__all__ = ["work_package_bp"]