from flask import Blueprint

projects_bp = Blueprint(
    "projects",
    __name__,
    url_prefix="/projects"
)

from . import project_routes  # noqa: E402, F401

__all__ = ["projects_bp"]