"""بسته داده‌های پیش‌فرض

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""
from . import statuses
from . import areas
from . import departments
from . import document_groups
from . import contract_types
from . import project_roles
from . import workflow_steps
from . import admin
from . import contractors
from . import holidays

SEED_STEPS = [
    ("وضعیت‌های پیش‌فرض اسناد", statuses.run),
    ("نواحی پیش‌فرض", areas.run),
    ("دپارتمان‌های پیش‌فرض", departments.run),
    ("گروه‌های سند پیش‌فرض", document_groups.run),
    ("تعطیلات ثابت تقویم", holidays.run),
    ("انواع قرارداد پیش‌فرض", contract_types.run),
    ("نقش‌های پروژه پیش‌فرض", project_roles.run),
    ("مراحل گردش‌کار پیش‌فرض", workflow_steps.run),
    ("کاربر مدیر سیستم", admin.run),
    ("پیمانکاران پیش‌فرض", contractors.run),
]


def run_all():
    """اجرای همه seedها به ترتیب وابستگی."""
    for _label, step in SEED_STEPS:
        step()
