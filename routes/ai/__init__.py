"""
پکیج روت‌های هوش مصنوعی
"""
from .assistant import assistant_bp
from . import export_routes  # noqa: F401  (ثبت endpoint خروجی اکسل)

__all__ = ["assistant_bp"]
