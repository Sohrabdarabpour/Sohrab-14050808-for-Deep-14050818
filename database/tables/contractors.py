"""جدول contractors — پیمانکاران

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""
TABLE_NAME = "contractors"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS contractors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE,
            national_id TEXT,
            economic_code TEXT,
            registration_number TEXT,
            manager_name TEXT,
            phone TEXT,
            mobile TEXT,
            email TEXT,
            address TEXT,
            postal_code TEXT,
            city TEXT,
            province TEXT,
            grade TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """

INDEX_SQL = [
    """
        CREATE INDEX IF NOT EXISTS idx_contractors_name
        ON contractors(name)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_contractors_code
        ON contractors(code)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_contractors_is_active
        ON contractors(is_active)
    """,
]

def create(cursor):
    """ساخت جدول و ایندکس‌های آن."""
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)
