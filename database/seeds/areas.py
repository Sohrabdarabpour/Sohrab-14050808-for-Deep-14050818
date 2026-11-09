"""داده‌های پیش‌فرض — نواحی پیش‌فرض

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""

import os
from datetime import datetime

from config import Config

from ..connection import get_connection
from helpers.date_helper import now_tehran, now_tehran_str


def create_default_areas():
    areas = []
    connection = get_connection()
    try:
        for area in areas:
            existing = connection.execute(
                "SELECT id FROM areas WHERE code = ?",
                (area["code"],)
            ).fetchone()
            if existing:
                continue
            connection.execute("""
                INSERT INTO areas (title, code, sort_order, is_active)
                VALUES (?, ?, ?, 1)
            """, (area["title"], area["code"], area["sort_order"]))
        connection.commit()
    finally:
        connection.close()


def run():
    """اجرای seed این ماژول."""
    create_default_areas()
