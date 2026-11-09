from flask import Blueprint

contractor_bp = Blueprint(
    "contractors",
    __name__,
    url_prefix="/contractors"
)

from . import contractor_routes  # noqa: E402, F401

__all__ = ["contractor_bp"]