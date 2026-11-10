"""افزودن ستون‌های پکیج سند به جدول documents.

اجرای مکرر بی‌خطر است (هر ستون فقط اگر نبود اضافه می‌شود).
"""

import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, PROJECT_ROOT)

from database.connection import get_connection


#: (نام ستون، نوع)
COLUMNS = [
    # شماره‌گذاری
    ("package_code", "TEXT"),
    ("package_year", "INTEGER"),

    # طبقه‌بندی و منبع
    ("direction", "TEXT DEFAULT 'incoming'"),
    ("source_type", "TEXT"),
    ("source_department_id", "INTEGER"),
    ("priority", "TEXT DEFAULT 'normal'"),
    ("confidentiality", "TEXT DEFAULT 'internal'"),

    # فرستنده
    ("sender_name", "TEXT"),
    ("sender_ref_no", "TEXT"),
    ("sender_ref_date", "TEXT"),

    # مرحله چرخه عمر
    ("stage", "TEXT DEFAULT 'draft'"),

    # SLA کامل
    ("sla_start_date", "TEXT"),
    ("sla_effective_days", "INTEGER"),
    ("is_overdue", "INTEGER DEFAULT 0"),
    ("overdue_days", "INTEGER DEFAULT 0"),

    # آرشیو
    ("registered_by", "INTEGER"),
    ("registered_at", "TEXT"),
    ("closed_by", "INTEGER"),
    ("closed_at", "TEXT"),
    ("archived_by", "INTEGER"),
    ("archived_at", "TEXT"),
    ("archive_reason", "TEXT"),
    ("reopen_count", "INTEGER DEFAULT 0"),
]

INDEX_SQL = [
    """CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_package_code
       ON documents(package_code) WHERE package_code IS NOT NULL""",
    """CREATE INDEX IF NOT EXISTS idx_documents_stage
       ON documents(stage)""",
    """CREATE INDEX IF NOT EXISTS idx_documents_due
       ON documents(response_due_date)""",
    """CREATE INDEX IF NOT EXISTS idx_documents_overdue
       ON documents(is_overdue)""",
    """CREATE INDEX IF NOT EXISTS idx_documents_source
       ON documents(source_type)""",
]


def add_document_package_columns():
    connection = get_connection()
    try:
        existing = {
            col["name"] for col in
            connection.execute("PRAGMA table_info(documents)").fetchall()
        }
        added = []
        for name, col_type in COLUMNS:
            if name in existing:
                continue
            connection.execute(
                f"ALTER TABLE documents ADD COLUMN {name} {col_type}"
            )
            added.append(name)
            print(f"✅ ستون {name} اضافه شد")

        for stmt in INDEX_SQL:
            connection.execute(stmt)
        connection.commit()

        if not added:
            print("ℹ️  همه‌ی ستون‌ها قبلاً وجود داشتند")
        else:
            print(f"✅ {len(added)} ستون اضافه شد")
    finally:
        connection.close()


if __name__ == "__main__":
    add_document_package_columns()