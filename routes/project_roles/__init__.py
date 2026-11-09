from flask import Blueprint

project_roles_bp = Blueprint(
    "project_roles",
    __name__,
    url_prefix="/project-roles"
)

from . import project_role_routes  # noqa: E402, F401

__all__ = ["project_roles_bp"]