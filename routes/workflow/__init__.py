"""
Blueprint گردش‌کار
"""
from flask import Blueprint

workflow_bp = Blueprint(
    "workflow",
    __name__,
    url_prefix="/workflow",
)

notification_bp = Blueprint(
    "notifications",
    __name__,
    url_prefix="/notifications",
)

# ★ ایمپورت روت‌ها بعد از تعریف Blueprint
from . import note_routes          # noqa: E402, F401
from . import notification_routes  # noqa: E402, F401

__all__ = ["workflow_bp", "notification_bp"]