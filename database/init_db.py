"""مقداردهی اولیه دیتابیس — فقط هماهنگ‌کننده.

این فایل قبلاً ~۲۴۵۰ خط بود و همه‌چیز را در خود داشت. الان فقط ترتیب اجرا را
مشخص می‌کند و هر بخش در فایل خودش قرار دارد:

    database/tables/<table>.py        ← ساختار جدول + ایندکس‌ها (DDL)
    database/seeds/<entity>.py        ← داده‌های پیش‌فرض
    database/repositories/<entity>.py ← توابع CRUD

برای اصلاح یک جدول، فقط فایل همان جدول را باز کنید.

توابع CRUD برای سازگاری با کدهای موجود، از همین ماژول هم قابل import هستند:
    from database.init_db import get_note, get_user, ...
"""

import os

from config import Config

from .connection import get_connection
from .repositories import *  # noqa: F401,F403  (سازگاری با importهای قدیمی)
from .repositories import __all__ as _REPOSITORY_EXPORTS
from .seeds import run_all as _run_seeds
from .tables import create_all as _create_tables
from .tables import create_indexes as _create_indexes
from .tables.calendar_holidays import migrate as _migrate_calendar_holidays
from .tables.document_groups import migrate as _migrate_document_groups
from .tables.documents import migrate as _migrate_documents

__all__ = ["init_db"] + list(_REPOSITORY_EXPORTS)


def init_db():
    """ساخت جداول در صورت نبود و درج داده‌های پیش‌فرض.

    اجرای مکرر آن بی‌خطر است (همه دستورها IF NOT EXISTS هستند).
    """
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)

    connection = get_connection()
    cursor = connection.cursor()
    try:
        _create_tables(cursor)
        _migrate_documents(cursor)
        _migrate_document_groups(cursor)
        _migrate_calendar_holidays(cursor)
        _create_indexes(cursor)
        connection.commit()
    finally:
        connection.close()

    _run_seeds()


if __name__ == "__main__":
    init_db()
    print("OK - database initialized")
