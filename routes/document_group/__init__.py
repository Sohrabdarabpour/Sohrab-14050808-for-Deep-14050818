from flask import Blueprint

document_group_bp = Blueprint(
    "document_group",
    __name__,
    url_prefix="/document-groups",
)

# ★ وارد کردن روت‌ها برای ثبت در Blueprint
from . import group_routes     # noqa: E402, F401
from . import subgroup_routes  # noqa: E402, F401