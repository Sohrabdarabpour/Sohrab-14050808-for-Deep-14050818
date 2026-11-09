"""جدول workflow_steps — مراحل گردش‌کار

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""
TABLE_NAME = "workflow_steps"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS workflow_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            step_order INTEGER NOT NULL DEFAULT 0,
            assigned_role TEXT,
            is_final INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """

INDEX_SQL = [
    """
        CREATE INDEX IF NOT EXISTS idx_workflow_steps_role
        ON workflow_steps(assigned_role)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_workflow_steps_order
        ON workflow_steps(step_order)
    """,
]

def create(cursor):
    """ساخت جدول و ایندکس‌های آن."""
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)
