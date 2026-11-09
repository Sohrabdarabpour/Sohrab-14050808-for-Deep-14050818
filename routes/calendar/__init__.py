"""Blueprint تقویم کاری و مهلت پاسخ."""

from flask import Blueprint

calendar_bp = Blueprint("calendar", __name__, url_prefix="/calendar")

from . import calendar_routes  # noqa: E402,F401

__all__ = ["calendar_bp"]
