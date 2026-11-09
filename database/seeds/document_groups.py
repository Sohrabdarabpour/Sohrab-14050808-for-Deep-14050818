"""داده‌های پیش‌فرض — گروه‌های سند پیش‌فرض

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""

import os
from datetime import datetime

from config import Config

from ..connection import get_connection
from helpers.date_helper import now_tehran, now_tehran_str


def create_default_document_groups():
    groups = [
        ("منابع انسانی", "HR", "#2b6cb0", 1),
        ("روش اجرایی", "PR", "#167a5c", 2),
        ("برآورد", "ES", "#d69e2e", 3),
        ("نظارت کارگاهی", "SS", "#c05621", 4),
        ("مواد و مصالح", "M", "#805ad5", 5),
        ("تحویل قطعی", "FTD", "#319795", 6),
        ("دعاوی پیمانکار", "CC", "#e53e3e", 7),
        ("انرژی", "Eny", "#dd6b20", 8),
        ("مهندسی", "E", "#3182ce", 9),
        ("بهداشت، ایمنی و محیط زیست", "HSE", "#38a169", 10),
        ("مالی", "F", "#b7791f", 11),
        ("قراردادی", "CO", "#d53f8c", 12),
        ("کنترل کیفیت", "QC", "#2c7a7b", 13),
        ("مناقصه", "T", "#6b46c1", 14),
        ("مدیریت پروژه (برنامه ریزی و کنترل پروژه)", "PM", "#1b698b", 15),
        ("تحویل موقت", "PTD", "#4a5568", 16),
        ("عمومی", "GE", "#718096", 99),
    ]
    connection = get_connection()
    try:
        inserted = 0
        for title, code, color, sort_order in groups:
            existing = connection.execute(
                "SELECT id FROM document_groups WHERE code = ?",
                (code,)
            ).fetchone()
            if existing:
                continue
            connection.execute("""
                INSERT INTO document_groups
                (title, code, color, sort_order, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (title, code, color, sort_order))
            inserted += 1
        connection.commit()
        if inserted:
            print(f"✅ {inserted} گروه سند پیش‌فرض ایجاد شد")
    finally:
        connection.close()


def run():
    """اجرای seed این ماژول."""
    create_default_document_groups()
