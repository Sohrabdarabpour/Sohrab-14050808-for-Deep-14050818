"""داده‌های پیش‌فرض — کاربر مدیر سیستم

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""

import os
from datetime import datetime

from config import Config

from ..connection import get_connection
from helpers.date_helper import now_tehran, now_tehran_str
from ..users import create_user


def create_default_admin():
    connection = get_connection()
    user = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        ("admin",)
    ).fetchone()
    connection.close()
    if user:
        return
    success = create_user(
        username="admin",
        password="admin123",
        full_name="مدیر نرم افزار",
        role="admin"
    )
    if success:
        print("✅ کاربر مدیر سیستم ایجاد شد")
        print("   نام کاربری: admin")
        print("   رمز عبور: admin123")


def run():
    """اجرای seed این ماژول."""
    create_default_admin()
