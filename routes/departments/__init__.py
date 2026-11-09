from flask import Blueprint

departments_bp = Blueprint(
    "departments",
    __name__,
    url_prefix="/departments"
)

from . import department_routes

__all__ = ["departments_bp"]