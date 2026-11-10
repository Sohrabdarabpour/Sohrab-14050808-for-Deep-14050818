"""مقداردهی اولیه دیتابیس — فقط هماهنگ‌کننده.

اجرای مکرر آن بی‌خطر است (همه دستورها IF NOT EXISTS هستند).
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

# ★★★ جدید — Migration ستون‌های پکیج سند
from .migrations.add_document_package_columns import (
    add_document_package_columns as _migrate_package_columns,
)

__all__ = ["init_db"] + list(_REPOSITORY_EXPORTS)


def init_db():
    """ساخت جداول در صورت نبود و درج داده‌های پیش‌فرض."""
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

    # ★★★ جدید — Migration ستون‌های پکیج سند
    _migrate_package_columns()

    _run_seeds()


if __name__ == "__main__":
    init_db()
    print("OK - database initialized")