"""جدول notifications — اعلان‌ها

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""
TABLE_NAME = "notifications"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT,
            link TEXT,
            notification_type TEXT DEFAULT 'info',
            document_id INTEGER,
            note_id INTEGER,
            is_read INTEGER NOT NULL DEFAULT 0,
            is_dismissed INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP,          -- ★ بدون DEFAULT
            read_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE CASCADE,
            FOREIGN KEY (document_id) REFERENCES documents(id)
                ON DELETE CASCADE,
            FOREIGN KEY (note_id) REFERENCES document_notes(id)
                ON DELETE CASCADE
        )
    """

INDEX_SQL = [
    """
        CREATE INDEX IF NOT EXISTS idx_notif_user
        ON notifications(user_id)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_notif_unread
        ON notifications(user_id, is_read)
    """,
    """
        CREATE INDEX IF NOT EXISTS idx_notif_created
        ON notifications(created_at)
    """,
]

def create(cursor):
    """ساخت جدول و ایندکس‌های آن."""
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)
