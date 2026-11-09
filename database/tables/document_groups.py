"""جدول document_groups — گروه‌های سند

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""
TABLE_NAME = "document_groups"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS document_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE NOT NULL,
            code TEXT UNIQUE,
            color TEXT DEFAULT '#3D8499',
            days_review INTEGER DEFAULT 0,
            description TEXT,
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """

INDEX_SQL = []


def create(cursor):
    """ساخت جدول و ایندکس‌های آن."""
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)


def migrate(cursor):
    """افزودن مهلت پیش‌فرض پاسخ به دیتابیس‌های قدیمی."""
    column_names = [
        column["name"]
        for column in cursor.execute("PRAGMA table_info(document_groups)").fetchall()
    ]
    if "days_review" not in column_names:
        cursor.execute(
            "ALTER TABLE document_groups ADD COLUMN days_review INTEGER DEFAULT 0"
        )

