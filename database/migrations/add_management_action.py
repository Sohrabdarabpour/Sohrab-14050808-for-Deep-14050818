"""افزودن ستون management_action به جدول document_packages.

اجرای مکرر بی‌خطر است.
"""

import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, PROJECT_ROOT)

from database.connection import get_connection


def add_management_action_column():
    connection = get_connection()
    try:
        existing = {
            col["name"]
            for col in connection.execute(
                "PRAGMA table_info(document_packages)"
            ).fetchall()
        }
        if "management_action" in existing:
            print("ℹ️  ستون management_action قبلاً وجود دارد")
            return

        connection.execute(
            "ALTER TABLE document_packages ADD COLUMN management_action TEXT"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_dp_management_action "
            "ON document_packages(management_action)"
        )
        connection.commit()
        print("✅ ستون management_action اضافه شد")
    finally:
        connection.close()


if __name__ == "__main__":
    add_management_action_column()