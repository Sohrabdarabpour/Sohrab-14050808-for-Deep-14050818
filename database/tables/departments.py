"""جدول departments — دپارتمان‌ها

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""
TABLE_NAME = "departments"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE NOT NULL,
            code TEXT UNIQUE,
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            supervisor_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (supervisor_id) REFERENCES users(id)
        )
    """

INDEX_SQL = []

def create(cursor):
    """ساخت جدول و ایندکس‌های آن."""
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)
