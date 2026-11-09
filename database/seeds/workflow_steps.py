"""داده‌های پیش‌فرض — مراحل گردش‌کار پیش‌فرض

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""

import os
from datetime import datetime

from config import Config

from ..connection import get_connection
from helpers.date_helper import now_tehran, now_tehran_str


def create_default_workflow_steps():
    steps = [
        {"code": "expert_submit", "title": "ثبت توسط کارشناس",
         "step_order": 1, "assigned_role": "expert", "is_final": 0},
        {"code": "supervisor_review", "title": "بررسی سرپرست",
         "step_order": 2, "assigned_role": "supervisor", "is_final": 0},
        {"code": "doc_controller_review", "title": "بررسی کنترل مستندات",
         "step_order": 3, "assigned_role": "doc_controller", "is_final": 1},
    ]
    connection = get_connection()
    try:
        inserted = 0
        for step in steps:
            existing = connection.execute(
                "SELECT id FROM workflow_steps WHERE code = ?", (step["code"],)
            ).fetchone()
            if existing:
                continue
            connection.execute("""
                INSERT INTO workflow_steps
                (code, title, step_order, assigned_role, is_final, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (step["code"], step["title"], step["step_order"],
                  step["assigned_role"], step["is_final"]))
            inserted += 1
        connection.commit()
        if inserted:
            print(f"✅ {inserted} مرحله گردش‌کار ایجاد شد")
    finally:
        connection.close()


def run():
    """اجرای seed این ماژول."""
    create_default_workflow_steps()
