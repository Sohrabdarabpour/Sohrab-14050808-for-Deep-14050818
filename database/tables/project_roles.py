"""جدول project_roles — نقش‌های پروژه

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""
TABLE_NAME = "project_roles"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS project_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE NOT NULL,
            code TEXT UNIQUE,
            color TEXT DEFAULT '#1b698b',
            description TEXT,
            is_exclusive INTEGER NOT NULL DEFAULT 0,
            is_required INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """

INDEX_SQL = [
    """
        CREATE INDEX IF NOT EXISTS idx_project_roles_code
        ON project_roles(code)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_project_roles_is_active
        ON project_roles(is_active)
    """,
]

def create(cursor):
    """ساخت جدول و ایندکس‌های آن."""
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)
