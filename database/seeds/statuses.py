"""داده‌های پیش‌فرض — وضعیت‌های پیش‌فرض اسناد

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""

import os
from datetime import datetime

from config import Config

from ..connection import get_connection
from helpers.date_helper import now_tehran, now_tehran_str


def create_default_statuses():
    statuses = [
        {"title": "تکمیل", "code": "completed", "color": "#00B894", "sort_order": 1},
        {"title": "در حال بررسی", "code": "in_progress", "color": "#3D8499", "sort_order": 2},
        {"title": "جهت اطلاع", "code": "informational", "color": "#E3DF09", "sort_order": 3},
        {"title": "متوقف شده", "code": "stopped", "color": "#3033D6", "sort_order": 4},
        {"title": "ابطال شده", "code": "deleted", "color": "#D63031", "sort_order": 5},
    ]
    connection = get_connection()
    try:
        for status in statuses:
            existing = connection.execute(
                "SELECT id, title FROM document_statuses WHERE code = ?",
                (status["code"],)
            ).fetchone()
            if existing:
                connection.execute("""
                    UPDATE document_statuses
                    SET title = ?, color = ?, sort_order = ?
                    WHERE code = ?
                """, (status["title"], status["color"],
                      status["sort_order"], status["code"]))
                continue
            same_title = connection.execute(
                "SELECT id, code FROM document_statuses WHERE title = ?",
                (status["title"],)
            ).fetchone()
            if same_title:
                connection.execute("""
                    UPDATE document_statuses
                    SET code = ?, color = ?, sort_order = ?
                    WHERE id = ?
                """, (status["code"], status["color"],
                      status["sort_order"], same_title["id"]))
                continue
            connection.execute("""
                INSERT INTO document_statuses
                (title, code, color, sort_order, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (status["title"], status["code"],
                  status["color"], status["sort_order"]))
        connection.commit()
    finally:
        connection.close()


def fix_status_codes():
    connection = get_connection()
    try:
        old_title_row = connection.execute(
            "SELECT id, code, title FROM document_statuses WHERE title = ? LIMIT 1",
            ("حذف شده",)
        ).fetchone()
        if old_title_row:
            new_title_exists = connection.execute(
                "SELECT id FROM document_statuses WHERE title = ? LIMIT 1",
                ("ابطال شده",)
            ).fetchone()
            if new_title_exists:
                connection.execute(
                    "DELETE FROM document_statuses WHERE id = ?",
                    (old_title_row["id"],)
                )
            else:
                connection.execute(
                    "UPDATE document_statuses SET title = ? WHERE id = ?",
                    ("ابطال شده", old_title_row["id"])
                )
        deleted_row = connection.execute(
            "SELECT id, code, title FROM document_statuses WHERE title = ? LIMIT 1",
            ("ابطال شده",)
        ).fetchone()
        if not deleted_row:
            connection.execute("""
                INSERT INTO document_statuses
                (title, code, color, sort_order, is_active)
                VALUES ('ابطال شده', 'deleted', '#D63031', 5, 1)
            """)
        elif deleted_row["code"] != "deleted":
            connection.execute("""
                UPDATE document_statuses SET code = 'deleted' WHERE id = ?
            """, (deleted_row["id"],))
        connection.commit()
    finally:
        connection.close()


def run():
    """اجرای همه seedهای این ماژول به ترتیب."""
    create_default_statuses()
    fix_status_codes()
