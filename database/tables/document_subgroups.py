"""جدول document_subgroups — زیرگروه‌های سند

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""
TABLE_NAME = "document_subgroups"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS document_subgroups (
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

INDEX_SQL = [
    """
        CREATE INDEX IF NOT EXISTS idx_subgroups_title
        ON document_subgroups(title)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_subgroups_code
        ON document_subgroups(code)
    """,
]

def create(cursor):
    """ساخت جدول و ایندکس‌های آن."""
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)
