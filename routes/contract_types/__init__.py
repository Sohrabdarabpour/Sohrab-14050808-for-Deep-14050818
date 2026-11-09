from flask import Blueprint

contract_types_bp = Blueprint(
    "contract_types",
    __name__,
    url_prefix="/contract-types"
)

from . import contract_type_routes  # noqa: E402, F401

__all__ = ["contract_types_bp"]