"""پیوست‌های سند (فایل‌های اسکن‌شده و پاسخ‌ها)."""

TABLE_NAME = "document_package_attachments"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS document_package_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_id INTEGER NOT NULL,
            parent_attachment_id INTEGER,
            original_name TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            mime TEXT,
            size INTEGER NOT NULL DEFAULT 0,
            sha256 TEXT,
            kind TEXT DEFAULT 'other',
            description TEXT,
            previewable INTEGER DEFAULT 0,
            uploaded_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (package_id) REFERENCES document_packages(id) ON DELETE CASCADE,
            FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE SET NULL
        )
    """

INDEX_SQL = [
    """CREATE INDEX IF NOT EXISTS idx_dpatt_package
       ON document_package_attachments(package_id)""",
    """CREATE INDEX IF NOT EXISTS idx_dpatt_parent
       ON document_package_attachments(parent_attachment_id)""",
]


def create(cursor):
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)