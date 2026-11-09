"""داده‌های پیش‌فرض — پیمانکاران پیش‌فرض

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""

import os
from datetime import datetime

from config import Config

from ..connection import get_connection
from helpers.date_helper import now_tehran, now_tehran_str


def create_default_contractors():
    contractors = []
    if not contractors:
        return
    inserted = 0
    for c in contractors:
        if c.get("code"):
            existing = get_contractor_by_code(c["code"])
            if existing:
                continue
        new_id = create_contractor(**c)
        if new_id:
            inserted += 1
    if inserted:
        print(f"✅ {inserted} پیمانکار پیش‌فرض ایجاد شد")


def run():
    """اجرای seed این ماژول."""
    create_default_contractors()
