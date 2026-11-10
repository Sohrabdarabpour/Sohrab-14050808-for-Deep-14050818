"""جدول‌های document_completion_requests و items — تکمیل مدارک."""

TABLE_NAME = "document_completion_requests"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS document_completion_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            requested_by INTEGER,
            contractor_id INTEGER,

            mode TEXT NOT NULL DEFAULT 'written',
            reference_id INTEGER,

            request_date TEXT,
            due_date TEXT,

            status TEXT NOT NULL DEFAULT 'open',
            note TEXT,

            fulfilled_at TEXT,
            closed_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        )
    """

CREATE_ITEMS_SQL = """
        CREATE TABLE IF NOT EXISTS document_completion_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            is_received INTEGER DEFAULT 0,
            received_at TEXT,
            reference_id INTEGER,
            attachment_id INTEGER,
            note TEXT,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (request_id) REFERENCES document_completion_requests(id) ON DELETE CASCADE
        )
    """

INDEX_SQL = [
    """CREATE INDEX IF NOT EXISTS idx_compl_doc
       ON document_completion_requests(document_id)""",
    """CREATE INDEX IF NOT EXISTS idx_compl_status
       ON document_completion_requests(status)""",
    """CREATE INDEX IF NOT EXISTS idx_compl_items_req
       ON document_completion_items(request_id)""",
]


def create(cursor):
    cursor.execute(CREATE_SQL)
    cursor.execute(CREATE_ITEMS_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)