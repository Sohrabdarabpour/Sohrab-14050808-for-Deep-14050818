"""داده‌های پیش‌فرض — نقش‌های پروژه پیش‌فرض

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""

import os
from datetime import datetime

from config import Config

from ..connection import get_connection
from helpers.date_helper import now_tehran, now_tehran_str


def create_default_project_roles():
    roles = [
        ("مدیر پروژه",    "manager",            "#1b698b", 1, 0, 1),
        ("کنترل پروژه",   "project_controller", "#167a5c", 1, 1, 2),
        ("کنترل مستندات", "doc_controller",     "#d69e2e", 1, 0, 3),
        ("ناظر",          "supervisor",         "#c05621", 1, 0, 4),
        ("کارشناس فنی",   "technical_expert",   "#805ad5", 0, 0, 5),
        ("کارشناس مالی",  "financial_expert",   "#319795", 0, 0, 6),
        ("هماهنگ‌کننده",   "coordinator",        "#2b6cb0", 0, 0, 7),
        ("عضو تیم",       "team_member",        "#718096", 0, 0, 8),
    ]
    connection = get_connection()
    try:
        inserted = 0
        for title, code, color, excl, req, sort_order in roles:
            existing = connection.execute(
                "SELECT id FROM project_roles WHERE code = ?",
                (code,)
            ).fetchone()
            if existing:
                continue
            connection.execute("""
                INSERT INTO project_roles
                (title, code, color, is_exclusive, is_required,
                 sort_order, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (title, code, color, excl, req, sort_order))
            inserted += 1
        connection.commit()
        if inserted:
            print(f"✅ {inserted} نقش پروژه پیش‌فرض ایجاد شد")
    finally:
        connection.close()


def run():
    """اجرای seed این ماژول."""
    create_default_project_roles()
