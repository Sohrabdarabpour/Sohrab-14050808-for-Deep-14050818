"""جدول document_attachments — پیوست‌های سند (با پشتیبانی از پیش‌نمایش)."""

TABLE_NAME = "document_attachments"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS document_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            reference_id INTEGER,
            event_id INTEGER,

            original_name TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            mime TEXT,
            size INTEGER NOT NULL DEFAULT 0,
            sha256 TEXT,

            kind TEXT DEFAULT 'other',
            previewable INTEGER DEFAULT 0,

            uploaded_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        )
    """

INDEX_SQL = [
    """CREATE INDEX IF NOT EXISTS idx_attach_doc
       ON document_attachments(document_id)""",
    """CREATE INDEX IF NOT EXISTS idx_attach_ref
       ON document_attachments(reference_id)""",
]


def create(cursor):
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)