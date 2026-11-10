"""جدول document_events — تاریخچه‌ی کامل و غیرقابل‌تغییر سند."""

TABLE_NAME = "document_events"

CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS document_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            actor_id INTEGER,
            event_type TEXT NOT NULL,
            summary TEXT,
            payload TEXT,
            assignment_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
            FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """

INDEX_SQL = [
    """CREATE INDEX IF NOT EXISTS idx_events_doc_created
       ON document_events(document_id, created_at)""",
    """CREATE INDEX IF NOT EXISTS idx_events_type
       ON document_events(event_type)""",
]


def create(cursor):
    cursor.execute(CREATE_SQL)
    for statement in INDEX_SQL:
        cursor.execute(statement)