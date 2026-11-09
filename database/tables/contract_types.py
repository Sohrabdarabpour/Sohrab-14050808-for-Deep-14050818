"""جدول contract_types — انواع قرارداد

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""
TABLE_NAME = "contract_types"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS contract_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE NOT NULL,
            code TEXT UNIQUE,
            color TEXT DEFAULT '#1b698b',
            description TEXT,
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """

INDEX_SQL = [
    """
        CREATE INDEX IF NOT EXISTS idx_contract_types_code
        ON contract_types(code)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_contract_types_is_active
        ON contract_types(is_active)
    """,
]

def create(cursor):
    """ساخت جدول و ایندکس‌های آن."""
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)
