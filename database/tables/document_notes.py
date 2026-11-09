"""جدول document_notes — یادداشت‌های سند

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""
TABLE_NAME = "document_notes"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS document_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'in_review',
            current_step_id INTEGER,
            assigned_to INTEGER,
            parent_note_id INTEGER,
            created_at TIMESTAMP,          -- ★ بدون DEFAULT
            updated_at TIMESTAMP,          -- ★ بدون DEFAULT
            closed_at TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents(id)
                ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE CASCADE,
            FOREIGN KEY (current_step_id) REFERENCES workflow_steps(id)
                ON DELETE SET NULL,
            FOREIGN KEY (assigned_to) REFERENCES users(id)
                ON DELETE SET NULL,
            FOREIGN KEY (parent_note_id) REFERENCES document_notes(id)
                ON DELETE SET NULL
        )
    """

INDEX_SQL = [
    """
        CREATE INDEX IF NOT EXISTS idx_notes_document
        ON document_notes(document_id)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_notes_user
        ON document_notes(user_id)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_notes_status
        ON document_notes(status)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_notes_assigned
        ON document_notes(assigned_to)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_notes_step
        ON document_notes(current_step_id)
    """,
]

def create(cursor):
    """ساخت جدول و ایندکس‌های آن."""
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)
