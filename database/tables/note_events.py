"""جدول note_events — رویدادهای یادداشت

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""
TABLE_NAME = "note_events"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS note_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            message TEXT,
            from_step_id INTEGER,
            to_step_id INTEGER,
            from_user_id INTEGER,
            to_user_id INTEGER,
            created_at TIMESTAMP,          -- ★ بدون DEFAULT
            FOREIGN KEY (note_id) REFERENCES document_notes(id)
                ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE CASCADE,
            FOREIGN KEY (from_step_id) REFERENCES workflow_steps(id)
                ON DELETE SET NULL,
            FOREIGN KEY (to_step_id) REFERENCES workflow_steps(id)
                ON DELETE SET NULL,
            FOREIGN KEY (from_user_id) REFERENCES users(id)
                ON DELETE SET NULL,
            FOREIGN KEY (to_user_id) REFERENCES users(id)
                ON DELETE SET NULL
        )
    """

INDEX_SQL = [
    """
        CREATE INDEX IF NOT EXISTS idx_ne_note
        ON note_events(note_id)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_ne_user
        ON note_events(user_id)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_ne_type
        ON note_events(event_type)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_ne_created
        ON note_events(created_at)
    """,
]

def create(cursor):
    """ساخت جدول و ایندکس‌های آن."""
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)
