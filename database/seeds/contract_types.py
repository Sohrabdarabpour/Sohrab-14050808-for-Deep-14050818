"""داده‌های پیش‌فرض — انواع قرارداد پیش‌فرض

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""

import os
from datetime import datetime

from config import Config

from ..connection import get_connection
from helpers.date_helper import now_tehran, now_tehran_str


def create_default_contract_types():
    contract_types = [
        ("EPC (طراحی + تأمین + اجرا)", "EPC",  "#1b698b", 1),
        ("PC (تأمین + اجرا)",          "PC",   "#167a5c", 2),
        ("پیمانکاری",                  "CON",  "#d69e2e", 3),
        ("مشاوره",                     "CONS", "#c05621", 4),
        ("خدمات",                      "SERV", "#805ad5", 5),
        ("تأمین کالا",                 "SUP",  "#319795", 6),
        ("پیمان مدیریت",               "MC",   "#2b6cb0", 7),
        ("نظارت",                      "SUP2", "#4a5568", 8),
        ("طراحی",                      "DES",  "#2f855a", 9),
        ("دست‌مزد",                    "LO",   "#718096", 10),
        ("عمومی",                      "GEN",  "#a0aeb8", 99),
    ]
    connection = get_connection()
    try:
        inserted = 0
        for title, code, color, sort_order in contract_types:
            existing = connection.execute(
                "SELECT id FROM contract_types WHERE code = ?",
                (code,)
            ).fetchone()
            if existing:
                continue
            connection.execute("""
                INSERT INTO contract_types
                (title, code, color, sort_order, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (title, code, color, sort_order))
            inserted += 1
        connection.commit()
        if inserted:
            print(f"✅ {inserted} نوع قرارداد پیش‌فرض ایجاد شد")
    finally:
        connection.close()


def run():
    """اجرای seed این ماژول."""
    create_default_contract_types()
