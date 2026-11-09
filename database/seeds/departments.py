"""داده‌های پیش‌فرض — دپارتمان‌های پیش‌فرض

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""

import os
from datetime import datetime

from config import Config

from ..connection import get_connection
from helpers.date_helper import now_tehran, now_tehran_str


def create_default_departments():
    departments = [
        {"title": "دفتر فنی", "code": "technical_office", "sort_order": 1},
        {"title": "کنترل مستندات", "code": "document_control", "sort_order": 2},
        {"title": "متره برآورد", "code": "quantity_survey", "sort_order": 3},
        {"title": "بازنگری طرح", "code": "design_review", "sort_order": 4},
        {"title": "برنامه ریزی و کنترل پروژه", "code": "planning_project_control", "sort_order": 5},
        {"title": "پیمان رسیدگی", "code": "contract_review", "sort_order": 6},
        {"title": "کنترل کیفی", "code": "quality_control", "sort_order": 7},
        {"title": "نظارت کارگاهی", "code": "site_supervision", "sort_order": 8},
        {"title": "ایمنی", "code": "safety", "sort_order": 9},
        {"title": "عمومی", "code": "general", "sort_order": 10},
    ]
    connection = get_connection()
    try:
        for department in departments:
            existing = connection.execute(
                "SELECT id FROM departments WHERE code = ?",
                (department["code"],)
            ).fetchone()
            if existing:
                continue
            connection.execute("""
                INSERT INTO departments (title, code, sort_order, is_active)
                VALUES (?, ?, ?, 1)
            """, (department["title"], department["code"],
                  department["sort_order"]))
        connection.commit()
    finally:
        connection.close()


def run():
    """اجرای seed این ماژول."""
    create_default_departments()
