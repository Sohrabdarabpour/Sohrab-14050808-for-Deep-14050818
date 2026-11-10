"""Blueprint کارتابل."""

from flask import Blueprint

inbox_bp = Blueprint(
    "inbox",
    __name__,
    url_prefix="/inbox",
)

from . import inbox_routes  # noqa: E402,F401

__all__ = ["inbox_bp"]